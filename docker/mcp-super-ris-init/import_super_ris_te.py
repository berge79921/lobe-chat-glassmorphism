#!/usr/bin/env python3
"""Import TE JSON + original HTML artifacts into super_ris.te.

Supported inputs:
- *_TE.json files (recursive)
- Optional HTML files referenced via JSON keys (file/filepath/dateiname)
- Optional inline HTML fragments (kopf_html/spruch/begruendung/rechtliche_beurteilung)

Target table:
  super_ris.te(
    stable_key, normalized_gz, geschaeftszahl, datum, entscheidungsdatum,
    summary, source_json, original_html
  )
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import *_TE.json + HTML into super_ris.te",
    )
    parser.add_argument(
        "--json-root",
        default=os.getenv("IMPORT_JSON_ROOT", "/srv/super-ris-artifacts"),
        help="Root folder scanned recursively for *_TE.json files",
    )
    parser.add_argument(
        "--html-root",
        action="append",
        default=[],
        help="Optional extra HTML root (repeatable)",
    )
    parser.add_argument(
        "--glob",
        default=os.getenv("IMPORT_JSON_GLOB", "*_TE.json"),
        help="Glob pattern for JSON files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of JSON files (0 = no limit)",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=int(os.getenv("IMPORT_COMMIT_EVERY", "1000")),
        help="Commit DB transaction every N upserts (0 = commit once at end)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report only, do not write to DB",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    return parser.parse_args()


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        raw10 = raw[:10]
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y%m%d"):
            try:
                return datetime.strptime(raw10, fmt).date()
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _sanitize_stable_key(value: str) -> str:
    s = str(value).strip()
    s = s.replace("\\", "/")
    s = s.split("/")[-1]
    s = re.sub(r"\.(json|html|htm)$", "", s, flags=re.IGNORECASE)
    return s[:255]


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    if isinstance(value, (list, tuple)):
        for item in value:
            text = _as_text(item)
            if text:
                return text
    return None


def _first_non_empty(values: list[Any]) -> str | None:
    for value in values:
        text = _as_text(value)
        if text:
            return text
    return None


def _get_nested(dct: dict[str, Any], *keys: str) -> Any:
    cur: Any = dct
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _extract_summary(payload: dict[str, Any]) -> str | None:
    candidates = [
        payload.get("summary"),
        _get_nested(payload, "super_ris", "summary"),
        _get_nested(payload, "analysis", "summary"),
        _get_nested(payload, "mini_analysis", "summary"),
        _get_nested(payload, "extraction", "summary"),
        _get_nested(payload, "meta", "summary"),
        _get_nested(payload, "semantic", "entscheidung"),
        _get_nested(payload, "semantic", "begruendung"),
        _get_nested(payload, "basic", "spruch"),
        _get_nested(payload, "basic", "begruendung"),
    ]
    summary = _first_non_empty(candidates)
    if summary:
        return summary
    # Fallback for extraction formats with no dedicated summary field.
    parts = [
        _get_nested(payload, "semantic", "entscheidung"),
        _get_nested(payload, "semantic", "begruendung"),
        _get_nested(payload, "semantic", "rechtliche_bedeutung"),
    ]
    merged = [text for text in (_as_text(part) for part in parts) if text]
    if merged:
        return "\n\n".join(merged)
    return None


def _extract_geschaeftszahl(payload: dict[str, Any]) -> str | None:
    candidates = [
        payload.get("geschaeftszahl"),
        payload.get("geschaeftszahlen"),
        _get_nested(payload, "metadata", "case_number"),
        _get_nested(payload, "gz", "from_metadata"),
        payload.get("case_number"),
        _get_nested(payload, "meta", "geschaeftszahl"),
        _get_nested(payload, "meta", "geschaeftszahlen"),
        _get_nested(payload, "meta", "normalized_gz"),
        _get_nested(payload, "basic", "geschaeftszahl"),
    ]
    return _first_non_empty(candidates)


def _extract_normalized_gz(payload: dict[str, Any], geschaeftszahl: str | None) -> str | None:
    candidates = [
        payload.get("normalized_gz"),
        _get_nested(payload, "meta", "normalized_gz"),
        _get_nested(payload, "gz", "from_metadata"),
        _get_nested(payload, "metadata", "case_number"),
        geschaeftszahl,
    ]
    raw = _first_non_empty(candidates)
    if not raw:
        return None
    return raw.replace(" ", "")


def _extract_stable_key(payload: dict[str, Any], json_path: Path) -> str:
    candidates = [
        payload.get("stable_key"),
        payload.get("te_id"),
        _get_nested(payload, "meta", "stable_key"),
        _get_nested(payload, "super_ris", "stable_key"),
        payload.get("filepath"),
        payload.get("file"),
        payload.get("dateiname"),
        json_path.stem,
    ]
    raw = _first_non_empty(candidates) or json_path.stem
    key = _sanitize_stable_key(raw)
    if key.lower().endswith("_te"):
        key = key[:-3]
    return key or _sanitize_stable_key(json_path.stem)


def _candidate_html_paths(payload: dict[str, Any]) -> list[str]:
    values = [
        payload.get("filepath"),
        payload.get("file"),
        payload.get("dateiname"),
        _get_nested(payload, "extraction", "source_file"),
        _get_nested(payload, "meta", "filepath"),
        _get_nested(payload, "meta", "file"),
    ]
    out: list[str] = []
    for value in values:
        text = _as_text(value)
        if not text:
            continue
        out.append(text)
        lowered = text.lower()
        if lowered.endswith(".json"):
            out.append(re.sub(r"\.json$", ".html", text, flags=re.IGNORECASE))
            out.append(re.sub(r"\.json$", ".htm", text, flags=re.IGNORECASE))
        elif "." not in Path(text).name:
            out.append(f"{text}.html")
            out.append(f"{text}.htm")
    return out


def _load_html_from_path(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _extract_inline_html(payload: dict[str, Any]) -> str | None:
    direct = _first_non_empty(
        [
            payload.get("original_html"),
            payload.get("html"),
            _get_nested(payload, "te", "original_html"),
            _get_nested(payload, "te", "html"),
        ]
    )
    if direct:
        return direct

    parts: list[str] = []
    for key in ("kopf_html", "spruch", "begruendung", "rechtliche_beurteilung"):
        value = payload.get(key)
        text = _as_text(value)
        if text:
            parts.append(text)

    te_obj = payload.get("te")
    if isinstance(te_obj, dict):
        for key in ("leitsatz", "spruch", "begruendung", "rechtliche_beurteilung"):
            text = _as_text(te_obj.get(key))
            if text:
                parts.append(text)

    basic_obj = payload.get("basic")
    if isinstance(basic_obj, dict):
        for key in ("kopf", "spruch", "begruendung"):
            text = _as_text(basic_obj.get(key))
            if text:
                parts.append(text)

    if parts:
        return "\n\n".join(parts)
    return None


def _resolve_original_html(
    payload: dict[str, Any],
    json_path: Path,
    html_roots: list[Path],
) -> str | None:
    inline_html = _extract_inline_html(payload)
    if inline_html:
        return inline_html

    rel_paths = _candidate_html_paths(payload)
    search_roots = [json_path.parent] + html_roots
    for rel in rel_paths:
        rel_norm = rel.replace("\\", "/").lstrip("/")
        basename = Path(rel_norm).name
        for root in search_roots:
            candidates = [
                root / rel_norm,
                root / basename,
                root / "RIS_DOWNLOADS" / basename,
                root / "RIS_DOWNLOADS" / "2021" / basename,
                root / "RIS_DOWNLOADS" / "2022" / basename,
                root / "RIS_DOWNLOADS" / "2023" / basename,
                root / "RIS_DOWNLOADS" / "2024" / basename,
                root / "RIS_DOWNLOADS" / "2025" / basename,
                root / "RIS_DOWNLOADS" / "2026" / basename,
            ]
            for candidate in candidates:
                html = _load_html_from_path(candidate)
                if html:
                    return html
    return None


def _collect_json_files(root: Path, pattern: str, limit: int) -> list[Path]:
    if limit > 0:
        files: list[Path] = []
        for path in root.rglob(pattern):
            files.append(path)
            if len(files) >= limit:
                break
        return sorted(files)
    return sorted(root.rglob(pattern))


def _build_conn() -> psycopg2.extensions.connection:
    cfg = {
        "host": os.getenv("MCP_ZIVILRECHT_DB_HOST", "mcp-super-ris-postgres"),
        "port": int(os.getenv("MCP_ZIVILRECHT_DB_PORT", "5432")),
        "dbname": os.getenv("MCP_ZIVILRECHT_DB_NAME", "super_ris"),
        "user": os.getenv("MCP_ZIVILRECHT_DB_USER", "postgres"),
        "connect_timeout": int(os.getenv("MCP_ZIVILRECHT_DB_CONNECT_TIMEOUT", "10")),
    }
    password = os.getenv("MCP_ZIVILRECHT_DB_PASSWORD", "")
    if password:
        cfg["password"] = password
    sslmode = os.getenv("MCP_ZIVILRECHT_DB_SSLMODE", "")
    if sslmode:
        cfg["sslmode"] = sslmode
    conn = psycopg2.connect(**cfg)
    conn.autocommit = False
    return conn


UPSERT_SQL = """
INSERT INTO super_ris.te (
  stable_key,
  normalized_gz,
  geschaeftszahl,
  datum,
  entscheidungsdatum,
  summary,
  source_json,
  original_html
) VALUES (
  %(stable_key)s,
  %(normalized_gz)s,
  %(geschaeftszahl)s,
  %(datum)s,
  %(entscheidungsdatum)s,
  %(summary)s,
  %(source_json)s,
  %(original_html)s
)
ON CONFLICT (stable_key)
DO UPDATE SET
  normalized_gz = EXCLUDED.normalized_gz,
  geschaeftszahl = EXCLUDED.geschaeftszahl,
  datum = EXCLUDED.datum,
  entscheidungsdatum = EXCLUDED.entscheidungsdatum,
  summary = EXCLUDED.summary,
  source_json = EXCLUDED.source_json,
  original_html = EXCLUDED.original_html
RETURNING (xmax = 0) AS inserted;
"""


def main() -> int:
    args = _parse_args()
    json_root = Path(args.json_root).resolve()
    if not json_root.exists():
        print(f"[import] json root not found: {json_root}", file=sys.stderr)
        return 2

    html_roots: list[Path] = []
    html_root_args = list(args.html_root)
    html_roots_env = os.getenv("IMPORT_HTML_ROOTS", "")
    if html_roots_env:
        for part in re.split(r"[,:;]", html_roots_env):
            if part.strip():
                html_root_args.append(part.strip())

    for item in html_root_args:
        if item:
            html_roots.append(Path(item).resolve())

    files = _collect_json_files(json_root, args.glob, args.limit)
    if not files:
        print(f"[import] no files matched {args.glob} under {json_root}")
        return 0

    print(f"[import] scanning {len(files)} file(s) from {json_root}")
    if args.dry_run:
        print("[import] dry-run mode enabled")

    inserted = 0
    updated = 0
    failed = 0
    with_html = 0
    upserted_since_commit = 0

    conn = None
    cur = None
    try:
        if not args.dry_run:
            conn = _build_conn()
            cur = conn.cursor()

        for index, path in enumerate(files, start=1):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON root is not an object")

                stable_key = _extract_stable_key(payload, path)
                geschaeftszahl = _extract_geschaeftszahl(payload)
                normalized_gz = _extract_normalized_gz(payload, geschaeftszahl)
                entscheidungsdatum = _parse_date(
                    payload.get("entscheidungsdatum")
                    or payload.get("datum")
                    or _get_nested(payload, "metadata", "date")
                    or _get_nested(payload, "meta", "entscheidungsdatum")
                )
                datum = _parse_date(
                    payload.get("datum")
                    or payload.get("entscheidungsdatum")
                    or _get_nested(payload, "metadata", "date")
                    or _get_nested(payload, "meta", "entscheidungsdatum")
                )
                summary = _extract_summary(payload)
                original_html = _resolve_original_html(payload, path, html_roots)
                if original_html:
                    with_html += 1

                row = {
                    "stable_key": stable_key,
                    "normalized_gz": normalized_gz,
                    "geschaeftszahl": geschaeftszahl,
                    "datum": datum,
                    "entscheidungsdatum": entscheidungsdatum,
                    "summary": summary,
                    "source_json": Json(payload),
                    "original_html": original_html,
                }

                if args.dry_run:
                    if args.verbose:
                        print(
                            f"[dry-run] {index:>6}: key={stable_key} gz={geschaeftszahl or '-'} "
                            f"date={entscheidungsdatum or datum or '-'} html={'yes' if original_html else 'no'}"
                        )
                    continue

                assert cur is not None
                savepoint_name = f"sp_te_{index}"
                cur.execute(f"SAVEPOINT {savepoint_name}")
                try:
                    cur.execute(UPSERT_SQL, row)
                    res = cur.fetchone()
                    cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                except Exception:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    raise
                if res and bool(res[0]):
                    inserted += 1
                    action = "inserted"
                else:
                    updated += 1
                    action = "updated"

                if args.verbose:
                    print(
                        f"[import] {index:>6}: {action} key={stable_key} "
                        f"html={'yes' if original_html else 'no'}"
                    )
                upserted_since_commit += 1
                if (
                    conn is not None
                    and args.commit_every > 0
                    and upserted_since_commit >= args.commit_every
                ):
                    conn.commit()
                    upserted_since_commit = 0

            except Exception as exc:  # keep loop robust
                failed += 1
                print(f"[import] ERROR {path}: {exc}", file=sys.stderr)

        if not args.dry_run and conn is not None:
            conn.commit()

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        print(f"[import] fatal: {exc}", file=sys.stderr)
        return 1
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    processed = len(files)
    print(
        "[import] done "
        f"processed={processed} inserted={inserted} updated={updated} failed={failed} with_html={with_html} dry_run={args.dry_run}"
    )
    return 1 if failed > 0 and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
