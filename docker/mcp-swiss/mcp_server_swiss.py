#!/usr/bin/env python3
"""
MCP Server für Schweizerisches Recht.

Bietet Tools für:
- PostgreSQL Datenbank (swiss.bger)
- Direkter Zugriff auf Entscheide des Bundesgerichts

Installation:
  pip install mcp psycopg2-binary
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import psycopg2

# Make repo-local Swiss Core importable when running this MCP script directly.
_resolved_self = Path(__file__).resolve()
for _candidate in [_resolved_self.parent] + list(_resolved_self.parents):
    if (_candidate / "swiss_core").exists():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break

from swiss_core.errors import SwissCoreError, SwissIdentifierNotFoundError
from swiss_core.identifiers import resolve_swiss_identifier as core_resolve_swiss_identifier
from swiss_core.retrieval import get_swiss_entscheidung_metadata as core_get_swiss_entscheidung_metadata
from swiss_core.retrieval import get_swiss_entscheidung_text as core_get_swiss_entscheidung_text
from swiss_core.retrieval import build_swiss_case_pack as core_build_swiss_case_pack
from swiss_core.retrieval import analyze_swiss_issue as core_analyze_swiss_issue
from swiss_core.retrieval import read_swiss_decision_passages as core_read_swiss_decision_passages
from swiss_core.retrieval import search_swiss_by_norm_refs as core_search_swiss_by_norm_refs
from swiss_core.retrieval import search_swiss_entscheidungen as core_search_swiss_entscheidungen

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP not installed. Install with: pip install mcp")
    exit(1)

# Configuration
DB_CONFIG = {
    "host": os.getenv("MCP_SWISS_DB_HOST", "localhost"),
    "port": int(os.getenv("MCP_SWISS_DB_PORT", "5432")),
    "dbname": os.getenv("MCP_SWISS_DB_NAME", "super_ris_ch"),
    "user": os.getenv("MCP_SWISS_DB_USER", "reinhardberger"),
    "connect_timeout": int(os.getenv("MCP_SWISS_DB_CONNECT_TIMEOUT", "10")),
}
if os.getenv("MCP_SWISS_DB_PASSWORD"):
    DB_CONFIG["password"] = os.getenv("MCP_SWISS_DB_PASSWORD")
if os.getenv("MCP_SWISS_DB_SSLMODE"):
    DB_CONFIG["sslmode"] = os.getenv("MCP_SWISS_DB_SSLMODE")

# Initialize MCP Server
server = Server("swiss-server")

# Database connection (lazy initialization)
_db_conn = None

def get_db_connection():
    """Get or create database connection."""
    global _db_conn
    if _db_conn is None or _db_conn.closed:
        _db_conn = psycopg2.connect(**DB_CONFIG)
        _db_conn.autocommit = True
    return _db_conn


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_swiss_entscheidungen",
            description="Durchsucht Entscheide des Schweizerischen Bundesgerichts in ch_core.decisions (R1) mittels Volltext + Filter. Gibt Metadaten und Snippets zurück.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriff(e) für die Volltextsuche, z.B. 'Kündigung', 'Haftung'"
                    },
                    "sprache": {
                        "type": "string",
                        "description": "Sprachfilter: 'de' (Deutsch), 'fr' (Französisch), 'it' (Italienisch). Default: 'de'",
                        "default": "de"
                    },
                    "rechtsgebiet": {
                        "type": "string",
                        "description": "Optionaler Filter auf primäres Rechtsgebiet (z.B. 'Zivilrecht')"
                    },
                    "year_from": {
                        "type": "integer",
                        "description": "Optionaler Start-Jahrfilter"
                    },
                    "year_to": {
                        "type": "integer",
                        "description": "Optionaler End-Jahrfilter"
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
        Tool(
            name="get_swiss_entscheidung",
            description="Kompatibilitäts-Tool: ruft einen spezifischen Entscheid anhand seiner Geschäftszahl ab (liefert weiterhin Textausschnitt).",
            inputSchema={
                "type": "object",
                "properties": {
                    "geschaeftszahl": {
                        "type": "string",
                        "description": "Die Geschäftszahl, z.B. '8C_391/2021'"
                    }
                },
                "required": ["geschaeftszahl"]
            }
        ),
        Tool(
            name="resolve_swiss_identifier",
            description="Löst Swiss-Identifiers (stable_key, Geschäftszahl, normalisierte GZ, BGE-Zitat) auf stable_key(s) auf.",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "z.B. CH_4A_166/2021_2021-09-22, 4A_166/2021 oder BGE 145 III 213"
                    }
                },
                "required": ["identifier"]
            }
        ),
        Tool(
            name="get_swiss_entscheidung_metadata",
            description="R1 Metadata-first Tool: liefert Metadaten, Statusflags, Regesta (falls vorhanden) und Identifier-Auflösung.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stable_key": {
                        "type": "string",
                        "description": "Interner canonical identifier (optional, alternativ identifier)"
                    },
                    "identifier": {
                        "type": "string",
                        "description": "Alternativer Identifier (GZ / BGE / stable_key)"
                    },
                    "include_regesta": {
                        "type": "boolean",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="read_swiss_decision_passages",
            description="Liest Passagen eines Entscheids aus ch_core.passages; optional query-fokussiert gerankt (R1 Passagen-Workflow).",
            inputSchema={
                "type": "object",
                "properties": {
                    "stable_key": {
                        "type": "string",
                        "description": "Canonical decision identifier"
                    },
                    "identifier": {
                        "type": "string",
                        "description": "Alternative ID (GZ/BGE/stable_key)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Optionaler Fokusbegriff für Passage-Ranking"
                    },
                    "section_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optionaler Filter, z.B. ['erwaegung','dispositiv']"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5
                    }
                }
            }
        ),
        Tool(
            name="search_swiss_by_norm",
            description="Sucht Entscheide anhand normalisierter Normreferenzen in ch_core.norm_refs (R1 vorbereitet; benötigt befüllte Normextraktion).",
            inputSchema={
                "type": "object",
                "properties": {
                    "citation": {
                        "type": "string",
                        "description": "z.B. 'Art. 41 OR', 'CO 41', 'Art. 6 EMRK'"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10
                    }
                },
                "required": ["citation"]
            }
        ),
        Tool(
            name="build_swiss_case_pack",
            description="Erstellt ein strukturiertes Recherchepaket (Treffer + bevorzugte Regesten + relevante Passagen + Normreferenzen) fuer eine Schweizer Rechtsfrage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Juristische Suchfrage (Stichwoerter / Problemstellung)"
                    },
                    "sprache": {
                        "type": "string",
                        "description": "Sprachfilter ('de','fr','it'), default 'de'",
                        "default": "de"
                    },
                    "rechtsgebiet": {
                        "type": "string",
                        "description": "Optionaler Filter auf primäres Rechtsgebiet"
                    },
                    "year_from": {"type": "integer"},
                    "year_to": {"type": "integer"},
                    "limit_decisions": {
                        "type": "integer",
                        "description": "Anzahl Top-Entscheide (default 5, max 10)",
                        "default": 5
                    },
                    "passages_per_decision": {
                        "type": "integer",
                        "description": "Anzahl relevanter Passagen pro Entscheid (default 3, max 10)",
                        "default": 3
                    },
                    "section_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optionaler Passage-Filter, z.B. ['erwaegung','dispositiv']"
                    },
                    "include_norm_refs": {"type": "boolean", "default": True},
                    "include_regesta": {"type": "boolean", "default": True}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="analyze_swiss_issue",
            description="Deterministisches Composite-Tool: erstellt ein quellengebundenes Voranalyse-Paket (Authorities, Normen, Kernpunkte) auf Basis von build_swiss_case_pack.",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue_query": {
                        "type": "string",
                        "description": "Rechtsfrage / Suchproblemstellung"
                    },
                    "facts": {
                        "type": "string",
                        "description": "Optionaler Sachverhaltstext (für Normhinweise/Folgequeries)"
                    },
                    "sprache": {"type": "string", "default": "de"},
                    "rechtsgebiet": {"type": "string"},
                    "year_from": {"type": "integer"},
                    "year_to": {"type": "integer"},
                    "limit_decisions": {"type": "integer", "default": 5},
                    "passages_per_decision": {"type": "integer", "default": 3},
                    "section_types": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "include_case_pack": {"type": "boolean", "default": True}
                },
                "required": ["issue_query"]
            }
        )
    ]


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool call."""

    if name == "search_swiss_entscheidungen":
        result = search_swiss_fulltext(
            arguments.get("query", ""),
            arguments.get("sprache", "de"),
            arguments.get("limit", 5),
            arguments.get("rechtsgebiet"),
            arguments.get("year_from"),
            arguments.get("year_to"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_swiss_entscheidung":
        result = get_swiss_by_gz(arguments.get("geschaeftszahl", ""))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "resolve_swiss_identifier":
        result = resolve_identifier_tool(arguments.get("identifier", ""))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_swiss_entscheidung_metadata":
        result = get_swiss_metadata_tool(
            stable_key=arguments.get("stable_key"),
            identifier=arguments.get("identifier"),
            include_regesta=arguments.get("include_regesta", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_swiss_by_norm":
        result = search_swiss_by_norm(
            arguments.get("citation", ""),
            arguments.get("limit", 10),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "read_swiss_decision_passages":
        result = read_swiss_decision_passages_tool(
            stable_key=arguments.get("stable_key"),
            identifier=arguments.get("identifier"),
            query=arguments.get("query"),
            section_types=arguments.get("section_types"),
            limit=arguments.get("limit", 5),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "build_swiss_case_pack":
        result = build_swiss_case_pack_tool(
            query=arguments.get("query", ""),
            sprache=arguments.get("sprache", "de"),
            rechtsgebiet=arguments.get("rechtsgebiet"),
            year_from=arguments.get("year_from"),
            year_to=arguments.get("year_to"),
            limit_decisions=arguments.get("limit_decisions", 5),
            passages_per_decision=arguments.get("passages_per_decision", 3),
            section_types=arguments.get("section_types"),
            include_norm_refs=arguments.get("include_norm_refs", True),
            include_regesta=arguments.get("include_regesta", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "analyze_swiss_issue":
        result = analyze_swiss_issue_tool(
            issue_query=arguments.get("issue_query", ""),
            facts=arguments.get("facts"),
            sprache=arguments.get("sprache", "de"),
            rechtsgebiet=arguments.get("rechtsgebiet"),
            year_from=arguments.get("year_from"),
            year_to=arguments.get("year_to"),
            limit_decisions=arguments.get("limit_decisions", 5),
            passages_per_decision=arguments.get("passages_per_decision", 3),
            section_types=arguments.get("section_types"),
            include_case_pack=arguments.get("include_case_pack", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


def search_swiss_fulltext(
    query: str,
    sprache: str,
    limit: int,
    rechtsgebiet: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> dict:
    """R1 full-text search over ch_core.decisions with metadata filters."""
    try:
        conn = get_db_connection()
        core_result = core_search_swiss_entscheidungen(
            query=query,
            sprache=sprache,
            rechtsgebiet=rechtsgebiet,
            year_from=year_from,
            year_to=year_to,
            limit=min(limit, 20),
            offset=0,
            conn=conn,
            db_config=DB_CONFIG,
        )
        results = []
        for row in core_result.get("results", []):
            results.append(
                {
                    "stable_key": row.get("stable_key"),
                    "geschaeftszahl": row.get("geschaeftszahl"),
                    "datum": row.get("entscheidungsdatum"),
                    "gericht": row.get("gericht") or "",
                    "rechtsgebiet": row.get("rechtsgebiet_primary") or "",
                    "sprache": row.get("sprache") or "",
                    "bge_citation": row.get("bge_citation"),
                    "snippet": row.get("snippet") or "",
                    "relevance": round(float(row["relevance"]), 3) if row.get("relevance") is not None else None,
                    "fts_relevance": round(float(row["fts_relevance"]), 3) if row.get("fts_relevance") is not None else None,
                    "ranking_bonus": round(float(row["ranking_bonus"]), 3) if row.get("ranking_bonus") is not None else None,
                    "rank_signals": row.get("rank_signals") or {},
                }
            )
        return {
            "results": results,
            "count": len(results),
            "query": core_result.get("query"),
            "sprache": core_result.get("sprache"),
            "rechtsgebiet": core_result.get("rechtsgebiet_primary"),
            "year_from": core_result.get("year_from"),
            "year_to": core_result.get("year_to"),
            "total": core_result.get("total"),
            "ranking_strategy": core_result.get("ranking_strategy"),
        }
    except SwissCoreError as exc:
        return {"results": [], "count": 0, "query": query, "error": str(exc)}
    except Exception as exc:
        return {"results": [], "count": 0, "query": query, "error": f"unexpected error: {exc}"}


def get_swiss_by_gz(gz: str) -> dict:
    """Compatibility get-by-GZ over ch_core.decisions (returns text excerpt + metadata)."""
    try:
        conn = get_db_connection()
        payload = core_get_swiss_entscheidung_text(
            identifier=gz,
            truncate_chars=35000,
            conn=conn,
            db_config=DB_CONFIG,
        )
        return {
            "found": True,
            "stable_key": payload.get("stable_key"),
            "geschaeftszahl": payload.get("geschaeftszahl"),
            "datum": payload.get("entscheidungsdatum"),
            "gericht": payload.get("gericht") or "",
            "rechtsgebiet": payload.get("rechtsgebiet") or "",
            "sprache": payload.get("sprache") or "",
            "text_content": payload.get("content") or "",
            "source_url": payload.get("source_url") or "",
            "content_status": payload.get("content_status") or "",
            "bge_citation": payload.get("bge_citation"),
        }
    except SwissIdentifierNotFoundError:
        return {"found": False, "geschaeftszahl": gz}
    except SwissCoreError as exc:
        return {"found": False, "geschaeftszahl": gz, "error": str(exc)}
    except Exception as exc:
        return {"found": False, "geschaeftszahl": gz, "error": f"unexpected error: {exc}"}


def resolve_identifier_tool(identifier: str) -> dict:
    """MCP wrapper around Swiss Core identifier resolution."""
    try:
        if not identifier or not str(identifier).strip():
            return {"ok": False, "error": "identifier is required"}
        conn = get_db_connection()
        resolved = core_resolve_swiss_identifier(str(identifier), conn=conn, db_config=DB_CONFIG)
        return {"ok": True, **resolved.to_dict()}
    except SwissCoreError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"unexpected error: {exc}"}


def get_swiss_metadata_tool(
    *,
    stable_key: Optional[str],
    identifier: Optional[str],
    include_regesta: bool = True,
) -> dict:
    """MCP wrapper around Swiss Core metadata-first retrieval."""
    try:
        conn = get_db_connection()
        result = core_get_swiss_entscheidung_metadata(
            stable_key=stable_key,
            identifier=identifier,
            include_regesta=include_regesta,
            conn=conn,
            db_config=DB_CONFIG,
        )
        return {"ok": True, "result": result}
    except SwissCoreError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"unexpected error: {exc}"}


def search_swiss_by_norm(citation: str, limit: int) -> dict:
    """Prepared R1 norm-centric search (works once ch_core.norm_refs is populated)."""
    try:
        conn = get_db_connection()
        return core_search_swiss_by_norm_refs(
            citation=citation,
            limit=limit,
            conn=conn,
            db_config=DB_CONFIG,
        )
    except SwissCoreError as exc:
        return {"results": [], "count": 0, "citation": citation, "error": str(exc)}
    except Exception as exc:
        return {"results": [], "count": 0, "citation": citation, "error": f"unexpected error: {exc}"}


def read_swiss_decision_passages_tool(
    *,
    stable_key: Optional[str],
    identifier: Optional[str],
    query: Optional[str],
    section_types,
    limit: int,
) -> dict:
    """MCP wrapper around Swiss Core passage reader."""
    try:
        conn = get_db_connection()
        return {
            "ok": True,
            "result": core_read_swiss_decision_passages(
                stable_key=stable_key,
                identifier=identifier,
                query=query,
                section_types=section_types,
                limit=limit,
                conn=conn,
                db_config=DB_CONFIG,
            ),
        }
    except SwissCoreError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"unexpected error: {exc}"}


def build_swiss_case_pack_tool(
    *,
    query: str,
    sprache: Optional[str],
    rechtsgebiet: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    limit_decisions: int,
    passages_per_decision: int,
    section_types,
    include_norm_refs: bool,
    include_regesta: bool,
) -> dict:
    """MCP wrapper around Swiss Core composite case pack builder."""
    try:
        conn = get_db_connection()
        return {
            "ok": True,
            "result": core_build_swiss_case_pack(
                query=query,
                sprache=sprache,
                rechtsgebiet=rechtsgebiet,
                year_from=year_from,
                year_to=year_to,
                limit_decisions=limit_decisions,
                passages_per_decision=passages_per_decision,
                section_types=section_types,
                include_norm_refs=include_norm_refs,
                include_regesta=include_regesta,
                conn=conn,
                db_config=DB_CONFIG,
            ),
        }
    except SwissCoreError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"unexpected error: {exc}"}


def analyze_swiss_issue_tool(
    *,
    issue_query: str,
    facts: Optional[str],
    sprache: Optional[str],
    rechtsgebiet: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    limit_decisions: int,
    passages_per_decision: int,
    section_types,
    include_case_pack: bool,
) -> dict:
    """MCP wrapper around Swiss Core issue analyzer."""
    try:
        conn = get_db_connection()
        return {
            "ok": True,
            "result": core_analyze_swiss_issue(
                issue_query=issue_query,
                facts=facts,
                sprache=sprache,
                rechtsgebiet=rechtsgebiet,
                year_from=year_from,
                year_to=year_to,
                limit_decisions=limit_decisions,
                passages_per_decision=passages_per_decision,
                section_types=section_types,
                include_case_pack=include_case_pack,
                conn=conn,
                db_config=DB_CONFIG,
            ),
        }
    except SwissCoreError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"unexpected error: {exc}"}


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
