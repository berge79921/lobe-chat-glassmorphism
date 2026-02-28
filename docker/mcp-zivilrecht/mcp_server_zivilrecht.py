#!/usr/bin/env python3
"""
MCP Server für österreichisches Zivilrecht.

Bietet Tools für:
- Fine-tuned Gemini Pro Modell (bereicherung-pro25-v1)
- PostgreSQL Datenbank (super_ris.rs, super_ris.te)
- Caching von großen Kontexten

Installation:
  pip install mcp psycopg2-binary

Verwendung mit Claude Code:
  claude mcp add zivilrecht-server python3 /path/to/mcp_server_zivilrecht.py

Verwendung mit Gemini CLI:
  gemini mcp add zivilrecht-server python3 /path/to/mcp_server_zivilrecht.py
"""

import asyncio
import json
import os
from typing import Any

import aiohttp
import psycopg2

try:
    from google.auth import default as google_auth_default
    from google.auth.transport.requests import Request as GoogleAuthRequest
except ImportError:
    google_auth_default = None
    GoogleAuthRequest = None

# Try to import MCP - provide instructions if not available
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP not installed. Install with: pip install mcp")
    print("Or use: uv pip install mcp")
    exit(1)

# Configuration
VERTEX_ENDPOINT_ID = "5416597799191969792"  # bereicherung-pro25-v1
VERTEX_PROJECT_ID = "iron-entropy-403013"
VERTEX_REGION = "us-central1"
VERTEX_AUTH_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)

DB_CONFIG = {
    "host": os.getenv("MCP_ZIVILRECHT_DB_HOST", "localhost"),
    "port": int(os.getenv("MCP_ZIVILRECHT_DB_PORT", "5432")),
    "dbname": os.getenv("MCP_ZIVILRECHT_DB_NAME", "super_ris"),
    "user": os.getenv("MCP_ZIVILRECHT_DB_USER", "reinhardberger"),
    "connect_timeout": int(os.getenv("MCP_ZIVILRECHT_DB_CONNECT_TIMEOUT", "10")),
}
if os.getenv("MCP_ZIVILRECHT_DB_PASSWORD"):
    DB_CONFIG["password"] = os.getenv("MCP_ZIVILRECHT_DB_PASSWORD")
if os.getenv("MCP_ZIVILRECHT_DB_SSLMODE"):
    DB_CONFIG["sslmode"] = os.getenv("MCP_ZIVILRECHT_DB_SSLMODE")

# Initialize MCP Server
server = Server("zivilrecht-server")

# Database connection (lazy initialization)
_db_conn = None
_has_rs_content_status = None

def get_db_connection():
    """Get or create database connection."""
    global _db_conn
    if _db_conn is None or _db_conn.closed:
        _db_conn = psycopg2.connect(**DB_CONFIG)
        _db_conn.autocommit = True
    return _db_conn


def has_rs_content_status_column() -> bool:
    """Check once whether super_ris.rs has content_status marker column."""
    global _has_rs_content_status
    if _has_rs_content_status is not None:
        return _has_rs_content_status

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'super_ris'
                  AND table_name = 'rs'
                  AND column_name = 'content_status'
            )
            """
        )
        _has_rs_content_status = bool(cursor.fetchone()[0])
        return _has_rs_content_status
    finally:
        cursor.close()


def rs_content_filter_sql(alias: str = "") -> str:
    """SQL predicate that excludes empty/placeholder RS rows."""
    prefix = f"{alias}." if alias else ""
    non_empty = (
        f"nullif(btrim(coalesce({prefix}rechtssatz_volltext, "
        f"{prefix}kurzinformation, '')), '') is not null"
    )
    if has_rs_content_status_column():
        return f"{non_empty} AND coalesce({prefix}content_status, '') <> 'NO_CONTENT_STUB'"
    return non_empty


def clamp_limit(value: Any, default: int, max_value: int) -> int:
    """Clamp possibly-invalid tool limit values to a safe integer range."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < 1:
        return default
    return min(n, max_value)


def clamp_query(value: Any, max_len: int = 500) -> str:
    """Normalize free-text query inputs and cap length."""
    if value is None:
        return ""
    text = str(value).strip()
    return text[:max_len]


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="ask_gemini_zivilrecht",
            description="Stellt eine Frage an das fine-tuned Gemini Pro Modell für österreichisches Zivilrecht (Laesio Enormis, Bereicherungsrecht, Pflichtteilsrecht). Das Modell ist spezialisiert auf ABGB und UGB.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Die rechtliche Frage auf Deutsch"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optionaler Sachverhalt oder zusätzlicher Kontext"
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="search_ogh_rechtssaetze",
            description="Durchsucht die OGH-Rechtssätze (super_ris.rs) mittels Volltext-Suche. Gibt RS-Nummer, Kernaussage und Schlagworte zurück.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriff(e) für die Volltextsuche, z.B. 'laesio enormis', 'Bereicherung Lebensgemeinschaft'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl der Ergebnisse (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_rechtssatz",
            description="Ruft einen spezifischen OGH-Rechtssatz direkt ab anhand seiner RS-Nummer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "rs_number": {
                        "type": "string",
                        "description": "Die RS-Nummer im Format 'RS0XXXXXX', z.B. 'RS0030258'"
                    }
                },
                "required": ["rs_number"]
            }
        ),
        Tool(
            name="search_ogh_entscheidungen",
            description="Durchsucht die OGH-Textentscheidungen (super_ris.te) mittels Volltext-Suche.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriff(e) für die Volltextsuche"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl der Ergebnisse (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_by_paragraph",
            description="Findet OGH-Rechtssätze zu einem bestimmten Gesetzesparagraphen.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {
                        "type": "string",
                        "description": "Paragraph im Format '§ 934 ABGB', '§ 351 UGB', '§ 1431 ABGB'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl der Ergebnisse (default: 15)",
                        "default": 15
                    }
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_by_schlagwort",
            description="Sucht Rechtssätze nach exaktem Schlagwort-Tag aus der OGH-Taxonomie.",
            inputSchema={
                "type": "object",
                "properties": {
                    "schlagwort": {
                        "type": "string",
                        "description": "Exaktes Schlagwort, z.B. 'Bereicherungsrecht', 'Schadenersatz', 'Laesio enormis'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl der Ergebnisse (default: 10)",
                        "default": 10
                    }
                },
                "required": ["schlagwort"]
            }
        ),
        Tool(
            name="hot_index_stats",
            description="Liefert Status/Counts des aktiven Hot-Zivil-Index (super_ris.hot_*_current).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="hot_rs_lookup",
            description="Direkter Lookup eines Hot-Rechtssatzes mit verknüpften TE-Mini-Stories aus dem aktiven Hot-Index.",
            inputSchema={
                "type": "object",
                "properties": {
                    "rs_number": {
                        "type": "string",
                        "description": "RS-Nummer, z.B. RS0037089"
                    },
                    "te_limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl TE-Mini-Stories (default: 5, max: 20)",
                        "default": 5
                    }
                },
                "required": ["rs_number"]
            }
        ),
        Tool(
            name="hot_rs_search",
            description="FTS-Suche im aktiven Hot-Zivil-Index (super_ris.hot_rs_current) mit Ranking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriff(e), z.B. 'Schadenersatz', 'Laesio enormis'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl Ergebnisse (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="hot_cluster_context",
            description="Liefert Grounding-Kontext für einen Hot-Index-Cluster: Cluster-Metadaten, Top-RS und TE-Mini-Stories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cluster_id": {
                        "type": "string",
                        "description": "Cluster-ID aus dem Hot-Index, z.B. 'AGB_GELTUNGSKONTROLLE'"
                    },
                    "topic_id": {
                        "type": "string",
                        "description": "Optionaler Topic-Filter zur Absicherung des Clusters"
                    },
                    "rs_limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl RS im Kontext (default: 10, max: 30)",
                        "default": 10
                    },
                    "te_limit_per_rs": {
                        "type": "integer",
                        "description": "Maximale Anzahl TE-Mini-Stories pro RS (default: 3, max: 10)",
                        "default": 3
                    }
                },
                "required": ["cluster_id"]
            }
        ),
        Tool(
            name="search_kommentar_paragraph",
            description="Sucht Kommentar-Artikel (kommentar.artikel) nach Paragraphenreferenz, bevorzugt aktuelle Fassungen (is_latest).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {
                        "type": "string",
                        "description": "Paragraphenreferenz, z.B. '§ 934 ABGB'"
                    },
                    "law": {
                        "type": "string",
                        "description": "Optionaler Gesetzesfilter (z.B. 'ABGB')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl Ergebnisse (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_kommentar_keyword",
            description="Sucht Kommentar-Artikel (kommentar.artikel) nach Keyword, bevorzugt aktuelle Fassungen (is_latest).",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword, z.B. 'Laesio enormis', 'Schadenersatz'"
                    },
                    "law": {
                        "type": "string",
                        "description": "Optionaler Gesetzesfilter (z.B. 'ABGB')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl Ergebnisse (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="search_lehrbuch",
            description="Durchsucht Lehrbuch-Inhalte (PSK Perner/Spitzer/Kodek + Riedler Schuldrecht) via Volltextsuche. Liefert Kapitel, Abschnitt, §-Referenzen und Textauszug.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriff(e) für die Volltextsuche, z.B. 'Gutgläubiger Erwerb', 'Bereicherung Kondiktionstypen'"
                    },
                    "rechtsgebiet": {
                        "type": "string",
                        "description": "Optional: Filter nach Rechtsgebiet (SCHADENERSATZ, SACHENRECHT, BEREICHERUNGSRECHT, VERTRAEGE, SCHULDRECHT_AT, MEHRPERSONAL, FAMILIENRECHT, INTERNATIONALE_BEZUEGE, GOA, SCHULDRECHT_BT)"
                    },
                    "werk": {
                        "type": "string",
                        "description": "Optional: Filter nach Werk (PSK oder RIEDLER)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl der Ergebnisse (default: 5, max: 20)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
    ]


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool call."""

    if name == "ask_gemini_zivilrecht":
        result = await ask_gemini(arguments.get("question", ""), arguments.get("context", ""))
        return [TextContent(type="text", text=result)]

    elif name == "search_ogh_rechtssaetze":
        result = search_rs_fulltext(arguments.get("query", ""), arguments.get("limit", 10))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_rechtssatz":
        result = get_rs_by_number(arguments.get("rs_number", ""))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_ogh_entscheidungen":
        result = search_te_fulltext(arguments.get("query", ""), arguments.get("limit", 5))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_by_paragraph":
        result = search_by_paragraph(arguments.get("paragraph", ""), arguments.get("limit", 15))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_by_schlagwort":
        result = search_by_schlagwort(arguments.get("schlagwort", ""), arguments.get("limit", 10))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "hot_index_stats":
        result = hot_index_stats()
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "hot_rs_lookup":
        result = hot_rs_lookup(arguments.get("rs_number", ""), arguments.get("te_limit", 5))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "hot_rs_search":
        result = hot_rs_search(arguments.get("query", ""), arguments.get("limit", 10))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "hot_cluster_context":
        result = hot_cluster_context(
            arguments.get("cluster_id", ""),
            arguments.get("topic_id", ""),
            arguments.get("rs_limit", 10),
            arguments.get("te_limit_per_rs", 3),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_kommentar_paragraph":
        result = search_kommentar_paragraph(
            arguments.get("paragraph", ""),
            arguments.get("law", ""),
            arguments.get("limit", 10),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_kommentar_keyword":
        result = search_kommentar_keyword(
            arguments.get("keyword", ""),
            arguments.get("law", ""),
            arguments.get("limit", 10),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_lehrbuch":
        result = search_lehrbuch(
            arguments.get("query", ""),
            arguments.get("rechtsgebiet", ""),
            arguments.get("werk", ""),
            arguments.get("limit", 5),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def ask_gemini(question: str, context: str = "") -> str:
    """Call the fine-tuned Gemini Pro model."""
    def _resolve_access_token() -> tuple[str | None, str | None]:
        explicit_token = os.getenv("VERTEX_ACCESS_TOKEN", "").strip()
        if explicit_token:
            return explicit_token, None
        if google_auth_default is None or GoogleAuthRequest is None:
            return None, "google-auth package is missing."
        try:
            credentials, _ = google_auth_default(scopes=list(VERTEX_AUTH_SCOPES))
            if not credentials.valid:
                credentials.refresh(GoogleAuthRequest())
            token = (credentials.token or "").strip()
            if not token:
                return None, "No access token returned from application default credentials."
            return token, None
        except Exception as exc:
            return None, str(exc)

    token, token_error = await asyncio.to_thread(_resolve_access_token)
    if not token:
        return (
            "Authentication error for Vertex AI. "
            f"Details: {token_error or 'unknown error'}. "
            "Set application default credentials or VERTEX_ACCESS_TOKEN."
        )

    url = f"https://{VERTEX_REGION}-aiplatform.googleapis.com/v1/projects/{VERTEX_PROJECT_ID}/locations/{VERTEX_REGION}/endpoints/{VERTEX_ENDPOINT_ID}:generateContent"

    # Build prompt
    if context:
        full_prompt = f"Sachverhalt:\n{context}\n\nFrage:\n{question}"
    else:
        full_prompt = question

    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096
        }
    }

    try:
        timeout = aiohttp.ClientTimeout(total=190)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                raw = await response.text()
                if response.status >= 400:
                    return f"Vertex request failed ({response.status}): {raw[:600]}"
                parsed = json.loads(raw)
                if "candidates" in parsed:
                    return parsed["candidates"][0]["content"]["parts"][0]["text"]
                return f"Error: {parsed.get('error', 'Unknown error')}"
    except json.JSONDecodeError:
        return "Error parsing Vertex response."
    except Exception as exc:
        return f"Vertex request exception: {exc}"


def search_rs_fulltext(query: str, limit: int) -> dict:
    """Full-text search in RS using the indexed summary tsvector."""
    limit = min(limit, 50)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        content_filter = rs_content_filter_sql()
        cursor.execute(f"""
            WITH q AS (
                SELECT plainto_tsquery('german', %s) AS tsq
            )
            SELECT rs_number,
                   COALESCE(rechtssatz_volltext, kurzinformation) as rechtssatz,
                   rechtsgebiet_primary, schlagworte,
                   ts_rank(kurzinformation_tsv, q.tsq) as rank
            FROM super_ris.rs, q
            WHERE {content_filter}
              AND kurzinformation_tsv @@ q.tsq
            ORDER BY rank DESC
            LIMIT %s
        """, (query, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "rs_number": row[0],
                "rechtssatz": (row[1] or "")[:800],
                "rechtsgebiet": row[2] or "",
                "schlagworte": row[3] or [],
                "relevance": round(float(row[4]), 3)
            })
        return {"results": results, "count": len(results), "query": query}
    finally:
        cursor.close()


def get_rs_by_number(rs_number: str) -> dict:
    """Get specific RS by number with full Rechtssatz text."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        content_filter = rs_content_filter_sql()
        cursor.execute(f"""
            SELECT rs_number,
                   COALESCE(rechtssatz_volltext, kurzinformation) as rechtssatz,
                   rechtsgebiet_primary, schlagworte,
                   fachgebiete, entscheidungsdatum
            FROM super_ris.rs
            WHERE rs_number = %s
              AND {content_filter}
        """, (rs_number,))

        row = cursor.fetchone()
        if row:
            return {
                "found": True,
                "rs_number": row[0],
                "rechtssatz": row[1] or "",
                "rechtsgebiet": row[2] or "",
                "schlagworte": row[3] or [],
                "fachgebiete": row[4] or [],
                "datum": str(row[5]) if row[5] else None
            }
        cursor.execute("SELECT 1 FROM super_ris.rs WHERE rs_number = %s", (rs_number,))
        if cursor.fetchone():
            return {"found": False, "rs_number": rs_number, "reason": "no_content_available"}
        return {"found": False, "rs_number": rs_number}
    finally:
        cursor.close()


def search_te_fulltext(query: str, limit: int) -> dict:
    """Full-text search in TE."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT stable_key, normalized_gz, entscheidungsdatum, summary
            FROM super_ris.te
            WHERE to_tsvector('german', COALESCE(summary, ''))
                  @@ plainto_tsquery('german', %s)
            LIMIT %s
        """, (query, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "stable_key": row[0],
                "geschaeftszahl": row[1],
                "datum": str(row[2]) if row[2] else None,
                "summary": (row[3] or "")[:300]
            })
        return {"results": results, "count": len(results), "query": query}
    finally:
        cursor.close()


def search_by_paragraph(paragraph: str, limit: int) -> dict:
    """Search RS related to a specific paragraph."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        content_filter = rs_content_filter_sql()
        cursor.execute(f"""
            SELECT rs_number, kurzinformation, schlagworte
            FROM super_ris.rs
            WHERE {content_filter}
              AND kurzinformation ILIKE %s
            LIMIT %s
        """, (f"%{paragraph}%", limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "rs_number": row[0],
                "kernaussage": (row[1] or "")[:400],
                "schlagworte": row[2] or []
            })
        return {"paragraph": paragraph, "results": results, "count": len(results)}
    finally:
        cursor.close()


def search_by_schlagwort(schlagwort: str, limit: int) -> dict:
    """Search RS by Schlagwort tag."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        content_filter = rs_content_filter_sql()
        cursor.execute(f"""
            SELECT rs_number, kurzinformation, rechtsgebiet_primary, schlagworte
            FROM super_ris.rs
            WHERE {content_filter}
              AND %s = ANY(schlagworte)
            LIMIT %s
        """, (schlagwort, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "rs_number": row[0],
                "kernaussage": (row[1] or "")[:400],
                "rechtsgebiet": row[2] or "",
                "schlagworte": row[3] or []
            })
        return {"schlagwort": schlagwort, "results": results, "count": len(results)}
    finally:
        cursor.close()


def hot_index_stats() -> dict:
    """Return metadata and counts for the active hot index release."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT release_id, build_ts, rs_count, te_count, link_count, cluster_rs_count,
                   builder_version, is_active
            FROM super_ris.hot_release
            WHERE is_active = true
            ORDER BY build_ts DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return {"found": False, "reason": "no_active_hot_release"}

        cursor.execute(
            """
            SELECT
              (SELECT count(*) FROM super_ris.hot_rs_current),
              (SELECT count(*) FROM super_ris.hot_te_current),
              (SELECT count(*) FROM super_ris.hot_rs_te_link_current),
              (SELECT count(*) FROM super_ris.hot_cluster_rs_current)
            """
        )
        current_counts = cursor.fetchone()
        return {
            "found": True,
            "active_release": {
                "release_id": row[0],
                "build_ts": row[1].isoformat() if row[1] else None,
                "rs_count_manifest": row[2],
                "te_count_manifest": row[3],
                "link_count_manifest": row[4],
                "cluster_rs_count_manifest": row[5],
                "builder_version": row[6],
                "is_active": bool(row[7]),
            },
            "current_view_counts": {
                "hot_rs_current": current_counts[0],
                "hot_te_current": current_counts[1],
                "hot_rs_te_link_current": current_counts[2],
                "hot_cluster_rs_current": current_counts[3],
            },
        }
    finally:
        cursor.close()


def hot_rs_lookup(rs_number: str, te_limit: int) -> dict:
    """Lookup a single hot RS and return linked TE mini-stories."""
    rs_number = clamp_query(rs_number, 50).upper()
    te_limit = clamp_limit(te_limit, default=5, max_value=20)
    if not rs_number:
        return {"found": False, "reason": "missing_rs_number"}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT rs_number, rechtssatz_text, te_count, gericht, is_cluster_cited,
                   cluster_ids, topic_ids, hot_rank, selection_tier, release_id
            FROM super_ris.hot_rs_current
            WHERE rs_number = %s
            LIMIT 1
            """,
            (rs_number,),
        )
        row = cursor.fetchone()
        if not row:
            return {"found": False, "rs_number": rs_number}

        cursor.execute(
            """
            SELECT te_stable_key, gz, datum, gericht, mini_story
            FROM super_ris.hot_rs_te_link_current
            WHERE rs_number = %s
            ORDER BY datum DESC NULLS LAST, te_stable_key
            LIMIT %s
            """,
            (rs_number, te_limit),
        )
        te_rows = cursor.fetchall()
        te_items = [
            {
                "te_stable_key": r[0],
                "gz": r[1],
                "datum": str(r[2]) if r[2] else None,
                "gericht": r[3],
                "mini_story": (r[4] or "")[:700],
            }
            for r in te_rows
        ]

        return {
            "found": True,
            "rs": {
                "rs_number": row[0],
                "rechtssatz_text": row[1] or "",
                "te_count": row[2] or 0,
                "gericht": row[3] or "",
                "is_cluster_cited": bool(row[4]),
                "cluster_ids": row[5] or [],
                "topic_ids": row[6] or [],
                "hot_rank": row[7],
                "selection_tier": row[8],
                "release_id": row[9],
            },
            "te_items": te_items,
            "te_items_count": len(te_items),
        }
    finally:
        cursor.close()


def hot_rs_search(query: str, limit: int) -> dict:
    """FTS search over hot_rs_current using the indexed tsvector."""
    query = clamp_query(query)
    limit = clamp_limit(limit, default=10, max_value=50)
    if not query:
        return {"query": query, "count": 0, "results": []}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            WITH q AS (SELECT plainto_tsquery('german', %s) AS tsq)
            SELECT r.rs_number, r.rechtssatz_text, r.te_count, r.gericht,
                   r.is_cluster_cited, r.hot_rank, r.selection_tier,
                   ts_rank(r.fts_vec, q.tsq) AS rank
            FROM super_ris.hot_rs_current r, q
            WHERE r.fts_vec @@ q.tsq
            ORDER BY rank DESC, r.hot_rank NULLS LAST, r.rs_number
            LIMIT %s
            """,
            (query, limit),
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "rs_number": row[0],
                    "rechtssatz_text": (row[1] or "")[:900],
                    "te_count": row[2] or 0,
                    "gericht": row[3] or "",
                    "is_cluster_cited": bool(row[4]),
                    "hot_rank": row[5],
                    "selection_tier": row[6],
                    "relevance": round(float(row[7]), 4),
                }
            )
        return {"query": query, "count": len(results), "results": results}
    finally:
        cursor.close()


def hot_cluster_context(cluster_id: str, topic_id: str = "", rs_limit: int = 10, te_limit_per_rs: int = 3) -> dict:
    """Build cluster-grounding context from hot cluster -> hot RS -> TE mini stories."""
    cluster_id = clamp_query(cluster_id, 120)
    topic_id = clamp_query(topic_id, 120)
    rs_limit = clamp_limit(rs_limit, default=10, max_value=30)
    te_limit_per_rs = clamp_limit(te_limit_per_rs, default=3, max_value=10)
    if not cluster_id:
        return {"found": False, "reason": "missing_cluster_id"}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        params: list[Any] = [cluster_id]
        topic_filter = ""
        if topic_id:
            topic_filter = " AND c.topic_id = %s"
            params.append(topic_id)

        cursor.execute(
            f"""
            SELECT c.topic_id, c.cluster_id, c.keywords, c.min_keywords, c.minimal, c.rs_count
            FROM super_ris.hot_cluster_current c
            WHERE c.cluster_id = %s
              {topic_filter}
            LIMIT 1
            """,
            tuple(params),
        )
        cluster_row = cursor.fetchone()
        if not cluster_row:
            result = {"found": False, "cluster_id": cluster_id}
            if topic_id:
                result["topic_id"] = topic_id
            return result

        params = [cluster_id]
        topic_filter = ""
        if topic_id:
            topic_filter = " AND x.topic_id = %s"
            params.append(topic_id)
        params.append(rs_limit)

        cursor.execute(
            f"""
            SELECT r.rs_number, r.rechtssatz_text, r.te_count, r.gericht, r.is_cluster_cited,
                   r.cluster_ids, r.topic_ids, r.hot_rank, r.selection_tier, r.release_id
            FROM super_ris.hot_cluster_rs_current x
            JOIN super_ris.hot_rs_current r
              ON r.rs_number = x.rs_number
            WHERE x.cluster_id = %s
              {topic_filter}
            ORDER BY r.hot_rank NULLS LAST, r.te_count DESC, r.rs_number
            LIMIT %s
            """,
            tuple(params),
        )
        rs_rows = cursor.fetchall()
        rs_numbers = [row[0] for row in rs_rows]
        te_by_rs: dict[str, list[dict[str, Any]]] = {rsn: [] for rsn in rs_numbers}

        if rs_numbers:
            cursor.execute(
                """
                SELECT rs_number, te_stable_key, gz, datum, gericht, mini_story
                FROM super_ris.hot_rs_te_link_current
                WHERE rs_number = ANY(%s)
                ORDER BY rs_number, datum DESC NULLS LAST, te_stable_key
                """,
                (rs_numbers,),
            )
            for row in cursor.fetchall():
                bucket = te_by_rs.get(row[0])
                if bucket is None or len(bucket) >= te_limit_per_rs:
                    continue
                bucket.append(
                    {
                        "te_stable_key": row[1],
                        "gz": row[2],
                        "datum": str(row[3]) if row[3] else None,
                        "gericht": row[4],
                        "mini_story": (row[5] or "")[:700],
                    }
                )

        rs_items = []
        for row in rs_rows:
            rs_items.append(
                {
                    "rs_number": row[0],
                    "rechtssatz_text": (row[1] or "")[:1000],
                    "te_count": row[2] or 0,
                    "gericht": row[3] or "",
                    "is_cluster_cited": bool(row[4]),
                    "cluster_ids": row[5] or [],
                    "topic_ids": row[6] or [],
                    "hot_rank": row[7],
                    "selection_tier": row[8],
                    "release_id": row[9],
                    "te_items": te_by_rs.get(row[0], []),
                }
            )

        return {
            "found": True,
            "cluster": {
                "topic_id": cluster_row[0],
                "cluster_id": cluster_row[1],
                "keywords": cluster_row[2] or [],
                "min_keywords": cluster_row[3] or 0,
                "minimal": bool(cluster_row[4]),
                "rs_count": cluster_row[5] or 0,
            },
            "rs_limit": rs_limit,
            "te_limit_per_rs": te_limit_per_rs,
            "rs_returned": len(rs_items),
            "rs_items": rs_items,
        }
    finally:
        cursor.close()


def search_kommentar_paragraph(paragraph: str, law: str = "", limit: int = 10) -> dict:
    """Search kommentar.artikel by paragraph_ref (prefer exact + latest)."""
    paragraph = clamp_query(paragraph, 200)
    law = clamp_query(law, 50)
    limit = clamp_limit(limit, default=10, max_value=50)
    if not paragraph:
        return {"paragraph": paragraph, "law": law or None, "count": 0, "results": []}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        law_filter = ""
        params: list[Any] = [paragraph]
        if law:
            law_filter = " AND lower(coalesce(a.law, '')) = lower(%s)"
            params.append(law)
        params.append(limit)

        cursor.execute(
            f"""
            SELECT a.id, a.werk_id, a.paragraph_ref, a.keyword, a.title, a.law,
                   a.doc_type, a.rechtsgebiet, a.stand_date, a.is_latest, a.auf_einen_blick
            FROM kommentar.artikel a
            WHERE a.is_latest = true
              AND a.paragraph_ref = %s
              {law_filter}
            ORDER BY a.werk_id, a.id
            LIMIT %s
            """,
            tuple(params),
        )
        rows = cursor.fetchall()

        # fallback for minor formatting differences (e.g. spacing) if exact has no result
        if not rows:
            params = [f"%{paragraph}%", limit]
            law_filter2 = ""
            if law:
                params = [f"%{paragraph}%", law, limit]
                law_filter2 = " AND lower(coalesce(a.law, '')) = lower(%s)"
            cursor.execute(
                f"""
                SELECT a.id, a.werk_id, a.paragraph_ref, a.keyword, a.title, a.law,
                       a.doc_type, a.rechtsgebiet, a.stand_date, a.is_latest, a.auf_einen_blick
                FROM kommentar.artikel a
                WHERE a.is_latest = true
                  AND a.paragraph_ref ILIKE %s
                  {law_filter2}
                ORDER BY a.werk_id, a.id
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cursor.fetchall()

        results = [
            {
                "artikel_id": r[0],
                "werk_id": r[1],
                "paragraph_ref": r[2],
                "keyword": r[3],
                "title": r[4],
                "law": r[5],
                "doc_type": r[6],
                "rechtsgebiet": r[7],
                "stand_date": str(r[8]) if r[8] else None,
                "is_latest": bool(r[9]),
                "auf_einen_blick": (r[10] or "")[:500],
            }
            for r in rows
        ]
        return {"paragraph": paragraph, "law": law or None, "count": len(results), "results": results}
    finally:
        cursor.close()


def search_kommentar_keyword(keyword: str, law: str = "", limit: int = 10) -> dict:
    """Search kommentar.artikel by keyword (prefer exact + latest)."""
    keyword = clamp_query(keyword, 200)
    law = clamp_query(law, 50)
    limit = clamp_limit(limit, default=10, max_value=50)
    if not keyword:
        return {"keyword": keyword, "law": law or None, "count": 0, "results": []}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        law_filter = ""
        params: list[Any] = [keyword]
        if law:
            law_filter = " AND lower(coalesce(a.law, '')) = lower(%s)"
            params.append(law)
        params.append(limit)

        cursor.execute(
            f"""
            SELECT a.id, a.werk_id, a.paragraph_ref, a.keyword, a.title, a.law,
                   a.doc_type, a.rechtsgebiet, a.stand_date, a.is_latest, a.auf_einen_blick
            FROM kommentar.artikel a
            WHERE a.is_latest = true
              AND a.keyword = %s
              {law_filter}
            ORDER BY a.werk_id, a.id
            LIMIT %s
            """,
            tuple(params),
        )
        rows = cursor.fetchall()

        if not rows:
            params = [f"%{keyword}%", limit]
            law_filter2 = ""
            if law:
                params = [f"%{keyword}%", law, limit]
                law_filter2 = " AND lower(coalesce(a.law, '')) = lower(%s)"
            cursor.execute(
                f"""
                SELECT a.id, a.werk_id, a.paragraph_ref, a.keyword, a.title, a.law,
                       a.doc_type, a.rechtsgebiet, a.stand_date, a.is_latest, a.auf_einen_blick
                FROM kommentar.artikel a
                WHERE a.is_latest = true
                  AND a.keyword ILIKE %s
                  {law_filter2}
                ORDER BY a.werk_id, a.id
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cursor.fetchall()

        results = [
            {
                "artikel_id": r[0],
                "werk_id": r[1],
                "paragraph_ref": r[2],
                "keyword": r[3],
                "title": r[4],
                "law": r[5],
                "doc_type": r[6],
                "rechtsgebiet": r[7],
                "stand_date": str(r[8]) if r[8] else None,
                "is_latest": bool(r[9]),
                "auf_einen_blick": (r[10] or "")[:500],
            }
            for r in rows
        ]
        return {"keyword": keyword, "law": law or None, "count": len(results), "results": results}
    finally:
        cursor.close()


# ============================================================================
# LEHRBUCH SEARCH
# ============================================================================

def search_lehrbuch(query: str, rechtsgebiet: str = "", werk: str = "", limit: int = 5) -> dict:
    """Search lehrbuch sections via FTS, return kapitel, titel, excerpt, §-refs."""
    query = clamp_query(query)
    limit = clamp_limit(limit, 5, 20)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        where_clauses = ["fts_vector @@ plainto_tsquery('german', %s)"]
        params: list = [query]
        if rechtsgebiet:
            where_clauses.append("rechtsgebiet = %s")
            params.append(rechtsgebiet.upper())
        if werk:
            where_clauses.append("werk = %s")
            params.append(werk.upper())
        where = " AND ".join(where_clauses)
        params.append(limit)

        cursor.execute(f"""
            SELECT id, werk, kapitel, rechtsgebiet, abschnitt_nr, titel,
                   seite_von, seite_bis, paragraph_refs, char_count,
                   ts_rank(fts_vector, plainto_tsquery('german', %s)) as rank,
                   ts_headline('german', text, plainto_tsquery('german', %s),
                               'StartSel=**,StopSel=**,MaxWords=60,MinWords=20') as excerpt
            FROM lehrbuch.abschnitt
            WHERE {where}
            ORDER BY rank DESC
            LIMIT %s
        """, [query, query] + params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "werk": row[1],
                "kapitel": row[2],
                "rechtsgebiet": row[3],
                "abschnitt_nr": row[4],
                "titel": row[5],
                "seite_von": row[6],
                "seite_bis": row[7],
                "paragraph_refs": row[8],
                "char_count": row[9],
                "rank": round(row[10], 4),
                "excerpt": row[11],
            })

        return {"query": query, "rechtsgebiet": rechtsgebiet or None, "werk": werk or None,
                "count": len(results), "results": results}
    finally:
        cursor.close()


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
