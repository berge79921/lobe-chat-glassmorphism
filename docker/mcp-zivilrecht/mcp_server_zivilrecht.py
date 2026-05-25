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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
            description="Sucht Kommentar-Artikel zu einer Paragraphenreferenz quellenübergreifend: kommentar.artikel (ABGB-ON, Rummel, Lexis, WK2-StGB, ZPO-ON, EO3, UGB-ON etc.) UND public.wk_kommentare (KBB Koziol/Bydlinski/Bollenberger Kurzkommentar zum ABGB, WK²-StGB, etc.). Liefert pro Treffer Werk, Kommentator, RZ-Count.",
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
            name="search_kbb_randziffer",
            description="RZ-granulare Volltext-Suche im KBB-Kurzkommentar zum ABGB (Koziol/Bydlinski/Bollenberger, 3. Aufl. 2010) via public.wk_randziffern. Liefert pro Treffer: §, RZ-Nummer, Section, Volltext der RZ, alle erwähnten OGH-Geschäftszahlen, §-Cross-Refs. Geeignet für gezielte juristische Stichwort-Recherche.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriff(e) für FTS-Volltextsuche, z.B. 'culpa in contrahendo', 'Schutzwirkung Dritter'"
                    },
                    "paragraph": {
                        "type": "string",
                        "description": "Optional: §-Filter, z.B. '§ 1295 ABGB' für RZ nur aus diesem §"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximale Anzahl RZ-Treffer (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": ["query"]
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
        Tool(
            name="get_klang_artikel",
            description="Ruft einen vollständigen Klang³-Großkommentar-Artikel ab (alle Randziffern + Übersicht + Literatur). Klang³ = Fenyves/Kerschner/Vonkilch, 3. Aufl. Deckt ABGB (26 Bände, ~24.000 Rz), KSchG, EheG/EPG und AHG ab.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {
                        "type": "string",
                        "description": "Paragraph, z.B. '364', '§ 364', '364a', '§ 12a KSchG', '§ 1 ABGB'"
                    },
                    "law": {
                        "type": "string",
                        "description": "Gesetz: 'ABGB' (default), 'KSchG', 'EheG_EPG', 'AHG'. Wird ignoriert wenn im paragraph-String enthalten.",
                        "default": "ABGB"
                    }
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_klang_randziffer",
            description="Ruft eine einzelne Randziffer aus dem Klang³-Kommentar ab (Volltext + OGH-Zitate + RS-Zitate + Seitenangaben).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {
                        "type": "string",
                        "description": "Paragraph, z.B. '364', '§ 364 ABGB', '12a', '§ 12a KSchG'"
                    },
                    "rz_num": {
                        "type": "integer",
                        "description": "Randziffer-Nummer (positiver Integer)"
                    },
                    "law": {
                        "type": "string",
                        "description": "Gesetz: 'ABGB' (default), 'KSchG', 'EheG_EPG', 'AHG'",
                        "default": "ABGB"
                    }
                },
                "required": ["paragraph", "rz_num"]
            }
        ),
        Tool(
            name="search_klang_by_paragraph",
            description="Liefert Kurzübersicht eines Klang³-Artikels: Rz-Count, Autoren, Stand-Datum, erste 200 Zeichen jeder Rz (kein Volltext). Für initiale Orientierung vor get_klang_artikel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {
                        "type": "string",
                        "description": "Paragraph, z.B. '364', '§ 364 ABGB', '12a KSchG'"
                    },
                    "law": {
                        "type": "string",
                        "description": "Gesetz: 'ABGB' (default), 'KSchG', 'EheG_EPG', 'AHG'",
                        "default": "ABGB"
                    }
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_klang_keyword",
            description="Volltextsuche über alle Randziffern im Klang³-Großkommentar-Korpus (ABGB + KSchG + EheG_EPG + AHG). Case-insensitive Substring-Match; liefert §-Ref, Rz-Nummer, Snippet und Score (Anzahl Treffer).",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Suchbegriff, z.B. 'Laesio enormis', 'culpa in contrahendo', 'Eigentumsfreiheitsklage'"
                    },
                    "korpora": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Korpus-Filter, z.B. ['ABGB', 'KSchG']. Default: alle vier Korpora."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximale Ergebnisanzahl (default: 50, max: 200)",
                        "default": 50
                    }
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="get_leipziger_artikel",
            description="Ruft einen vollständigen Leipziger-Kommentar-zum-StGB Artikel ab (alle Randnummern + alle Fußnoten). LK-StGB 13. Aufl. de Gruyter (Cirener/Radtke/Rissing-van Saan/Rönnau). 18 Bände 13. Aufl. + 2 Bände 12. Aufl. (Ersatz für §§ 263-266b u. §§ 331-358).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string", "description": "Paragraph, z.B. '211', '§ 211', '263a', '§ 218a StGB'"},
                    "law": {"type": "string", "default": "StGB"},
                    "edition": {"type": "integer", "description": "Auflage (13 oder 12). Default: automatisch — 13. Aufl. bevorzugt, Fallback 12.", "default": None}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_leipziger_randziffer",
            description="Ruft eine einzelne Randnummer aus dem Leipziger-StGB ab (Volltext + Fußnoten + Zitiervorschlag).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string", "description": "Paragraph, z.B. '211', '§ 263a'"},
                    "rn_num": {"type": "integer", "description": "Randnummer-Nummer"},
                    "law": {"type": "string", "default": "StGB"},
                    "edition": {"type": "integer", "default": None},
                    "include_footnotes": {"type": "boolean", "description": "Fußnoten mit Volltext mitliefern (default true)", "default": True}
                },
                "required": ["paragraph", "rn_num"]
            }
        ),
        Tool(
            name="search_leipziger_by_paragraph",
            description="Kurzübersicht eines Leipziger-StGB-Artikels: rn_count, Autoren, Edition, 200-char-Snippet je Rn + Fußnoten-Anzahl. Für Orientierung vor get_leipziger_artikel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string"},
                    "law": {"type": "string", "default": "StGB"},
                    "edition": {"type": "integer", "default": None}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_leipziger_keyword",
            description="Volltextsuche über alle Leipziger-StGB-Randnummern. Optional inkl. Fußnoten-Texte (in_footnotes=true).",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "max_results": {"type": "integer", "default": 50},
                    "in_footnotes": {"type": "boolean", "description": "Auch Fußnoten-Texte durchsuchen", "default": False},
                    "edition": {"type": "integer", "default": None}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="get_vvg_artikel",
            description="Ruft einen vollständigen Bruck/Möller-VVG-Großkommentar Artikel ab (alle Randnummern + alle Fußnoten). 10. Aufl. (de Gruyter, Beckmann/Koch) für §§ 1-73 + 100-124; 9. Aufl. (A9) als Ersatz für §§ 74-99 + 125-216. 210 §§ extrahiert (97.2% Coverage von §§ 1-216), 11.766 Rn, 99.5% enriched.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string", "description": "Paragraph, z.B. '100', '§ 100', '§ 28 VVG', '7a'"},
                    "edition": {"type": "integer", "description": "Auflage (10 oder 9). Default: 10 bevorzugt, Fallback 9.", "default": None}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_vvg_randziffer",
            description="Ruft eine einzelne Randnummer aus dem Bruck/Möller VVG-Großkommentar ab (Volltext + Fußnoten + Zitiervorschlag).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string"},
                    "rn_num": {"type": "integer"},
                    "edition": {"type": "integer", "default": None},
                    "include_footnotes": {"type": "boolean", "default": True}
                },
                "required": ["paragraph", "rn_num"]
            }
        ),
        Tool(
            name="search_vvg_by_paragraph",
            description="Kurzübersicht eines VVG-Großkommentar-Artikels: rn_count, Autoren, Edition, 200-char-Snippet je Rn + Schlagworte. Für Orientierung vor get_vvg_artikel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string"},
                    "edition": {"type": "integer", "default": None}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_vvg_keyword",
            description="Volltextsuche über alle Bruck/Möller VVG-Großkommentar Randnummern. Optional inkl. Fußnoten-Texte. Deckt §§ 1-216 VVG + Bedingungswerke (AHB 2016, ARB 2010/2012, AKB 2015).",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "max_results": {"type": "integer", "default": 50},
                    "in_footnotes": {"type": "boolean", "default": False},
                    "edition": {"type": "integer", "default": None},
                    "include_bedingungen": {"type": "boolean", "description": "Auch AHB/ARB/AKB-Bedingungswerke durchsuchen", "default": True}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="get_vvg_bedingung",
            description="Ruft eine Klausel aus den VVG-Bedingungswerken ab (AHB 2016 / ARB 2010/2012 / AKB 2015). Werk + Klausel-ID nötig.",
            inputSchema={
                "type": "object",
                "properties": {
                    "werk": {"type": "string", "description": "AHB_2016 | ARB_2010 | AKB_2015", "enum": ["AHB_2016", "ARB_2010", "AKB_2015"]},
                    "klausel_id": {"type": "string", "description": "Klausel-ID, z.B. 'Ziff. 1', 'Ziff. 7.1', '§ 5' (ARB), 'A.1.2' (AKB)"}
                },
                "required": ["werk", "klausel_id"]
            }
        ),
        Tool(
            name="get_bk_vvg_artikel",
            description="Ruft einen vollständigen Artikel aus dem Berliner Kommentar zum VVG (Honsell 1999, Springer) ab. Pre-Reform-2008. Kommentiert deutsches UND österreichisches VVG gleichermaßen. 163 §§, 4.248 Rn, 4.373 unique Schlagworte. Wertvolle Ergänzung zu Bruck/Möller für DE-AT-Rechtsvergleich.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string", "description": "Paragraph, z.B. '1', '§ 12', '§ 100 VVG'"}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_bk_vvg_randziffer",
            description="Ruft eine einzelne Randnummer aus dem Berliner Kommentar VVG (Honsell 1999) ab. Zitiervorschlag-Format: BK/<AUTOR> § X VVG Rn Y.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string"},
                    "rn_num": {"type": "integer"}
                },
                "required": ["paragraph", "rn_num"]
            }
        ),
        Tool(
            name="search_bk_vvg_keyword",
            description="Volltextsuche im Berliner Kommentar VVG (Honsell 1999). Mit Mojibake-Toleranz für OCR-Schäden — 'österreich' findet auch 'Osterreich', 'für' findet auch 'fUr'/'fiir', 'Rücktritt' findet auch 'Riicktritt'. Findet DE+AT-VVG-Kommentare zu Begriffen wie 'OGH', 'Obliegenheit', 'Rückwärtsversicherung'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "max_results": {"type": "integer", "default": 50},
                    "mojibake_tolerant": {"type": "boolean", "description": "OCR-Umlaut-Varianten automatisch suchen (default true)", "default": True}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="search_at_praxis_keyword",
            description="Volltextsuche in AT-Versicherungsrechts-Praxisliteratur (9 Werke, 6.894 Chunks): Kainz/Michtner/Reisinger Kfz, Hartjes/Janker/Reisinger Haftpflicht, Kronsteiner Rechtsschutz, Maitz Unfall, Bührer/Nigl D&O+Cyber, Gisch/Reisinger Versicherungsvertragsrecht, Haslwanter Deckungsanspruch Haftpflicht, Jeremias § 12 VersVG, FS Fenyves. Schließt die AT-Spezialwerk-Lücke des BK/Bruck-Möller-Korpus.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "source_work": {"type": "string", "description": "Nur dieses Werk (z.B. 'jeremias_p12', 'kronsteiner_rs'); leer für alle"},
                    "max_results": {"type": "integer", "default": 30}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="find_at_praxis_by_paragraph",
            description="Reverse-Lookup: alle Chunks aus AT-Praxisliteratur die einen bestimmten § referenzieren. Z.B. 'find_at_praxis_by_paragraph(\"§ 12 VersVG\")' → alle Werke die § 12 zitieren (vor allem Jeremias).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string", "description": "§ N + Gesetz, z.B. '§ 12 VersVG', '§ 6 VersVG'"},
                    "max_results": {"type": "integer", "default": 30}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="get_at_praxis_chunk",
            description="Liefert einen vollständigen Chunk aus AT-Praxisliteratur per stable_key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stable_key": {"type": "string", "description": "z.B. 'at-praxis|jeremias_p12|chunk_0042'"}
                },
                "required": ["stable_key"]
            }
        ),
        Tool(
            name="compare_vvg_kommentare",
            description="Vergleicht Berliner Kommentar VVG (Honsell 1999, DE+AT, pre-Reform) mit Bruck/Möller (DE n.F., post-Reform-2008) — plus optional AT-Praxisliteratur (9 Werke). Mit auto-Mapping AT↔DE: § 6 VersVG (AT) ≡ § 28 VVG (DE), § 69 VersVG (AT) ≡ § 95 VVG (DE), § 158k VersVG (AT) ≡ § 127 VVG (DE) usw. Mit include_at_praxis=true (default) wird zusätzlich der AT-Praxis-Korpus durchsucht — perfekt für Rechtsvergleich AT/DE + AT-Spezialliteratur.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string", "description": "§ N (mit/ohne 'VersVG'/'VVG'-Suffix)"},
                    "source_law": {"type": "string", "description": "AT|DE|auto", "enum": ["AT", "DE", "auto"], "default": "auto"},
                    "include_at_praxis": {"type": "boolean", "description": "AT-Praxisliteratur einbeziehen (default true)", "default": True}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="search_at_lehrbuch_keyword",
            description="Volltextsuche in der AT-Lehrbücher-Sammlung (46 Werke, 84.374 Chunks): ABGB (Bydlinski/Perner/Spitzer Kurzkommentar), UGB (Artmann), ZPO (Rechberger), AußStrG, FSG, GewO, TKG, DSGVO, DSGVO+BDSG+TTDSG, Sachverständigenrecht, Berufsrecht (RAO, Anwaltsrecht), Erbrecht (Eccher, Winkler), Familienrecht (Gewaltschutz Deixler/Mayrhofer, Unterhalt), Insolvenzrecht (Buchegger), Verfassungsrecht (Berka, Grundrechte), Baurecht (Pabel), Sozialrecht (Grillberger), HandelsvertreterG (Nocker), Vereinsrecht, IT-Recht (Heißl), Kostenrecht (Ziehensack), Anlegerschaden, Schmerzengeld (Kerschner), Zustellrecht u.v.m. Optional Filter auf subject_area (z.B. erbrecht, familienrecht, datenschutz) oder source_work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "subject_area": {"type": "string", "description": "Filter: zivilrecht | erbrecht | familienrecht | wirtschaftsrecht_ugb | prozessrecht_zpo | datenschutz | telekomrecht | IT-recht | verfassungsrecht | verwaltungsrecht_gewerbe | gesellschaftsrecht | sachverstaendigenrecht | berufsrecht | ..."},
                    "source_work": {"type": "string", "description": "Filter: ein konkretes Werk (z.B. 'abgb_bydlinski_perner_spitzer', 'zpo_rechberger', 'fsg_grubmann')"},
                    "max_results": {"type": "integer", "default": 30}
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="find_at_lehrbuch_by_paragraph",
            description="Reverse-Lookup: alle Chunks aus AT-Lehrbücher-Sammlung, die einen bestimmten § referenzieren. Funktioniert über die ganze 46-Werke-Sammlung (15.779 §-Refs gesamt). Z.B. 'find_at_lehrbuch_by_paragraph(\"§ 152 ABGB\")' findet alle Werke die § 152 ABGB zitieren.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string"},
                    "max_results": {"type": "integer", "default": 30}
                },
                "required": ["paragraph"]
            }
        ),
        Tool(
            name="get_at_lehrbuch_chunk",
            description="Liefert vollständigen Chunk aus AT-Lehrbücher-Sammlung per stable_key (z.B. 'at-lit|zpo_rechberger|chunk_0421').",
            inputSchema={
                "type": "object",
                "properties": {
                    "stable_key": {"type": "string"}
                },
                "required": ["stable_key"]
            }
        ),
        Tool(
            name="list_at_lehrbuecher_werke",
            description="Listet alle 46 Werke der AT-Lehrbücher-Sammlung mit Metadaten (slug, autor, subject_area, page_count). Optional Filter auf subject_area.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject_area": {"type": "string"}
                }
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

    elif name == "search_kbb_randziffer":
        result = search_kbb_randziffer(
            arguments.get("query", ""),
            arguments.get("paragraph", ""),
            arguments.get("limit", 10),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_klang_artikel":
        result = get_klang_artikel(
            arguments.get("paragraph", ""),
            arguments.get("law", "ABGB"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_klang_randziffer":
        result = search_klang_randziffer(
            arguments.get("paragraph", ""),
            arguments.get("rz_num", 1),
            arguments.get("law", "ABGB"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_klang_by_paragraph":
        result = search_klang_by_paragraph(
            arguments.get("paragraph", ""),
            arguments.get("law", "ABGB"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_klang_keyword":
        result = search_klang_keyword(
            arguments.get("keyword", ""),
            arguments.get("korpora", None),
            arguments.get("max_results", 50),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_leipziger_artikel":
        result = get_leipziger_artikel(
            arguments.get("paragraph", ""),
            arguments.get("law", "StGB"),
            arguments.get("edition"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_leipziger_randziffer":
        result = search_leipziger_randziffer(
            arguments.get("paragraph", ""),
            arguments.get("rn_num", 1),
            arguments.get("law", "StGB"),
            arguments.get("edition"),
            arguments.get("include_footnotes", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_leipziger_by_paragraph":
        result = search_leipziger_by_paragraph(
            arguments.get("paragraph", ""),
            arguments.get("law", "StGB"),
            arguments.get("edition"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_leipziger_keyword":
        result = search_leipziger_keyword(
            arguments.get("keyword", ""),
            arguments.get("max_results", 50),
            arguments.get("in_footnotes", False),
            arguments.get("edition"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_vvg_artikel":
        result = get_vvg_artikel(
            arguments.get("paragraph", ""),
            arguments.get("edition"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_vvg_randziffer":
        result = search_vvg_randziffer(
            arguments.get("paragraph", ""),
            arguments.get("rn_num", 1),
            arguments.get("edition"),
            arguments.get("include_footnotes", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_vvg_by_paragraph":
        result = search_vvg_by_paragraph(
            arguments.get("paragraph", ""),
            arguments.get("edition"),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_vvg_keyword":
        result = search_vvg_keyword(
            arguments.get("keyword", ""),
            arguments.get("max_results", 50),
            arguments.get("in_footnotes", False),
            arguments.get("edition"),
            arguments.get("include_bedingungen", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_vvg_bedingung":
        result = get_vvg_bedingung(
            arguments.get("werk", ""),
            arguments.get("klausel_id", ""),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_bk_vvg_artikel":
        result = get_bk_vvg_artikel(arguments.get("paragraph", ""))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_bk_vvg_randziffer":
        result = search_bk_vvg_randziffer(
            arguments.get("paragraph", ""),
            arguments.get("rn_num", 1),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_bk_vvg_keyword":
        result = search_bk_vvg_keyword(
            arguments.get("keyword", ""),
            arguments.get("max_results", 50),
            arguments.get("mojibake_tolerant", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_at_praxis_keyword":
        result = search_at_praxis_keyword(
            arguments.get("keyword", ""),
            arguments.get("source_work", ""),
            arguments.get("max_results", 30),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "find_at_praxis_by_paragraph":
        result = find_at_praxis_by_paragraph(
            arguments.get("paragraph", ""),
            arguments.get("max_results", 30),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_at_praxis_chunk":
        result = get_at_praxis_chunk(arguments.get("stable_key", ""))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "compare_vvg_kommentare":
        result = compare_vvg_kommentare(
            arguments.get("paragraph", ""),
            arguments.get("source_law", "auto"),
            arguments.get("include_at_praxis", True),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "search_at_lehrbuch_keyword":
        result = search_at_lehrbuch_keyword(
            arguments.get("keyword", ""),
            arguments.get("subject_area", ""),
            arguments.get("source_work", ""),
            arguments.get("max_results", 30),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "find_at_lehrbuch_by_paragraph":
        result = find_at_lehrbuch_by_paragraph(
            arguments.get("paragraph", ""),
            arguments.get("max_results", 30),
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "get_at_lehrbuch_chunk":
        result = get_at_lehrbuch_chunk(arguments.get("stable_key", ""))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "list_at_lehrbuecher_werke":
        result = list_at_lehrbuecher_werke(arguments.get("subject_area", ""))
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


def search_kbb_randziffer(query: str, paragraph: str = "", limit: int = 10) -> dict:
    """RZ-granulare Volltext-Suche im KBB-Kurzkommentar via public.wk_randziffern FTS."""
    query = clamp_query(query, 300)
    paragraph = clamp_query(paragraph, 100)
    limit = clamp_limit(limit, default=10, max_value=50)
    if not query:
        return {"query": query, "paragraph": paragraph or None, "count": 0, "results": []}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Build websearch_to_tsquery for forgiving search (handles phrases, AND-tokens)
        para_filter = ""
        extra_params: list[Any] = []
        if paragraph:
            para_filter = " AND k.paragraph_ref = %s"
            extra_params.append(paragraph)

        cursor.execute(
            f"""
            SELECT k.paragraph_ref, k.kommentator, rz.rz_raw, rz.section,
                   rz.text, rz.ogh_cases, rz.paragraphen_refs,
                   ts_rank(rz.text_tsvector, websearch_to_tsquery('german', %s)) AS rank
            FROM public.wk_randziffern rz
            JOIN public.wk_kommentare k ON k.id = rz.kommentar_id
            WHERE k.werk = 'KBB'
              AND rz.text_tsvector @@ websearch_to_tsquery('german', %s)
              {para_filter}
            ORDER BY rank DESC, k.paragraph_ref
            LIMIT %s
            """,
            tuple([query, query] + extra_params + [limit]),
        )
        rows = cursor.fetchall()
        results = [
            {
                "paragraph_ref": r[0],
                "kommentator": r[1],
                "rz": r[2],
                "section": r[3],
                "text": (r[4] or "")[:1500],
                "ogh_cases": r[5] or [],
                "paragraphen_refs": r[6] or [],
                "relevance": float(r[7]) if r[7] is not None else None,
            }
            for r in rows
        ]
        return {"query": query, "paragraph": paragraph or None, "count": len(results), "results": results}
    finally:
        cursor.close()


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
                "source": "kommentar.artikel",
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

        # Also query public.wk_kommentare (KBB, WK²)
        wk_law_filter = ""
        wk_params: list[Any] = [paragraph]
        if law:
            wk_law_filter = " AND lower(coalesce(k.law, '')) = lower(%s)"
            wk_params.append(law)
        wk_params.append(limit)
        cursor.execute(
            f"""
            SELECT k.id, k.werk, k.paragraph_ref, k.title, k.law, k.doc_type,
                   k.rechtsgebiet_primary, k.kommentator, k.auflage, k.rz_count,
                   coalesce((SELECT count(*) FROM public.wk_randziffern rz WHERE rz.kommentar_id = k.id), 0) AS rz_actual
            FROM public.wk_kommentare k
            WHERE k.paragraph_ref = %s
              {wk_law_filter}
            ORDER BY k.werk, k.id
            LIMIT %s
            """,
            tuple(wk_params),
        )
        wk_rows = cursor.fetchall()
        for r in wk_rows:
            results.append({
                "source": "public.wk_kommentare",
                "kommentar_id": r[0],
                "werk": r[1],
                "paragraph_ref": r[2],
                "title": r[3],
                "law": r[4],
                "doc_type": r[5],
                "rechtsgebiet": r[6],
                "kommentator": r[7],
                "auflage": r[8],
                "rz_count": r[9],
                "rz_actual": r[10],
            })

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
# KLANG3 GROSSKOMMENTAR — FILE-BASED TOOLS
# ============================================================================

# Corpus root directories (keyed by canonical law token used in filenames)
_KLANG3_CORPUS_DIRS: dict[str, Path] = {
    "ABGB":      Path("/Users/reinhardberger/HCS/Kommentare/AT/ABGB/klang3/extracted"),
    "KSchG":     Path("/Users/reinhardberger/HCS/Kommentare/AT/KSCHG/klang3/extracted"),
    "EheG_EPG":  Path("/Users/reinhardberger/HCS/Kommentare/AT/EHEG_EPG/klang3/extracted"),
    "AHG":       Path("/Users/reinhardberger/HCS/Kommentare/AT/AHG/klang3/extracted"),
}

# Aliases: normalised user input → canonical filename law token
_LAW_ALIASES: dict[str, str] = {
    "abgb": "ABGB",
    "kschg": "KSchG",
    "kscg": "KSchG",
    "eheg_epg": "EheG_EPG",
    "eheg": "EheG_EPG",
    "epg": "EheG_EPG",
    "eheg/epg": "EheG_EPG",
    "ahg": "AHG",
}

# Module-level keyword search cache: law_token -> list of (paragraph_ref, rz_num, rz_text, authors, page_from)
_klang3_cache: dict[str, list[tuple]] = {}


def _resolve_law(law_input: str) -> Optional[str]:
    """Normalise user-supplied law string to canonical filename token, or None if unknown."""
    return _LAW_ALIASES.get(law_input.lower().strip(), None)


def _parse_paragraph_input(paragraph: str, default_law: str = "ABGB") -> Tuple[str, str, str]:
    """Parse varied paragraph inputs to (law_token, num_str, suffix).

    Handles: '364', '§ 364', '364a', '§ 364a', '§ 1 ABGB', '§ 12a KSchG'.
    Returns canonical law_token (for filename lookup), numeric string, and lowercase suffix.
    """
    text = paragraph.strip()

    # Strip leading '§' and whitespace
    text = re.sub(r"^§\s*", "", text).strip()

    # Try to extract trailing law token (e.g. "364 ABGB", "12a KSchG", "100 EheG_EPG")
    law_from_input: Optional[str] = None
    m = re.match(r"^(\d+[a-z]*)\s+(.+)$", text, re.IGNORECASE)
    if m:
        candidate_law = m.group(2).strip()
        resolved = _resolve_law(candidate_law)
        if resolved:
            law_from_input = resolved
            text = m.group(1).strip()
        # else: the trailing part might not be a law name — keep full text for num+suffix parsing

    # Now text should be just the number (possibly with suffix), e.g. '364', '364a', '1216c'
    m2 = re.match(r"^(\d+)([a-z]*)$", text, re.IGNORECASE)
    if not m2:
        # last fallback: extract first digit sequence
        m3 = re.search(r"(\d+)([a-z]*)", text, re.IGNORECASE)
        if m3:
            num_str = m3.group(1)
            suffix = m3.group(2).lower()
        else:
            num_str = text
            suffix = ""
    else:
        num_str = m2.group(1)
        suffix = m2.group(2).lower()

    # Resolve law: explicit > default_law
    if law_from_input:
        law_token = law_from_input
    else:
        law_token = _resolve_law(default_law) or "ABGB"

    return law_token, num_str, suffix


def _find_klang3_file(law_token: str, num_str: str, suffix: str) -> Optional[Path]:
    """Locate the JSON file for a given paragraph in the appropriate corpus directory.

    Filename pattern: __{num_str}{suffix}_{law_token}__{Author}__Klang3.json
    Tries exact num+suffix first, then falls back to num-only if suffix is empty.
    """
    corpus_dir = _KLANG3_CORPUS_DIRS.get(law_token)
    if not corpus_dir or not corpus_dir.exists():
        return None

    # Build the prefix we need: __<num><suffix>_<law>__
    para_part = f"{num_str}{suffix}"
    prefix = f"__{para_part}_{law_token}__"
    # Note: filenames use single underscore between num/law, double-underscore around
    # Actual pattern observed: __364_ABGB__Author__Klang3.json
    # i.e. __{para}_{law}__{author}__Klang3.json
    # So prefix = f"__{para_part}_{law_token}__"

    for p in corpus_dir.glob(f"__{para_part}_{law_token}__*__Klang3.json"):
        return p

    # Also try the case where suffix letter is uppercase (defensive)
    if suffix:
        for p in corpus_dir.glob(f"__{num_str}{suffix.upper()}_{law_token}__*__Klang3.json"):
            return p

    return None


def _load_klang_file(path: Path) -> Optional[dict]:
    """Load and return parsed JSON from a Klang3 file; None on any error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_klang_corpus_cache(law_token: str) -> List[tuple]:
    """Load all RZ tuples for a corpus into the module cache (lazy, one-shot per law).

    Each tuple: (paragraph_ref, law, rz_num, rz_text, authors, page_from)
    """
    if law_token in _klang3_cache:
        return _klang3_cache[law_token]

    corpus_dir = _KLANG3_CORPUS_DIRS.get(law_token)
    if not corpus_dir or not corpus_dir.exists():
        _klang3_cache[law_token] = []
        return []

    entries: List[tuple] = []
    for json_path in sorted(corpus_dir.glob("*__Klang3.json")):
        data = _load_klang_file(json_path)
        if not data:
            continue
        meta = _leipziger_meta(data)
        paragraph_ref = meta.get("paragraph_ref", "")
        law = meta.get("law", law_token)
        authors = meta.get("authors", [])
        for rz in data.get("randziffern", []):
            entries.append((
                paragraph_ref,
                law,
                rz.get("rz_num"),
                rz.get("rz_text", ""),
                authors,
                rz.get("page_from"),
            ))

    _klang3_cache[law_token] = entries
    return entries


def get_klang_artikel(paragraph: str, law: str = "ABGB") -> dict:
    """Return full Klang³ article for a paragraph: meta + uebersicht + literatur + all randziffern."""
    paragraph = clamp_query(paragraph, 100)
    law = clamp_query(law, 30)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}

    law_token, num_str, suffix = _parse_paragraph_input(paragraph, law)
    file_path = _find_klang3_file(law_token, num_str, suffix)
    if not file_path:
        return {
            "found": False,
            "paragraph": paragraph,
            "law": law_token,
            "reason": "paragraph_not_found_in_klang3_corpus",
        }

    data = _load_klang_file(file_path)
    if not data:
        return {"found": False, "reason": "file_load_error", "file": str(file_path)}

    return {
        "found": True,
        "source": "Klang3",
        "meta": data.get("meta", {}),
        "uebersicht": data.get("uebersicht", ""),
        "literatur": data.get("literatur", ""),
        "stammfassung": data.get("stammfassung", ""),
        "randziffern": data.get("randziffern", []),
        "citations_summary": data.get("citations_summary", {}),
        "stats": data.get("stats", {}),
    }


def search_klang_randziffer(paragraph: str, rz_num: int, law: str = "ABGB") -> dict:
    """Return a single Klang³ Randziffer with full text, citations, and Zitiervorschlag."""
    paragraph = clamp_query(paragraph, 100)
    law = clamp_query(law, 30)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}

    try:
        rz_num = int(rz_num)
    except (TypeError, ValueError):
        return {"found": False, "reason": "invalid_rz_num"}

    law_token, num_str, suffix = _parse_paragraph_input(paragraph, law)
    file_path = _find_klang3_file(law_token, num_str, suffix)
    if not file_path:
        return {
            "found": False,
            "paragraph": paragraph,
            "law": law_token,
            "reason": "paragraph_not_found_in_klang3_corpus",
        }

    data = _load_klang_file(file_path)
    if not data:
        return {"found": False, "reason": "file_load_error"}

    meta = _leipziger_meta(data)
    for rz in data.get("randziffern", []):
        if rz.get("rz_num") == rz_num:
            # Build a concrete Zitiervorschlag with the actual Rz number
            zitier_base = meta.get("zitiervorschlag", "")
            zitiervorschlag = zitier_base.replace(" Rz N", f" Rz {rz_num}")
            return {
                "found": True,
                "source": "Klang3",
                "paragraph_ref": meta.get("paragraph_ref", ""),
                "law": meta.get("law", law_token),
                "authors": meta.get("authors", []),
                "stand_date": meta.get("stand_date", ""),
                "volume_id": meta.get("volume_id", ""),
                "zitiervorschlag": zitiervorschlag,
                "rz_num": rz.get("rz_num"),
                "rz_text": rz.get("rz_text", ""),
                "ogh_zitate": rz.get("ogh_zitate", []),
                "rs_zitate": rz.get("rs_zitate", []),
                "page_from": rz.get("page_from"),
                "page_to": rz.get("page_to"),
                "anchor_side": rz.get("anchor_side"),
                "char_count": rz.get("char_count"),
            }

    return {
        "found": False,
        "paragraph_ref": meta.get("paragraph_ref", ""),
        "rz_num": rz_num,
        "reason": "rz_not_found",
        "rz_count": data.get("stats", {}).get("rz_count"),
    }


def search_klang_by_paragraph(paragraph: str, law: str = "ABGB") -> dict:
    """Return short overview of a Klang³ article: rz_count, authors, stand_date, 200-char snippet per Rz."""
    paragraph = clamp_query(paragraph, 100)
    law = clamp_query(law, 30)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}

    law_token, num_str, suffix = _parse_paragraph_input(paragraph, law)
    file_path = _find_klang3_file(law_token, num_str, suffix)
    if not file_path:
        return {
            "found": False,
            "paragraph": paragraph,
            "law": law_token,
            "reason": "paragraph_not_found_in_klang3_corpus",
        }

    data = _load_klang_file(file_path)
    if not data:
        return {"found": False, "reason": "file_load_error"}

    meta = _leipziger_meta(data)
    stats = data.get("stats", {})
    rz_overview = [
        {
            "rz_num": rz.get("rz_num"),
            "snippet": (rz.get("rz_text", "") or "")[:200],
            "ogh_zitate_count": len(rz.get("ogh_zitate", [])),
            "rs_zitate_count": len(rz.get("rs_zitate", [])),
            "page_from": rz.get("page_from"),
        }
        for rz in data.get("randziffern", [])
    ]

    return {
        "found": True,
        "source": "Klang3",
        "paragraph_ref": meta.get("paragraph_ref", ""),
        "law": meta.get("law", law_token),
        "authors": meta.get("authors", []),
        "stand_date": meta.get("stand_date", ""),
        "volume_id": meta.get("volume_id", ""),
        "zitiervorschlag": meta.get("zitiervorschlag", ""),
        "rz_count": stats.get("rz_count", len(rz_overview)),
        "page_from": stats.get("page_from"),
        "page_to": stats.get("page_to"),
        "total_chars": stats.get("total_chars"),
        "citations_summary": data.get("citations_summary", {}),
        "rz_overview": rz_overview,
    }


def search_klang_keyword(keyword: str, korpora: Optional[List[str]] = None, max_results: int = 50) -> dict:
    """Case-insensitive keyword search over all Klang³ Randziffern; scored by occurrence count."""
    keyword = clamp_query(keyword, 300)
    max_results = clamp_limit(max_results, default=50, max_value=200)
    if not keyword:
        return {"keyword": keyword, "count": 0, "results": []}

    # Normalise corpus list
    valid_tokens = list(_KLANG3_CORPUS_DIRS.keys())
    if korpora:
        selected = []
        for k in korpora:
            resolved = _resolve_law(str(k))
            if resolved and resolved in valid_tokens:
                selected.append(resolved)
        if not selected:
            selected = valid_tokens
    else:
        selected = valid_tokens

    kw_lower = keyword.lower()
    matches: List[dict] = []

    for law_token in selected:
        entries = _load_klang_corpus_cache(law_token)
        for paragraph_ref, law, rz_num, rz_text, authors, page_from in entries:
            if not rz_text:
                continue
            score = rz_text.lower().count(kw_lower)
            if score == 0:
                continue
            # Build a 300-char snippet around the first occurrence
            idx = rz_text.lower().find(kw_lower)
            start = max(0, idx - 80)
            end = min(len(rz_text), idx + 220)
            snippet = ("..." if start > 0 else "") + rz_text[start:end] + ("..." if end < len(rz_text) else "")
            matches.append({
                "paragraph_ref": paragraph_ref,
                "law": law,
                "rz_num": rz_num,
                "snippet": snippet,
                "author": authors[0] if authors else "",
                "page_from": page_from,
                "score": score,
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    total_found = len(matches)
    return {
        "keyword": keyword,
        "korpora": selected,
        "total_found": total_found,
        "count": min(total_found, max_results),
        "results": matches[:max_results],
    }


# ============================================================================
# LEIPZIGER KOMMENTAR StGB — FILE-BASED TOOLS
# ============================================================================

_LEIPZIGER_BASE: Path = Path("/Users/reinhardberger/HCS/Kommentare/DE/StGB/leipziger")
# V2 production paths (extracted_v2 + enriched_v2 with §-membership-voting)
_LEIPZIGER_EXTRACTED: Path = _LEIPZIGER_BASE / "extracted_v2"
_LEIPZIGER_ENRICHED: Path = _LEIPZIGER_BASE / "enriched_v2"
# V1 fallback (deprecated — boundary-bleed not fully resolved)
_LEIPZIGER_EXTRACTED_V1: Path = _LEIPZIGER_BASE / "extracted"
_LEIPZIGER_ENRICHED_V1: Path = _LEIPZIGER_BASE / "enriched"

# Cache: edition -> list of (paragraph_ref, rn_num, rn_text, authors, page_from, fn_count)
_leipziger_cache: dict[int, list[tuple]] = {}


def _resolve_leipziger_dir(prefer_enriched: bool = True) -> Path:
    """Prefer enriched dir if it has files, fall back to extracted."""
    if prefer_enriched and _LEIPZIGER_ENRICHED.exists():
        if any(_LEIPZIGER_ENRICHED.glob("__*.json")):
            return _LEIPZIGER_ENRICHED
    return _LEIPZIGER_EXTRACTED


def _parse_stgb_paragraph(paragraph: str) -> Tuple[str, str]:
    """Parse paragraph input to (num_str, suffix).

    Handles: '211', '§ 211', '263a', '§ 263a StGB', '§ 218a'.
    """
    text = paragraph.strip()
    text = re.sub(r"^§\s*", "", text).strip()
    text = re.sub(r"\s+StGB\s*$", "", text, flags=re.IGNORECASE).strip()
    m = re.match(r"^(\d+)([a-z]?)$", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2).lower()
    m2 = re.search(r"(\d+)([a-z]?)", text, re.IGNORECASE)
    if m2:
        return m2.group(1), m2.group(2).lower()
    return text, ""


def _find_leipziger_file(num_str: str, suffix: str, edition: Optional[int] = None) -> Optional[Path]:
    """Locate a Leipziger §-JSON file.

    Lookup order (prefers higher-quality source):
      1. enriched_v2/  (V2 with enrichment) — if § has been enriched
      2. extracted_v2/ (V2 without enrichment) — fallback for non-enriched V2 §§
      3. enriched/     (V1 with enrichment) — V1 fallback when V2 missing
      4. extracted/    (V1 raw)
    """
    para_part = f"{num_str}{suffix}"
    editions_to_try = [edition] if edition else [13, 12]
    v2_prefix = f"__{para_part}_StGB__"

    def _best_match(candidates: list) -> Optional[Path]:
        """Prefer author-named files over generic LK_StGB; if tied, prefer file with most Rn."""
        if not candidates:
            return None
        # Sort: non-LK_StGB first, then by Rn-count desc
        def sort_key(p: Path):
            is_generic = '__LK_StGB__' in p.name
            # Quick Rn-count via JSON read (cheap)
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                rn_count = len(d.get("randnummern", []))
            except Exception:
                rn_count = 0
            return (is_generic, -rn_count)
        return sorted(candidates, key=sort_key)[0]

    # Try each dir in order
    for search_dir in [_LEIPZIGER_ENRICHED, _LEIPZIGER_EXTRACTED]:
        if not search_dir.exists():
            continue
        for ed in editions_to_try:
            cands = list(search_dir.glob(f"{v2_prefix}*__Leipziger_aufl{ed}_v2.json"))
            if cands:
                return _best_match(cands)
        cands = list(search_dir.glob(f"{v2_prefix}*__Leipziger_aufl*_v2.json"))
        if cands:
            return _best_match(cands)
    # V1 fallback
    for search_dir in [_LEIPZIGER_ENRICHED_V1, _LEIPZIGER_EXTRACTED_V1]:
        if not search_dir.exists():
            continue
        for ed in editions_to_try:
            cands = list(search_dir.glob(f"{v2_prefix}*__Leipziger_aufl{ed}.json"))
            if cands:
                return _best_match(cands)
        cands = list(search_dir.glob(f"{v2_prefix}*__Leipziger_aufl*.json"))
        if cands:
            return _best_match(cands)
    return None


def _load_leipziger_file(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _leipziger_meta(data: dict) -> dict:
    """Return unified meta dict for V1 (nested 'meta') and V2 (flat) schemas."""
    if "meta" in data and isinstance(data["meta"], dict):
        return data["meta"]
    # V2 flat schema — synthesize meta
    return {
        "paragraph_ref": data.get("paragraph_ref", ""),
        "law": data.get("law", "StGB"),
        "edition": data.get("edition"),
        "edition_label": data.get("edition_label"),
        "is_replacement": data.get("is_replacement", False),
        "authors": data.get("authors", []),
        "volume_id": data.get("volume_id", ""),
        "zitiervorschlag": data.get("zitiervorschlag", ""),
        "para_from": data.get("para_num"),
        "title": data.get("title", ""),
    }


def _load_leipziger_corpus_cache(edition: int = 13) -> List[tuple]:
    """Load all Rn tuples for keyword search (lazy). Supports both V2 (flat) and V1 (nested meta) schemas."""
    if edition in _leipziger_cache:
        return _leipziger_cache[edition]
    src_dir = _resolve_leipziger_dir()
    entries: List[tuple] = []
    # V2 (preferred) + V1 fallback
    patterns = [f"*__Leipziger_aufl{edition}_v2.json", f"*__Leipziger_aufl{edition}.json"]
    seen_paragraphs: set = set()
    for pattern in patterns:
        for json_path in sorted(src_dir.glob(pattern)):
            # Also try V1 dir if src_dir is V2
            pass
        # Iterate both V2 and V1 dirs
        for search_dir in [src_dir, _LEIPZIGER_ENRICHED_V1 if _LEIPZIGER_ENRICHED_V1.exists() else _LEIPZIGER_EXTRACTED_V1]:
            if search_dir == src_dir and not pattern.endswith("_v2.json"):
                continue  # V1 pattern only in V1 dir
            if search_dir != src_dir and pattern.endswith("_v2.json"):
                continue  # V2 pattern only in V2 dir
            for json_path in sorted(search_dir.glob(pattern)):
                data = _load_leipziger_file(json_path)
                if not data:
                    continue
                # V2: flat schema; V1: nested 'meta'
                paragraph_ref = data.get("paragraph_ref") or data.get("meta", {}).get("paragraph_ref", "")
                if paragraph_ref in seen_paragraphs:
                    continue  # prefer V2 (loaded first)
                seen_paragraphs.add(paragraph_ref)
                authors = data.get("authors") or data.get("meta", {}).get("authors", [])
                vol_edition = data.get("edition") or data.get("meta", {}).get("edition", edition)
                for rn in data.get("randnummern", []):
                    entries.append((
                        paragraph_ref,
                        rn.get("rn_num"),
                        rn.get("rn_text", ""),
                        authors or rn.get("page_authors", []),
                        rn.get("page_from"),
                        len(rn.get("fussnoten", [])),
                        rn.get("fussnoten", []),
                        rn.get("stable_key", ""),
                        vol_edition,
                    ))
    _leipziger_cache[edition] = entries
    return entries


def get_leipziger_artikel(paragraph: str, law: str = "StGB", edition: Optional[int] = None) -> dict:
    """Vollständiger Leipziger-StGB-Artikel: Meta + alle Randnummern + alle Fußnoten."""
    paragraph = clamp_query(paragraph, 100)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}
    num_str, suffix = _parse_stgb_paragraph(paragraph)
    file_path = _find_leipziger_file(num_str, suffix, edition)
    if not file_path:
        return {"found": False, "paragraph": paragraph, "reason": "paragraph_not_found_in_leipziger_corpus"}
    data = _load_leipziger_file(file_path)
    if not data:
        return {"found": False, "reason": "file_load_error", "file": str(file_path)}
    return {
        "found": True,
        "source": "Leipziger Kommentar StGB",
        "meta": _leipziger_meta(data),
        "header_excerpt": data.get("header_excerpt", ""),
        "randnummern": data.get("randnummern", []),
        "stats": data.get("stats", {}),
        "file": file_path.name,
        "extractor_version": "v2" if "_v2.json" in file_path.name else "v1",
    }


def search_leipziger_randziffer(paragraph: str, rn_num: int, law: str = "StGB",
                                  edition: Optional[int] = None, include_footnotes: bool = True) -> dict:
    """Einzelne Leipziger-Randnummer mit Volltext + Fußnoten + Zitiervorschlag."""
    paragraph = clamp_query(paragraph, 100)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}
    try:
        rn_num = int(rn_num)
    except (TypeError, ValueError):
        return {"found": False, "reason": "invalid_rn_num"}
    num_str, suffix = _parse_stgb_paragraph(paragraph)
    file_path = _find_leipziger_file(num_str, suffix, edition)
    if not file_path:
        return {"found": False, "paragraph": paragraph, "reason": "paragraph_not_found_in_leipziger_corpus"}
    data = _load_leipziger_file(file_path)
    if not data:
        return {"found": False, "reason": "file_load_error"}
    meta = _leipziger_meta(data)
    for rn in data.get("randnummern", []):
        if rn.get("rn_num") == rn_num:
            zitier_base = meta.get("zitiervorschlag", "")
            zit = zitier_base.replace(" Rn. N", f" Rn. {rn_num}")
            fns = rn.get("fussnoten", []) if include_footnotes else []
            return {
                "found": True,
                "source": "Leipziger Kommentar StGB",
                "paragraph_ref": meta.get("paragraph_ref", ""),
                "law": meta.get("law", "StGB"),
                "edition": meta.get("edition"),
                "edition_label": meta.get("edition_label"),
                "is_replacement": meta.get("is_replacement", False),
                "authors": meta.get("authors", []) or rn.get("page_authors", []),
                "page_authors": rn.get("page_authors", []),
                "volume_id": meta.get("volume_id", ""),
                "zitiervorschlag": zit,
                "rn_num": rn["rn_num"],
                "rn_text": rn.get("rn_text", ""),
                "page_from": rn.get("page_from"),
                "page_to": rn.get("page_to"),
                "char_count": rn.get("char_count"),
                "anchor_side": rn.get("anchor_side"),
                "fussnote_refs": rn.get("fussnote_refs", []),
                "fussnoten": fns,
                "fn_count": len(rn.get("fussnoten", [])),
            }
    return {
        "found": False,
        "paragraph_ref": meta.get("paragraph_ref", ""),
        "rn_num": rn_num,
        "reason": "rn_not_found",
        "rn_count_in_paragraph": data.get("stats", {}).get("rn_count"),
    }


def search_leipziger_by_paragraph(paragraph: str, law: str = "StGB", edition: Optional[int] = None) -> dict:
    """Übersicht eines Leipziger-Artikels: rn_count, Autoren, edition, 200-char-Snippet pro Rn."""
    paragraph = clamp_query(paragraph, 100)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}
    num_str, suffix = _parse_stgb_paragraph(paragraph)
    file_path = _find_leipziger_file(num_str, suffix, edition)
    if not file_path:
        return {"found": False, "paragraph": paragraph, "reason": "paragraph_not_found_in_leipziger_corpus"}
    data = _load_leipziger_file(file_path)
    if not data:
        return {"found": False, "reason": "file_load_error"}
    meta = _leipziger_meta(data)
    stats = data.get("stats", {})
    rn_overview = [
        {
            "rn_num": rn.get("rn_num"),
            "snippet": (rn.get("rn_text", "") or "")[:200],
            "fn_count": len(rn.get("fussnoten", [])),
            "page_from": rn.get("page_from"),
            "char_count": rn.get("char_count"),
        }
        for rn in data.get("randnummern", [])
    ]
    return {
        "found": True,
        "source": "Leipziger Kommentar StGB",
        "paragraph_ref": meta.get("paragraph_ref", ""),
        "law": meta.get("law", "StGB"),
        "edition": meta.get("edition"),
        "edition_label": meta.get("edition_label"),
        "is_replacement": meta.get("is_replacement", False),
        "authors": meta.get("authors", []),
        "volume_id": meta.get("volume_id", ""),
        "zitiervorschlag": meta.get("zitiervorschlag", ""),
        "rn_count": stats.get("rn_count", len(rn_overview)),
        "page_from": stats.get("page_from"),
        "page_to": stats.get("page_to"),
        "fn_total": stats.get("fn_total"),
        "rn_with_fn": stats.get("rn_with_fn"),
        "rn_overview": rn_overview,
    }


def search_leipziger_keyword(keyword: str, max_results: int = 50, in_footnotes: bool = False,
                              edition: Optional[int] = None) -> dict:
    """Volltextsuche über Leipziger Randnummern; optional inkl. Fußnoten-Texte."""
    keyword = clamp_query(keyword, 300)
    max_results = clamp_limit(max_results, default=50, max_value=200)
    if not keyword:
        return {"keyword": keyword, "count": 0, "results": []}
    editions = [edition] if edition else [13, 12]
    kw_lower = keyword.lower()
    matches: List[dict] = []
    for ed in editions:
        entries = _load_leipziger_corpus_cache(ed)
        for (paragraph_ref, rn_num, rn_text, authors, page_from, fn_count, fussnoten,
             stable_key, ent_edition) in entries:
            score = 0
            if rn_text:
                score += rn_text.lower().count(kw_lower)
            if in_footnotes:
                for fn in fussnoten:
                    fn_text = fn.get("fn_text_raw", "")
                    if fn_text:
                        score += fn_text.lower().count(kw_lower)
            if score == 0:
                continue
            # Build snippet
            haystack = rn_text or ""
            idx = haystack.lower().find(kw_lower)
            if idx == -1 and in_footnotes:
                # Find first FN with hit
                for fn in fussnoten:
                    fn_t = fn.get("fn_text_raw", "")
                    if kw_lower in fn_t.lower():
                        haystack = f"[FN {fn['fn_num']}] " + fn_t
                        idx = haystack.lower().find(kw_lower)
                        break
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(haystack), idx + 220)
                snippet = ("..." if start > 0 else "") + haystack[start:end] + ("..." if end < len(haystack) else "")
            else:
                snippet = haystack[:300]
            matches.append({
                "paragraph_ref": paragraph_ref,
                "rn_num": rn_num,
                "stable_key": stable_key,
                "snippet": snippet,
                "author": authors[0] if authors else "",
                "edition": ent_edition,
                "page_from": page_from,
                "fn_count": fn_count,
                "score": score,
            })
    matches.sort(key=lambda x: x["score"], reverse=True)
    total_found = len(matches)
    return {
        "keyword": keyword,
        "in_footnotes": in_footnotes,
        "total_found": total_found,
        "count": min(total_found, max_results),
        "results": matches[:max_results],
    }


# ============================================================================
# BRUCK/MÖLLER VVG GROSSKOMMENTAR — FILE-BASED TOOLS
# ============================================================================

_VVG_BASE: Path = Path("/Users/reinhardberger/HCS/Kommentare/DE/VVG/grosskommentar")
_VVG_EXTRACTED: Path = _VVG_BASE / "extracted_v2"
_VVG_ENRICHED: Path = _VVG_BASE / "enriched_v2"
_VVG_BED_EXTRACTED: Path = _VVG_BASE / "extracted_v2_bedingungen"
_VVG_BED_ENRICHED: Path = _VVG_BASE / "enriched_v2_bedingungen"

_VVG_GENERIC_AUTHOR_SLUGS = {"VVG_BM", "Generic", "VVG"}
_vvg_cache: dict[int, list[tuple]] = {}


def _parse_vvg_paragraph(paragraph: str) -> Tuple[str, str]:
    """Parse paragraph input to (num_str, suffix). Handles '100', '§ 100', '§ 7a VVG'."""
    text = paragraph.strip()
    text = re.sub(r"^§\s*", "", text).strip()
    text = re.sub(r"\s+VVG\s*$", "", text, flags=re.IGNORECASE).strip()
    m = re.match(r"^(\d+)([a-z]?)$", text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2).lower()
    m2 = re.search(r"(\d+)([a-z]?)", text, re.IGNORECASE)
    if m2:
        return m2.group(1), m2.group(2).lower()
    return text, ""


def _find_vvg_file(num_str: str, suffix: str, edition: Optional[int] = None) -> Optional[Path]:
    """Lookup VVG §-File. Reihenfolge: enriched_v2 → extracted_v2.

    Author-Files vor VVG_BM-Generic, dann mehr Rn first.
    """
    para_part = f"{num_str}{suffix}"
    editions_to_try = [edition] if edition else [10, 9]
    v2_prefix = f"__{para_part}_VVG__"

    def _best_match(candidates: list[Path]) -> Optional[Path]:
        if not candidates:
            return None

        def sort_key(p: Path):
            is_generic = any(g in p.name.split("__") for g in _VVG_GENERIC_AUTHOR_SLUGS)
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                rn_count = len(d.get("randnummern", []))
            except Exception:
                rn_count = 0
            return (is_generic, -rn_count)

        return sorted(candidates, key=sort_key)[0]

    for search_dir in [_VVG_ENRICHED, _VVG_EXTRACTED]:
        if not search_dir.exists():
            continue
        for ed in editions_to_try:
            cands = list(search_dir.glob(f"{v2_prefix}*__VVG_aufl{ed}_v2.json"))
            if cands:
                return _best_match(cands)
        cands = list(search_dir.glob(f"{v2_prefix}*__VVG_aufl*_v2.json"))
        if cands:
            return _best_match(cands)
    return None


def _vvg_meta(data: dict) -> dict:
    """V2 flat schema → unified meta dict."""
    if "meta" in data and isinstance(data["meta"], dict):
        return data["meta"]
    return {
        "paragraph_ref": data.get("paragraph_ref", ""),
        "law": "VVG",
        "edition": data.get("edition"),
        "main_author": data.get("main_author", ""),
        "volume_id": data.get("volume_id", ""),
        "para_from": data.get("para_num"),
        "page_start": data.get("page_start"),
        "page_end": data.get("page_end"),
        "schema_version": data.get("schema_version", ""),
        "korpus": "Bruck/Möller VVG Großkommentar",
    }


def _load_vvg_corpus_cache(edition: int = 10) -> list[tuple]:
    """Cache (paragraph_ref, rn_num, rn_text, authors, page_from, fn_count, fussnoten,
    stable_key, ent_edition) tuples for keyword search."""
    if edition in _vvg_cache:
        return _vvg_cache[edition]
    entries: list[tuple] = []
    for search_dir in [_VVG_ENRICHED, _VVG_EXTRACTED]:
        if not search_dir.exists():
            continue
        for f in sorted(search_dir.glob(f"__*_VVG__*aufl{edition}_v2.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            paragraph_ref = d.get("paragraph_ref", "")
            main_author = d.get("main_author", "")
            for rn in d.get("randnummern", []):
                stable_key = f"vvg-bm|VVG|{paragraph_ref}|rn{rn.get('rn_num')}|aufl{edition}"
                entries.append((
                    paragraph_ref,
                    rn.get("rn_num"),
                    rn.get("rn_text", ""),
                    rn.get("page_authors") or [main_author],
                    rn.get("page_from"),
                    len(rn.get("fussnoten", [])),
                    rn.get("fussnoten", []),
                    stable_key,
                    edition,
                ))
        # Brake — wenn enriched gefunden, nicht nochmal extracted scannen
        if entries:
            break
    _vvg_cache[edition] = entries
    return entries


def _load_vvg_bedingungen_cache() -> list[tuple]:
    """Bedingungswerke (AHB/ARB/AKB) cache. Returns (klausel_ref, werk, rn_num, rn_text,
    page_from, fn_count, stable_key, edition)."""
    cached: list[tuple] = []
    src = _VVG_BED_ENRICHED if _VVG_BED_ENRICHED.exists() else _VVG_BED_EXTRACTED
    if not src.exists():
        return cached
    for f in sorted(src.glob("__*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        werk = d.get("werk", "")
        klausel_ref = d.get("klausel_ref", "")
        klausel_id = d.get("klausel_id", "")
        edition = d.get("edition", 10)
        for rn in d.get("randnummern", []):
            stable_key = (
                f"vvg-bm|{werk}|{klausel_id.replace(' ', '_').replace('.', '-')}"
                f"|rn{rn.get('rn_num')}|aufl{edition}"
            )
            cached.append((
                klausel_ref,
                werk,
                rn.get("rn_num"),
                rn.get("rn_text", ""),
                rn.get("page_from"),
                0,
                stable_key,
                edition,
            ))
    return cached


def get_vvg_artikel(paragraph: str, edition: Optional[int] = None) -> dict:
    """Vollständiger Bruck/Möller VVG-Artikel: Meta + alle Rn."""
    paragraph = clamp_query(paragraph, 100)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}
    num_str, suffix = _parse_vvg_paragraph(paragraph)
    f = _find_vvg_file(num_str, suffix, edition)
    if not f:
        return {"found": False, "paragraph": paragraph, "reason": "paragraph_not_found_in_vvg_corpus"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return {"found": False, "reason": "file_load_error", "error": str(e)}
    meta = _vvg_meta(data)
    return {
        "found": True,
        "source": "Bruck/Möller VVG Großkommentar",
        "meta": meta,
        "rn_count": len(data.get("randnummern", [])),
        "randnummern": data.get("randnummern", []),
        "file": f.name,
    }


def search_vvg_randziffer(paragraph: str, rn_num: int, edition: Optional[int] = None,
                          include_footnotes: bool = True) -> dict:
    """Spezifische VVG-Rn mit Volltext + Fußnoten."""
    paragraph = clamp_query(paragraph, 100)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}
    try:
        rn_num = int(rn_num)
    except (TypeError, ValueError):
        return {"found": False, "reason": "invalid_rn_num"}
    num_str, suffix = _parse_vvg_paragraph(paragraph)
    f = _find_vvg_file(num_str, suffix, edition)
    if not f:
        return {"found": False, "paragraph": paragraph, "reason": "paragraph_not_found_in_vvg_corpus"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {"found": False, "reason": "file_load_error"}
    meta = _vvg_meta(data)
    for rn in data.get("randnummern", []):
        if rn.get("rn_num") == rn_num:
            zit = (
                f"Bruck/Möller/{meta.get('main_author', '')} "
                f"{meta.get('edition', 10)}. Aufl. VVG {meta.get('paragraph_ref', '')} Rn. {rn_num}"
            )
            fns = rn.get("fussnoten", []) if include_footnotes else []
            return {
                "found": True,
                "source": "Bruck/Möller VVG Großkommentar",
                "paragraph_ref": meta.get("paragraph_ref"),
                "law": "VVG",
                "edition": meta.get("edition"),
                "main_author": meta.get("main_author"),
                "page_authors": rn.get("page_authors", []),
                "volume_id": meta.get("volume_id"),
                "zitiervorschlag": zit,
                "rn_num": rn["rn_num"],
                "rn_text": rn.get("rn_text", ""),
                "page_from": rn.get("page_from"),
                "page_to": rn.get("page_to"),
                "char_count": rn.get("char_count"),
                "paragraph_ref_corrected": rn.get("paragraph_ref_corrected"),
                "enrichment": rn.get("enrichment", {}),
                "fussnote_refs": rn.get("fussnote_refs", []),
                "fussnoten": fns,
                "fn_count": len(rn.get("fussnoten", [])),
            }
    return {
        "found": False,
        "paragraph_ref": meta.get("paragraph_ref"),
        "rn_num": rn_num,
        "reason": "rn_not_found",
        "rn_count_in_paragraph": len(data.get("randnummern", [])),
    }


def search_vvg_by_paragraph(paragraph: str, edition: Optional[int] = None) -> dict:
    """Übersicht eines VVG-Artikels: Snippets + Schlagworte je Rn."""
    paragraph = clamp_query(paragraph, 100)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}
    num_str, suffix = _parse_vvg_paragraph(paragraph)
    f = _find_vvg_file(num_str, suffix, edition)
    if not f:
        return {"found": False, "paragraph": paragraph, "reason": "paragraph_not_found_in_vvg_corpus"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {"found": False, "reason": "file_load_error"}
    meta = _vvg_meta(data)
    rns = data.get("randnummern", [])
    overview = [
        {
            "rn_num": rn.get("rn_num"),
            "snippet": (rn.get("rn_text", "") or "")[:200],
            "schlagworte": (rn.get("enrichment") or {}).get("schlagworte", []),
            "rechtsgebiet_sub": (rn.get("enrichment") or {}).get("rechtsgebiet_sub"),
            "fn_count": len(rn.get("fussnoten", [])),
            "page_from": rn.get("page_from"),
            "char_count": rn.get("char_count"),
        }
        for rn in rns
    ]
    return {
        "found": True,
        "source": "Bruck/Möller VVG Großkommentar",
        "paragraph_ref": meta.get("paragraph_ref"),
        "law": "VVG",
        "edition": meta.get("edition"),
        "main_author": meta.get("main_author"),
        "volume_id": meta.get("volume_id"),
        "rn_count": len(rns),
        "rn_overview": overview,
    }


def search_vvg_keyword(keyword: str, max_results: int = 50, in_footnotes: bool = False,
                      edition: Optional[int] = None, include_bedingungen: bool = True) -> dict:
    """Volltextsuche VVG-Korpus + optional Bedingungswerke."""
    keyword = clamp_query(keyword, 300)
    max_results = clamp_limit(max_results, default=50, max_value=200)
    if not keyword:
        return {"keyword": keyword, "count": 0, "results": []}
    editions = [edition] if edition else [10, 9]
    kw_lower = keyword.lower()
    matches: list[dict] = []

    # VVG-§§
    for ed in editions:
        for (paragraph_ref, rn_num, rn_text, authors, page_from, fn_count, fussnoten,
             stable_key, ent_edition) in _load_vvg_corpus_cache(ed):
            score = (rn_text or "").lower().count(kw_lower)
            if in_footnotes:
                for fn in fussnoten:
                    fn_text = fn.get("fn_text_raw", "")
                    score += (fn_text or "").lower().count(kw_lower)
            if score == 0:
                continue
            hay = rn_text or ""
            idx = hay.lower().find(kw_lower)
            if idx == -1 and in_footnotes:
                for fn in fussnoten:
                    ft = fn.get("fn_text_raw", "")
                    if kw_lower in (ft or "").lower():
                        hay = f"[FN {fn.get('fn_num')}] " + ft
                        idx = hay.lower().find(kw_lower)
                        break
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(hay), idx + 220)
                snippet = ("..." if start > 0 else "") + hay[start:end] + ("..." if end < len(hay) else "")
            else:
                snippet = hay[:300]
            matches.append({
                "source": "VVG-§§",
                "paragraph_ref": paragraph_ref,
                "rn_num": rn_num,
                "stable_key": stable_key,
                "snippet": snippet,
                "author": authors[0] if authors else "",
                "edition": ent_edition,
                "page_from": page_from,
                "fn_count": fn_count,
                "score": score,
            })

    # Bedingungswerke
    if include_bedingungen:
        for (klausel_ref, werk, rn_num, rn_text, page_from, fn_count,
             stable_key, ent_edition) in _load_vvg_bedingungen_cache():
            score = (rn_text or "").lower().count(kw_lower)
            if score == 0:
                continue
            hay = rn_text or ""
            idx = hay.lower().find(kw_lower)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(hay), idx + 220)
                snippet = ("..." if start > 0 else "") + hay[start:end] + ("..." if end < len(hay) else "")
            else:
                snippet = hay[:300]
            matches.append({
                "source": "VVG-Bedingungen",
                "werk": werk,
                "klausel_ref": klausel_ref,
                "rn_num": rn_num,
                "stable_key": stable_key,
                "snippet": snippet,
                "edition": ent_edition,
                "page_from": page_from,
                "score": score,
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {
        "keyword": keyword,
        "in_footnotes": in_footnotes,
        "include_bedingungen": include_bedingungen,
        "total_found": len(matches),
        "count": min(len(matches), max_results),
        "results": matches[:max_results],
    }


def get_vvg_bedingung(werk: str, klausel_id: str) -> dict:
    """Liefert die Kommentierung einer Klausel aus AHB/ARB/AKB."""
    if werk not in {"AHB_2016", "ARB_2010", "AKB_2015"}:
        return {"found": False, "reason": "invalid_werk", "werk": werk}
    klausel_id = clamp_query(klausel_id, 50)
    if not klausel_id:
        return {"found": False, "reason": "missing_klausel_id"}
    src = _VVG_BED_ENRICHED if _VVG_BED_ENRICHED.exists() else _VVG_BED_EXTRACTED
    if not src.exists():
        return {"found": False, "reason": "bedingungen_dir_missing"}
    # Slug
    slug = (
        klausel_id.replace("Ziff.", "Ziff").replace("§", "")
        .strip().replace(" ", "_").replace(".", "-")
    )
    slug = re.sub(r"[^\w\-]", "", slug)
    cands = list(src.glob(f"__{slug}_{werk}__*.json"))
    if not cands:
        return {"found": False, "reason": "klausel_not_found", "werk": werk, "klausel_id": klausel_id, "slug": slug}
    f = cands[0]
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return {"found": False, "reason": "file_load_error", "error": str(e)}
    return {
        "found": True,
        "source": f"Bruck/Möller VVG Großkommentar — {werk}",
        "werk": d.get("werk"),
        "werk_label": d.get("werk_label"),
        "klausel_ref": d.get("klausel_ref"),
        "klausel_id": d.get("klausel_id"),
        "klausel_title": d.get("klausel_title"),
        "edition": d.get("edition"),
        "main_author": d.get("main_author"),
        "rn_count": len(d.get("randnummern", [])),
        "randnummern": d.get("randnummern", []),
        "file": f.name,
    }


# ============================================================================
# BERLINER KOMMENTAR VVG (HONSELL 1999) — DE+AT
# ============================================================================

_BK_VVG_BASE: Path = Path("/Users/reinhardberger/HCS/Kommentare/DE_AT/VVG/berliner")
_BK_VVG_EXTRACTED: Path = _BK_VVG_BASE / "extracted_v2"
_BK_VVG_ENRICHED: Path = _BK_VVG_BASE / "enriched_v2"
_bk_vvg_cache: list[tuple] = []


def _find_bk_vvg_file(num_str: str, suffix: str) -> Optional[Path]:
    """Lookup BK VVG §-File. enriched_v2 -> extracted_v2."""
    para_part = f"{num_str}{suffix}"
    prefix = f"__{para_part}_VVG__"
    for dir_path in [_BK_VVG_ENRICHED, _BK_VVG_EXTRACTED]:
        if not dir_path.exists():
            continue
        cands = list(dir_path.glob(f"{prefix}*_VVG_aufl1_v2.json"))
        if not cands:
            continue

        def sort_key(p: Path):
            is_generic = "__BK_VVG__" in p.name
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                rn_count = len(d.get("randnummern", []))
            except Exception:
                rn_count = 0
            return (is_generic, -rn_count)

        return sorted(cands, key=sort_key)[0]
    return None


def get_bk_vvg_artikel(paragraph: str) -> dict:
    """Kompletter Berliner-Kommentar-VVG-Artikel."""
    paragraph = clamp_query(paragraph, 100)
    if not paragraph:
        return {"found": False, "reason": "missing_paragraph"}
    num_str, suffix = _parse_vvg_paragraph(paragraph)
    f = _find_bk_vvg_file(num_str, suffix)
    if not f:
        return {"found": False, "paragraph": paragraph, "reason": "paragraph_not_found_in_bk_vvg_corpus"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return {"found": False, "reason": "file_load_error", "error": str(e)}
    return {
        "found": True,
        "source": "Berliner Kommentar VVG (Honsell 1999)",
        "scope": "DE+AT",
        "stand": "1998-09-15",
        "paragraph_ref": data.get("paragraph_ref"),
        "edition": data.get("edition"),
        "main_author": data.get("main_author"),
        "rn_count": len(data.get("randnummern", [])),
        "randnummern": data.get("randnummern", []),
        "file": f.name,
    }


def search_bk_vvg_randziffer(paragraph: str, rn_num: int) -> dict:
    """Einzelne Randnummer aus BK VVG."""
    paragraph = clamp_query(paragraph, 100)
    try:
        rn_num = int(rn_num)
    except (TypeError, ValueError):
        return {"found": False, "reason": "invalid_rn_num"}
    num_str, suffix = _parse_vvg_paragraph(paragraph)
    f = _find_bk_vvg_file(num_str, suffix)
    if not f:
        return {"found": False, "reason": "paragraph_not_found"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {"found": False, "reason": "file_load_error"}
    for rn in data.get("randnummern", []):
        if rn.get("rn_num") == rn_num:
            page_authors = rn.get("page_authors", [])
            author = page_authors[0] if page_authors else data.get("main_author", "BK_VVG")
            zit = f"BK/{author} § {num_str}{suffix} VVG Rn {rn_num}"
            return {
                "found": True,
                "source": "Berliner Kommentar VVG (Honsell 1999)",
                "scope": "DE+AT",
                "paragraph_ref": data.get("paragraph_ref"),
                "rn_num": rn["rn_num"],
                "rn_text": rn.get("rn_text", ""),
                "char_count": rn.get("char_count"),
                "page_authors": page_authors,
                "zitiervorschlag": zit,
                "enrichment": rn.get("enrichment", {}),
                "fussnoten": rn.get("fussnoten", []),
            }
    return {"found": False, "reason": "rn_not_found", "rn_num": rn_num}


def _bk_mojibake_variants(keyword: str) -> list[str]:
    """Erzeugt OCR-Mojibake-Varianten der Suchanfrage.

    BK 1999 wurde via PdfCompressor 3.1.34 OCRed — typische Umlaut-Fehler:
    - ü → ii / ti / U / u (Riicktritt, fUr, tiber, dnvergehen)
    - ö → o (Osterreich, Erhohung, Konnen)
    - ä → a (geandert, Pramie, Verkaufer)
    - ß → B (mUssen, beschrankt, BeschluB)

    Returns list of variants to OR-match. Inkl. das Original.
    """
    variants = {keyword, keyword.lower()}
    kl = keyword.lower()
    # Generate de-umlauted variant + ASCII-mappings
    mappings = [
        ("ü", "ii"), ("ü", "u"), ("ü", "ti"), ("ü", "U"),
        ("ö", "o"), ("ö", "O"),
        ("ä", "a"), ("ä", "A"),
        ("ß", "B"), ("ß", "ss"),
        ("Ü", "U"), ("Ü", "ii"),
        ("Ö", "O"),
        ("Ä", "A"),
    ]
    # Generate de-umlauted variant
    ascii_v = (
        kl.replace("ü", "u").replace("ö", "o").replace("ä", "a").replace("ß", "ss")
    )
    variants.add(ascii_v)
    # For each umlaut in keyword, generate variants
    for orig, repl in mappings:
        if orig in keyword:
            variants.add(keyword.replace(orig, repl))
            variants.add(keyword.lower().replace(orig.lower(), repl.lower()))
    # Also: query without umlauts — try matching uppercase-O for Ö
    if "ö" in kl or "ü" in kl or "ä" in kl:
        variants.add(kl.replace("ö", "o").replace("ü", "ii").replace("ä", "a"))
        variants.add(kl.replace("ö", "O").replace("ü", "U").replace("ä", "A"))
    return [v for v in variants if v and len(v) >= 2]


def search_bk_vvg_keyword(keyword: str, max_results: int = 50,
                          mojibake_tolerant: bool = True) -> dict:
    """Volltextsuche im Berliner Kommentar VVG.

    Mit `mojibake_tolerant=True` (default): erzeugt Umlaut-Varianten der Suchanfrage,
    um OCR-Schäden im BK zu kompensieren. z.B. 'österreich' findet auch 'Osterreich'.
    """
    keyword = clamp_query(keyword, 300)
    max_results = clamp_limit(max_results, default=50, max_value=200)
    if not keyword:
        return {"keyword": keyword, "count": 0, "results": []}

    if mojibake_tolerant:
        search_terms = _bk_mojibake_variants(keyword)
    else:
        search_terms = [keyword.lower()]

    matches: list[dict] = []
    seen: set = set()
    src = _BK_VVG_ENRICHED if _BK_VVG_ENRICHED.exists() else _BK_VVG_EXTRACTED
    if not src.exists():
        return {"keyword": keyword, "count": 0, "results": []}

    for f in sorted(src.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        paragraph_ref = data.get("paragraph_ref", "")
        for rn in data.get("randnummern", []):
            txt = rn.get("rn_text", "")
            txt_lower = (txt or "").lower()
            # Score: total count across all variants
            score = 0
            best_idx = -1
            best_term = ""
            for term in search_terms:
                t_lower = term.lower()
                cnt = txt_lower.count(t_lower)
                if cnt > 0:
                    score += cnt
                    if best_idx == -1:
                        best_idx = txt_lower.find(t_lower)
                        best_term = term
            if score == 0:
                continue
            dedup_key = (paragraph_ref, rn.get("rn_num"))
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            if best_idx >= 0:
                start = max(0, best_idx - 80)
                end = min(len(txt), best_idx + 220)
                snippet = ("..." if start > 0 else "") + txt[start:end] + ("..." if end < len(txt) else "")
            else:
                snippet = txt[:300]
            page_authors = rn.get("page_authors", [])
            matches.append({
                "source": "Berliner Kommentar VVG",
                "paragraph_ref": paragraph_ref,
                "rn_num": rn.get("rn_num"),
                "matched_variant": best_term if best_term != keyword else None,
                "snippet": snippet,
                "author": page_authors[0] if page_authors else "",
                "schlagworte": (rn.get("enrichment") or {}).get("schlagworte", []),
                "score": score,
            })
            if len(matches) >= max_results * 3:
                break
        if len(matches) >= max_results * 3:
            break

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {
        "keyword": keyword,
        "mojibake_variants_tried": search_terms if mojibake_tolerant else [],
        "total_found": len(matches),
        "count": min(len(matches), max_results),
        "results": matches[:max_results],
    }


# ============================================================================
# CROSS-KORPUS-COMPARE — BK VVG (DE+AT) <-> Bruck/Möller (DE)
# ============================================================================

# AT VersVG <-> DE VVG n.F. (2008+) Mapping
# Bei Reform 2008 wurde die §-Nummerierung im DE-VVG geändert; AT VersVG hat Original-Nummerierung
AT_DE_VVG_MAPPING = {
    # AT-§ → DE-VVG-§ (n.F.)
    "6": "28",       # Obliegenheitsverletzung
    "16": "19",      # Anzeigepflicht
    "17": "20",
    "18": "21",
    "19": "21",
    "20": "21",
    "21": "21",
    "22": "22",      # Arglist
    "38": "37",      # Erstprämie Verzug
    "39": "38",      # Folgeprämie Verzug
    "69": "95",      # Vertragsübergang Veräußerung
    "70": "96",
    "96": "92",      # Schadenkündigung
    "158": "125",    # RSV
    "158a": "125",
    "158b": "126",
    "158c": "127",   # Anwaltswahl
    "158d": "128",
    "158e": "128",
    "158k": "127",   # Direktanspruch
    "158m": "127",
    "158n": "128",
}
DE_AT_VVG_MAPPING = {v: k for k, v in AT_DE_VVG_MAPPING.items()}


def compare_vvg_kommentare(paragraph: str, source_law: str = "auto",
                            include_at_praxis: bool = True) -> dict:
    """Vergleicht BK VVG (Honsell 1999, DE+AT) + Bruck/Möller (DE n.F.) + optional AT-Praxis.

    source_law: "AT", "DE", oder "auto" (default — versucht beide).
    include_at_praxis: True (default) — ergänzt AT-Praxisliteratur-Treffer.

    Bei AT-§ wird auto-mapped auf DE-§ via AT_DE_VVG_MAPPING.
    """
    # Parse paragraph
    paragraph = clamp_query(paragraph, 100)
    m = re.search(r"(\d{1,4})([a-z]?)", paragraph)
    if not m:
        return {"error": "invalid_paragraph", "paragraph": paragraph}
    num_str = m.group(1)
    suf = m.group(2) or ""
    full_key = f"{num_str}{suf}"

    # Determine paragraphs to look up
    if source_law == "AT":
        bk_para = f"§ {full_key}"
        bm_de_para = AT_DE_VVG_MAPPING.get(full_key, full_key)
        bm_para = f"§ {bm_de_para}"
        mapping_note = f"AT § {full_key} VersVG → DE § {bm_de_para} VVG (Reform 2008)"
    elif source_law == "DE":
        bm_para = f"§ {full_key}"
        bk_at_para = DE_AT_VVG_MAPPING.get(full_key, full_key)
        bk_para = f"§ {bk_at_para}"
        mapping_note = f"DE § {full_key} VVG n.F. → AT § {bk_at_para} VersVG"
    else:  # auto: try AT-mapping first (BK is DE+AT pre-Reform); same para in both
        bk_para = f"§ {full_key}"
        bm_de_para = AT_DE_VVG_MAPPING.get(full_key, full_key)
        bm_para = f"§ {bm_de_para}"
        if bm_de_para != full_key:
            mapping_note = f"auto-Mapping: AT § {full_key} VersVG ≡ DE § {bm_de_para} VVG"
        else:
            mapping_note = "kein AT/DE-Mapping nötig (selbe Nummer)"

    bk = get_bk_vvg_artikel(bk_para)
    bm = get_vvg_artikel(bm_para)

    def snippet(d: dict, n: int = 350) -> str:
        if not d.get("found"):
            return ""
        rns = d.get("randnummern", [])
        if not rns:
            return ""
        return (rns[0].get("rn_text", "") or "")[:n]

    result = {
        "query_paragraph": paragraph,
        "source_law": source_law,
        "mapping_note": mapping_note,
        "berliner_kommentar": {
            "paragraph_ref": bk.get("paragraph_ref"),
            "scope": "DE+AT (pre-Reform 1998)",
            "found": bk.get("found"),
            "rn_count": bk.get("rn_count"),
            "main_author": bk.get("main_author") if bk.get("found") else None,
            "first_rn_snippet": snippet(bk),
        },
        "bruck_moeller": {
            "paragraph_ref": bm.get("meta", {}).get("paragraph_ref") if bm.get("found") else None,
            "scope": "DE (post-Reform 2008)",
            "found": bm.get("found"),
            "edition": bm.get("meta", {}).get("edition") if bm.get("found") else None,
            "rn_count": bm.get("rn_count"),
            "main_author": bm.get("meta", {}).get("main_author") if bm.get("found") else None,
            "first_rn_snippet": snippet(bm),
        },
        "summary": (
            f"BK {bk.get('rn_count', 0)} Rn ({bk.get('main_author', '?')}) "
            f"vs Bruck/Möller {bm.get('rn_count', 0)} Rn "
            f"({bm.get('meta', {}).get('main_author', '?') if bm.get('found') else '?'})."
        ),
    }

    if include_at_praxis:
        at_hits = find_at_praxis_by_paragraph(f"§ {full_key} VersVG", max_results=20)
        result["at_praxisliteratur"] = {
            "scope": "AT-Spezialwerke (9 Werke, 6.894 chunks)",
            "found": at_hits.get("count", 0) > 0,
            "total_chunks": at_hits.get("count", 0),
            "works_mentioning": at_hits.get("works", []),
            "top_chunks": at_hits.get("results", [])[:5],
        }

    return result


# ============================================================================
# AT-PRAXISLITERATUR — 9 Werke, Chunk-basiert
# ============================================================================

_AT_PRAXIS_BASE: Path = Path("/Users/reinhardberger/HCS/Kommentare/AT/VersVG/praxisliteratur")
_AT_PRAXIS_ENRICHED: Path = _AT_PRAXIS_BASE / "enriched_chunks"
_AT_PRAXIS_EXTRACTED: Path = _AT_PRAXIS_BASE / "extracted_chunks"
_at_praxis_cache: list[dict] = []


def _load_at_praxis_cache() -> list[dict]:
    """Lädt Cache: bevorzugt enriched, aber komplettiert mit extracted für ungelabelte Chunks.

    Strategie: extracted ist die Master-Liste (alle 6.894). enriched hat Subset
    mit enrichment-Field. Beim Lookup verwenden wir enriched wenn da, sonst extracted.
    """
    global _at_praxis_cache
    if _at_praxis_cache:
        return _at_praxis_cache
    # Index by file name: enriched hat Priorität
    by_name: dict[str, dict] = {}
    if _AT_PRAXIS_EXTRACTED.exists():
        for f in sorted(_AT_PRAXIS_EXTRACTED.glob("*.json")):
            try:
                by_name[f.name] = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
    if _AT_PRAXIS_ENRICHED.exists():
        for f in sorted(_AT_PRAXIS_ENRICHED.glob("*.json")):
            try:
                by_name[f.name] = json.loads(f.read_text(encoding="utf-8"))  # Override with enriched
            except Exception:
                continue
    _at_praxis_cache = list(by_name.values())
    return _at_praxis_cache


def search_at_praxis_keyword(keyword: str, source_work: str = "", max_results: int = 30) -> dict:
    """Volltextsuche AT-Praxisliteratur."""
    keyword = clamp_query(keyword, 300)
    max_results = clamp_limit(max_results, default=30, max_value=100)
    if not keyword:
        return {"keyword": keyword, "count": 0, "results": []}
    kw_lower = keyword.lower()
    chunks = _load_at_praxis_cache()
    matches: list[dict] = []

    for c in chunks:
        if source_work and c.get("source_work") != source_work:
            continue
        text = c.get("chunk_text", "")
        score = (text or "").lower().count(kw_lower)
        if score == 0:
            continue
        idx = text.lower().find(kw_lower)
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(text), idx + 220)
            snippet_text = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
        else:
            snippet_text = text[:300]
        matches.append({
            "stable_key": c["stable_key"],
            "source_work": c.get("source_work"),
            "source_label": c.get("source_label"),
            "work_zitiervorschlag": c.get("work_zitiervorschlag", ""),
            "section_path": c.get("section_path", []),
            "page_from": c.get("page_from"),
            "snippet": snippet_text,
            "referenced_paragraphs": c.get("referenced_paragraphs", [])[:10],
            "schlagworte": (c.get("enrichment") or {}).get("schlagworte", []),
            "score": score,
        })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {
        "keyword": keyword,
        "source_work_filter": source_work or None,
        "total_found": len(matches),
        "count": min(len(matches), max_results),
        "results": matches[:max_results],
    }


def find_at_praxis_by_paragraph(paragraph: str, max_results: int = 30) -> dict:
    """Reverse-Lookup: alle Chunks die diesen § referenzieren."""
    paragraph = clamp_query(paragraph, 50)
    if not paragraph:
        return {"paragraph": paragraph, "count": 0, "results": []}
    chunks = _load_at_praxis_cache()
    matches: list[dict] = []
    works_set: set = set()

    # Normalize query — match auf "§ X GESETZ"
    para_norm = paragraph.strip()
    if not para_norm.startswith("§"):
        para_norm = f"§ {para_norm}"

    for c in chunks:
        refs = c.get("referenced_paragraphs", [])
        if any(para_norm in r or r in para_norm for r in refs):
            works_set.add(c.get("source_work", "?"))
            matches.append({
                "stable_key": c["stable_key"],
                "source_work": c.get("source_work"),
                "source_label": c.get("source_label"),
                "section_path": c.get("section_path", []),
                "page_from": c.get("page_from"),
                "snippet": (c.get("chunk_text", "") or "")[:300],
                "all_paragraphs_in_chunk": refs[:10],
                "schlagworte": (c.get("enrichment") or {}).get("schlagworte", []),
            })

    return {
        "paragraph": para_norm,
        "total_found": len(matches),
        "count": min(len(matches), max_results),
        "works": sorted(works_set),
        "results": matches[:max_results],
    }


def get_at_praxis_chunk(stable_key: str) -> dict:
    """Liefert kompletten Chunk per stable_key."""
    stable_key = clamp_query(stable_key, 200)
    if not stable_key.startswith("at-praxis|"):
        return {"error": "invalid_stable_key"}
    # Parse: at-praxis|<slug>|chunk_NNNN
    parts = stable_key.split("|")
    if len(parts) < 3:
        return {"error": "invalid_format"}
    slug = parts[1]
    chunk_part = parts[2]  # chunk_NNNN
    fname = f"{slug}__{chunk_part}.json"
    for d in [_AT_PRAXIS_ENRICHED, _AT_PRAXIS_EXTRACTED]:
        f = d / fname
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                return {"found": True, **data}
            except Exception as e:
                return {"error": "load_error", "detail": str(e)}
    return {"found": False, "stable_key": stable_key, "tried_file": fname}


# ============================================================================
# AT-LEHRBÜCHER-SAMMLUNG — 46 Werke, Chunk-basiert
# ============================================================================

_AT_LIT_BASE: Path = Path("/Users/reinhardberger/HCS/Kommentare/AT/lehrbuecher_sammlung")
_AT_LIT_ENRICHED: Path = _AT_LIT_BASE / "enriched_chunks"
_AT_LIT_EXTRACTED: Path = _AT_LIT_BASE / "extracted_chunks"
_AT_LIT_MANIFEST: Path = _AT_LIT_BASE / "at_lehrbuecher_volumes.json"
_at_lit_cache: list[dict] = []
_at_lit_works_meta: dict[str, dict] = {}


def _load_at_lit_cache() -> list[dict]:
    """Lade Cache (merged enriched + extracted; enriched hat Vorrang)."""
    global _at_lit_cache, _at_lit_works_meta
    if _at_lit_cache:
        return _at_lit_cache
    # Load manifest (works-meta)
    if _AT_LIT_MANIFEST.exists():
        try:
            m = json.loads(_AT_LIT_MANIFEST.read_text(encoding="utf-8"))
            for w in m.get("works", []):
                _at_lit_works_meta[w["slug"]] = w
        except Exception:
            pass
    by_name: dict[str, dict] = {}
    if _AT_LIT_EXTRACTED.exists():
        for f in sorted(_AT_LIT_EXTRACTED.glob("*.json")):
            try:
                by_name[f.name] = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
    if _AT_LIT_ENRICHED.exists():
        for f in sorted(_AT_LIT_ENRICHED.glob("*.json")):
            try:
                by_name[f.name] = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
    # Augment chunks with subject_area from manifest
    for d in by_name.values():
        slug = d.get("source_work")
        if slug in _at_lit_works_meta:
            d.setdefault("subject_area", _at_lit_works_meta[slug].get("subject_area", ""))
    _at_lit_cache = list(by_name.values())
    return _at_lit_cache


def search_at_lehrbuch_keyword(keyword: str, subject_area: str = "",
                               source_work: str = "", max_results: int = 30) -> dict:
    keyword = clamp_query(keyword, 300)
    max_results = clamp_limit(max_results, default=30, max_value=100)
    if not keyword:
        return {"keyword": keyword, "count": 0, "results": []}
    kw_lower = keyword.lower()
    chunks = _load_at_lit_cache()
    matches: list[dict] = []

    for c in chunks:
        if source_work and c.get("source_work") != source_work:
            continue
        if subject_area and c.get("subject_area") != subject_area:
            continue
        text = c.get("chunk_text", "")
        score = (text or "").lower().count(kw_lower)
        if score == 0:
            continue
        idx = text.lower().find(kw_lower)
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(text), idx + 220)
            snippet_text = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
        else:
            snippet_text = text[:300]
        matches.append({
            "stable_key": c["stable_key"],
            "source_work": c.get("source_work"),
            "source_label": c.get("source_label"),
            "subject_area": c.get("subject_area"),
            "section_path": c.get("section_path", []),
            "page_from": c.get("page_from"),
            "snippet": snippet_text,
            "referenced_paragraphs": c.get("referenced_paragraphs", [])[:10],
            "schlagworte": (c.get("enrichment") or {}).get("schlagworte", []),
            "score": score,
        })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return {
        "keyword": keyword,
        "subject_area_filter": subject_area or None,
        "source_work_filter": source_work or None,
        "total_found": len(matches),
        "count": min(len(matches), max_results),
        "results": matches[:max_results],
    }


def find_at_lehrbuch_by_paragraph(paragraph: str, max_results: int = 30) -> dict:
    paragraph = clamp_query(paragraph, 50)
    if not paragraph:
        return {"paragraph": paragraph, "count": 0, "results": []}
    chunks = _load_at_lit_cache()
    matches: list[dict] = []
    works_set: set = set()
    para_norm = paragraph.strip()
    if not para_norm.startswith("§"):
        para_norm = f"§ {para_norm}"

    for c in chunks:
        refs = c.get("referenced_paragraphs", [])
        if any(para_norm in r or r in para_norm for r in refs):
            works_set.add(c.get("source_work", "?"))
            matches.append({
                "stable_key": c["stable_key"],
                "source_work": c.get("source_work"),
                "source_label": c.get("source_label"),
                "subject_area": c.get("subject_area"),
                "section_path": c.get("section_path", []),
                "page_from": c.get("page_from"),
                "snippet": (c.get("chunk_text", "") or "")[:300],
                "all_paragraphs_in_chunk": refs[:10],
                "schlagworte": (c.get("enrichment") or {}).get("schlagworte", []),
            })

    return {
        "paragraph": para_norm,
        "total_found": len(matches),
        "count": min(len(matches), max_results),
        "works": sorted(works_set),
        "results": matches[:max_results],
    }


def get_at_lehrbuch_chunk(stable_key: str) -> dict:
    stable_key = clamp_query(stable_key, 200)
    if not stable_key.startswith("at-lit|"):
        return {"error": "invalid_stable_key"}
    parts = stable_key.split("|")
    if len(parts) < 3:
        return {"error": "invalid_format"}
    slug = parts[1]
    chunk_part = parts[2]
    fname = f"{slug}__{chunk_part}.json"
    for d in [_AT_LIT_ENRICHED, _AT_LIT_EXTRACTED]:
        f = d / fname
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                return {"found": True, **data}
            except Exception as e:
                return {"error": "load_error", "detail": str(e)}
    return {"found": False, "stable_key": stable_key, "tried_file": fname}


def list_at_lehrbuecher_werke(subject_area: str = "") -> dict:
    if not _at_lit_works_meta:
        _load_at_lit_cache()  # populates works_meta
    works = []
    subject_areas: dict[str, int] = {}
    for slug, w in sorted(_at_lit_works_meta.items()):
        sa = w.get("subject_area", "")
        subject_areas[sa] = subject_areas.get(sa, 0) + 1
        if subject_area and sa != subject_area:
            continue
        works.append({
            "slug": slug,
            "title": w.get("title"),
            "autoren": w.get("autoren"),
            "year": w.get("year"),
            "page_count": w.get("page_count"),
            "subject_area": sa,
            "layout_typ": w.get("layout_typ"),
        })
    return {
        "filter_subject_area": subject_area or None,
        "total_works": len(works),
        "subject_areas_summary": dict(sorted(subject_areas.items())),
        "works": works,
    }


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
