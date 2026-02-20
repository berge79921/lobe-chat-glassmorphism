#!/usr/bin/env python3
"""Import RS JSON artifacts into super_ris.rs."""

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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import *_RS.json into super_ris.rs")
    parser.add_argument(
        "--json-root",
        default=os.getenv("IMPORT_RS_JSON_ROOT", "/srv/super-ris-artifacts"),
        help="Root folder scanned recursively for *_RS.json files",
    )
    parser.add_argument(
        "--glob",
        default=os.getenv("IMPORT_RS_JSON_GLOB", "*_RS.json"),
        help="Glob pattern for RS JSON files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of files (0 = no limit)",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=int(os.getenv("IMPORT_RS_COMMIT_EVERY", os.getenv("IMPORT_COMMIT_EVERY", "1000"))),
        help="Commit DB transaction every N upserts (0 = commit once at end)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and report only")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    return parser.parse_args()


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
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


def _normalize_text_list(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        s = value.strip()
        if s:
            out.append(s)
    elif isinstance(value, list):
        for item in value:
            text = _as_text(item)
            if text:
                out.append(text)
    elif value is not None:
        text = _as_text(value)
        if text:
            out.append(text)
    return out


def _get_nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
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


def _extract_rs_number(payload: dict[str, Any], path: Path) -> str | None:
    from_rs_refs = _get_nested(payload, "rs", "references")
    rs_ref = None
    if isinstance(from_rs_refs, dict) and from_rs_refs:
        rs_ref = next(iter(from_rs_refs.keys()))
    file_candidates = [
        payload.get("dateiname"),
        payload.get("file"),
        payload.get("filepath"),
        path.name,
        path.stem,
    ]
    file_match = None
    for candidate in file_candidates:
        text = _as_text(candidate)
        if not text:
            continue
        match = re.search(r"(RS\d{6,10})", text, flags=re.IGNORECASE)
        if match:
            file_match = match.group(1).upper()
            break
    rs_number = _first_non_empty(
        [
            payload.get("rechtssatznummer"),
            payload.get("rs_number"),
            _get_nested(payload, "meta", "rechtssatznummer"),
            rs_ref,
            file_match,
        ]
    )
    if not rs_number:
        return None
    match = re.search(r"(RS\d{6,10})", rs_number, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return rs_number.strip().upper()


def _extract_row(payload: dict[str, Any], path: Path) -> dict[str, Any] | None:
    rs_number = _extract_rs_number(payload, path)
    if not rs_number:
        return None

    rechtssatz_volltext = _first_non_empty(
        [
            payload.get("rechtssatz"),
            _get_nested(payload, "super_ris", "summary"),
            _get_nested(payload, "analysis", "summary"),
        ]
    )

    kurzinformation = _first_non_empty(
        [
            _get_nested(payload, "super_ris", "summary"),
            _get_nested(payload, "analysis", "summary"),
            rechtssatz_volltext,
        ]
    )

    rechtsgebiet_primary = _first_non_empty(
        [
            payload.get("rechtsgebiet_primary"),
            payload.get("rechtsgebiet"),
            _get_nested(payload, "super_ris", "rechtsgebiet"),
        ]
    )

    schlagworte = _normalize_text_list(
        payload.get("schlagworte")
        if payload.get("schlagworte") is not None
        else _get_nested(payload, "super_ris", "schlagworte")
    )
    fachgebiete = _normalize_text_list(
        payload.get("fachgebiete")
        if payload.get("fachgebiete") is not None
        else _get_nested(payload, "super_ris", "fachgebiet")
    )

    entscheidungsdatum = _parse_date(
        payload.get("entscheidungsdatum")
        or payload.get("datum")
        or _get_nested(payload, "metadata", "date")
        or _get_nested(payload, "meta", "entscheidungsdatum")
    )

    return {
        "rs_number": rs_number,
        "rechtssatz_volltext": rechtssatz_volltext,
        "kurzinformation": kurzinformation,
        "rechtsgebiet_primary": rechtsgebiet_primary,
        "schlagworte": schlagworte,
        "fachgebiete": fachgebiete,
        "entscheidungsdatum": entscheidungsdatum,
    }


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
INSERT INTO super_ris.rs (
  rs_number,
  rechtssatz_volltext,
  kurzinformation,
  rechtsgebiet_primary,
  schlagworte,
  fachgebiete,
  entscheidungsdatum
) VALUES (
  %(rs_number)s,
  %(rechtssatz_volltext)s,
  %(kurzinformation)s,
  %(rechtsgebiet_primary)s,
  %(schlagworte)s,
  %(fachgebiete)s,
  %(entscheidungsdatum)s
)
ON CONFLICT (rs_number)
DO UPDATE SET
  rechtssatz_volltext = EXCLUDED.rechtssatz_volltext,
  kurzinformation = EXCLUDED.kurzinformation,
  rechtsgebiet_primary = EXCLUDED.rechtsgebiet_primary,
  schlagworte = EXCLUDED.schlagworte,
  fachgebiete = EXCLUDED.fachgebiete,
  entscheidungsdatum = EXCLUDED.entscheidungsdatum
RETURNING (xmax = 0) AS inserted;
"""


def main() -> int:
    args = _parse_args()
    json_root = Path(args.json_root).resolve()
    if not json_root.exists():
        print(f"[import-rs] json root not found: {json_root}", file=sys.stderr)
        return 2

    files = _collect_json_files(json_root, args.glob, args.limit)
    if not files:
        print(f"[import-rs] no files matched {args.glob} under {json_root}")
        return 0

    print(f"[import-rs] scanning {len(files)} file(s) from {json_root}")
    if args.dry_run:
        print("[import-rs] dry-run mode enabled")

    inserted = 0
    updated = 0
    failed = 0
    skipped = 0
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

                row = _extract_row(payload, path)
                if row is None:
                    skipped += 1
                    if args.verbose:
                        print(f"[import-rs] {index:>6}: skipped (no rs_number) path={path}")
                    continue

                if args.dry_run:
                    if args.verbose:
                        print(
                            f"[dry-run-rs] {index:>6}: rs={row['rs_number']} "
                            f"gebiet={row['rechtsgebiet_primary'] or '-'}"
                        )
                    continue

                assert cur is not None
                savepoint_name = f"sp_rs_{index}"
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
                    print(f"[import-rs] {index:>6}: {action} rs={row['rs_number']}")

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
                print(f"[import-rs] ERROR {path}: {exc}", file=sys.stderr)

        if not args.dry_run and conn is not None:
            conn.commit()

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        print(f"[import-rs] fatal: {exc}", file=sys.stderr)
        return 1
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    print(
        "[import-rs] done "
        f"processed={len(files)} inserted={inserted} updated={updated} skipped={skipped} failed={failed} dry_run={args.dry_run}"
    )
    return 1 if failed > 0 and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
