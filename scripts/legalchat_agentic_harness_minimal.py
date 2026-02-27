#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path("/Users/reinhardberger/HCS/lobe-chat-custom")
REPORT_ROOT = ROOT / "_review" / "test_reports"
ONESHOT_RUNNER = ROOT / "scripts" / "zivilrecht_oneshot_functional_compare.py"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MCP_BASE = "http://127.0.0.1:8070"
DEFAULT_REMOTE_SSH = "root@46.225.110.68"
DEFAULT_REMOTE_MCP_CONTAINER = "mcp-zivilrecht"
DEFAULT_CONFIG_DIR = ROOT / "config"
DEFAULT_AGENT_PROFILES_PATH = DEFAULT_CONFIG_DIR / "agent_profiles.yaml"
DEFAULT_MCP_REGISTRY_PATH = DEFAULT_CONFIG_DIR / "mcp_registry.yaml"
DEFAULT_SKILLS_BINDINGS_PATH = DEFAULT_CONFIG_DIR / "skills_bindings.yaml"

BUILTIN_MODEL_PROFILES: dict[str, dict[str, str]] = {
    "cheap_default": {
        "organizer": "qwen/qwen3-coder-next",
        "worker": "google/gemini-2.5-flash-lite",
        "synth": "google/gemini-3-flash-preview",
    },
    "cheap_grok_fast": {
        "organizer": "qwen/qwen3-coder-next",
        "worker": "x-ai/grok-4.1-fast",
        "synth": "x-ai/grok-4.1-fast",
    },
    "default": {
        "organizer": "qwen/qwen3-coder-next",
        "worker": "google/gemini-3-flash-preview",
        "synth": "x-ai/grok-4.1-fast",
    },
    "premium_champion": {
        "organizer": "openai/gpt-5.3-codex",
        "worker": "x-ai/grok-4.1-fast",
        "synth": "openai/gpt-5.3-codex",
    },
    "qwen_all": {
        "organizer": "qwen/qwen3-coder-next",
        "worker": "qwen/qwen3-coder-next",
        "synth": "qwen/qwen3-coder-next",
    },
    "nemotron_worker_qwen_synth": {
        "organizer": "qwen/qwen3-coder-next",
        "worker": "nvidia/nemotron-3-nano-30b-a3b:free",
        "synth": "qwen/qwen3-coder-next",
    },
    "nemotron_all": {
        "organizer": "nvidia/nemotron-3-nano-30b-a3b:free",
        "worker": "nvidia/nemotron-3-nano-30b-a3b:free",
        "synth": "nvidia/nemotron-3-nano-30b-a3b:free",
    },
    "cheap_parallel": {
        "organizer": "liquid/lfm-2-24b-a2b",
        "worker": "google/gemini-2.5-flash-lite",
        "synth": "google/gemini-3-flash-preview",
        "classifier": "liquid/lfm-2-24b-a2b",
    },
}

# ---------------------------------------------------------------------------
# Phase 2: Domain Classifier
# ---------------------------------------------------------------------------
RECHTSGEBIET_PATTERNS: dict[str, list[str]] = {
    "sozialversicherung": [
        r"\bASVG\b", r"\bPension\b", r"\bInvalidit", r"\bRehabilitationsgeld\b",
        r"\bVersicherungsfall\b", r"\bGeminderte\s+Arbeitsfähigkeit\b",
        r"\bBerufsunfähigkeit\b", r"\b§\s*\d+\s*ASVG\b", r"\bPVA\b",
    ],
    "exekution": [
        r"\bEO\b", r"\bExekution\b", r"\bOppositionsklage\b", r"\b§\s*\d+[a-d]?\s*EO\b",
        r"\bZwangsversteigerung\b", r"\bFahrnisexekution\b", r"\bDrittschuldner\b",
        r"\bPfändung\b", r"\bVollstreckung\b",
    ],
    "zustellrecht": [
        r"\bZust(?:G|ell)\b", r"\bZustellung\b", r"\bHinterlegung\b",
        r"\bErsatzzustellung\b", r"\bZustellmangel\b", r"\b§\s*\d+\s*ZustG\b",
        r"\bAbgabestelle\b", r"\bZustellversuch\b", r"\bZustellzeugnis\b",
        r"\bHZÜ\b", r"\bHaager\s+Zustellung", r"\bRechtshilfe(?:ersuchen)?\b",
        r"\bAnnahmeverweigerung\b", r"\bGeoForm\s*44\b", r"\b§\s*163\s*Geo\b",
        r"\bZMR.Abfrage\b", r"\bOrtsabwes", r"\babgemeldet\b",
    ],
    "interzession": [
        r"\bInterzession\b", r"\bSchuldbeitritt\b", r"\b§\s*25[a-d]?\s*KSchG\b",
        r"\bMithaftung\b", r"\bBürgschaft\b", r"\bWarnpflicht\b",
    ],
    "schadenersatz": [
        r"\bSchadenersatz\b", r"\bSchmerzensgeld\b", r"\bHaftung\b",
        r"\b§\s*1295\s*ABGB\b", r"\b§\s*1325\s*ABGB\b", r"\bKausalität\b",
        r"\bVerschulden\b", r"\bMitverschulden\b",
    ],
    "vertragsrecht": [
        r"\bVertrag\b", r"\bGewährleistung\b", r"\bIrrtum\b",
        r"\bAnfechtung\b", r"\bWandellung\b", r"\bPreisminderung\b",
        r"\blaesio\s+enormis\b", r"\bVertragsauflösung\b",
    ],
    "familienrecht": [
        r"\bScheidung\b", r"\bUnterhalt\b", r"\bObsorge\b", r"\bEhegatten\b",
        r"\bKindesunterhalt\b", r"\b§\s*\d+\s*EheG\b",
    ],
    "erbrecht": [
        r"\bErb(?:recht|folge|anspruch|teil)\b", r"\bPflichtteil\b",
        r"\bTestament\b", r"\bVermächtnis\b", r"\bVerlassenschaft\b",
    ],
    "sachenrecht": [
        r"\bEigentum\b", r"\bBesitz\b", r"\bGrundbuch\b", r"\bPfandrecht\b",
        r"\bServitut\b", r"\bErsitzung\b",
    ],
    "wohnungseigentum": [
        r"\bWEG\b", r"\bWohnungseigentum", r"\bEigentümergemeinschaft\b",
        r"\bHausverwaltung\b", r"\ballgemeine[rn]?\s+Teil", r"\bMiteigentum",
        r"\bRücklage\b", r"\bBetriebskosten\b", r"\bNutzwert\b",
        r"\b§\s*\d+\s*WEG\b", r"\bWohnungseigentumsanlage\b",
    ],
    "insolvenzrecht": [
        r"\bInsolvenz\b", r"\bKonkurs\b", r"\bSanierung\b", r"\b§\s*\d+\s*IO\b",
        r"\bMasseforderung\b", r"\bAnfechtung\b.*\bIO\b",
    ],
    "arbeitsrecht": [
        r"\bKündigung\b", r"\bEntlassung\b", r"\bAbfertigung\b",
        r"\bArbeitsvertrag\b", r"\bBetriebsrat\b", r"\bArbG\b",
    ],
    "konsumentenschutz": [
        r"\bKSchG\b", r"\bVerbraucher\b", r"\bRücktrittsrecht\b",
        r"\bHaustürgeschäft\b", r"\bFernabsatz\b",
    ],
    "zivilprozess": [
        r"\bZPO\b", r"\bKlage\b", r"\bBerufung\b", r"\bRevision\b",
        r"\bStreitwert\b", r"\b§\s*\d+\s*ZPO\b",
    ],
}

DOMAIN_MANDATORY_PARAGRAPHS: dict[str, list[str]] = {
    "schadenersatz": ["§ 1295 ABGB", "§ 1299 ABGB", "§ 1298 ABGB", "§ 1313a ABGB", "§ 1325 ABGB"],
    "vertragsrecht": ["§ 871 ABGB", "§ 872 ABGB", "§ 874 ABGB", "§ 877 ABGB", "§ 879 ABGB", "§ 922 ABGB", "§ 932 ABGB", "§ 934 ABGB"],
    "interzession": ["§ 25c KSchG", "§ 25d KSchG", "§ 879 ABGB", "§ 1346 ABGB"],
    "exekution": ["§ 35 EO", "§ 36 EO", "§ 40 EO", "§ 42 EO"],
    "erbrecht": ["§ 762 ABGB", "§ 774 ABGB", "§ 780 ABGB", "§ 781 ABGB"],
    "familienrecht": ["§ 90 ABGB", "§ 94 ABGB", "§ 49 EheG", "§ 55a EheG"],
    "sachenrecht": ["§ 367 ABGB", "§ 431 ABGB", "§ 480 ABGB", "§ 1500 ABGB"],
    "konsumentenschutz": ["§ 6 KSchG", "§ 9 KSchG", "§ 25c KSchG", "§ 25d KSchG"],
    "wohnungseigentum": ["§ 2 WEG", "§ 3 WEG", "§ 16 WEG", "§ 20 WEG", "§ 28 WEG", "§ 30 WEG", "§ 32 WEG", "§ 52 WEG"],
    "zustellrecht": ["§ 2 ZustG", "§ 7 ZustG", "§ 8 ZustG", "§ 12 ZustG", "§ 17 ZustG", "§ 22 ZustG"],
}

SUBDOMAIN_PATTERNS: dict[str, tuple[str, list[str], list[str]]] = {
    "arzthaftung": ("schadenersatz", [r"\bArzt\b", r"\bBehandlung", r"\bOperation\b", r"\bKunstfehler\b", r"\bAufkl.rung", r"\bDiagnose\b", r"\bKrankenhaus\b", r"\bLagerung\b", r"\bNarkose\b"],
                    ["§ 1295 ABGB", "§ 1299 ABGB", "§ 1298 ABGB", "§ 1313a ABGB", "§ 1325 ABGB", "§ 228 ZPO"]),
    "angehoerigenburgschaft": ("interzession", [r"\bAngehörig", r"\bEhegatt", r"\bHausfrau\b", r"\beinkommenlos", r"\bBürgschaft\b", r"\bmitunterschrieb", r"\bVersäumungsurteil\b", r"\bExekution\b"],
                              ["§ 25c KSchG", "§ 25d KSchG", "§ 879 ABGB", "§ 35 EO", "§ 1346 ABGB"]),
    "immobilienkauf": ("vertragsrecht", [r"\bLiegenschaft", r"\bWohnung", r"\bKauf.*(?:Haus|Wohnung)", r"\bImmobilie"],
                      ["§ 922 ABGB", "§ 932 ABGB", "§ 871 ABGB", "§ 874 ABGB", "§ 934 ABGB"]),
    "weg_erhaltung": ("wohnungseigentum", [r"\bErhaltung", r"\bHeiz", r"\bÖltank", r"\bÖlaustritt", r"\bMangel.*(?:allgemein|gemeinsam)", r"\bInstandhaltung", r"\bSanierung"],
                      ["§ 28 WEG", "§ 30 WEG", "§ 20 WEG", "§ 1318 ABGB"]),
    "hzue_rechtshilfe": ("zustellrecht", [r"\bHZÜ\b", r"\bHaager\b", r"\bRechtshilfe", r"\bBMJ\b", r"\bUS.Complaint\b", r"\bSummons\b", r"\bAffidavit", r"\bGeoForm", r"\b§\s*163\s*Geo"],
                         ["§ 17 ZustG", "§ 2 ZustG", "§ 7 ZustG", "§ 8 ZustG", "§ 12 ZustG"]),
    "hinterlegung_abgabestelle": ("zustellrecht", [r"\bHinterlegung\b", r"\bAbgabestelle\b", r"\babgemeldet\b", r"\bOrtsabwes", r"\bwohn.*nicht\s*mehr", r"\bumgezogen\b"],
                                  ["§ 17 ZustG", "§ 2 ZustG", "§ 8 ZustG"]),
}

_PARAGRAPH_RX = re.compile(r"§\s*(\d+[a-z]?)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöü]{1,15})")


def classify_domain(query: str) -> dict[str, Any]:
    """Deterministic domain classifier based on regex patterns."""
    text = query or ""
    scores: dict[str, float] = {}
    for domain, patterns in RECHTSGEBIET_PATTERNS.items():
        hits = sum(1 for p in patterns if re.search(p, text, re.I))
        if hits:
            scores[domain] = hits / len(patterns)
    paragraphs = [f"§ {m.group(1)} {m.group(2)}" for m in _PARAGRAPH_RX.finditer(text)]
    keywords = []
    for domain, score in sorted(scores.items(), key=lambda x: -x[1])[:3]:
        keywords.append(domain.replace("_", " ").title())
    best = max(scores, key=scores.get) if scores else ""
    confidence = scores.get(best, 0.0) if best else 0.0
    # Inject mandatory paragraphs and sub-domain detection
    mandatory = list(DOMAIN_MANDATORY_PARAGRAPHS.get(best, []))
    subdomain = ""
    for sd_name, (parent, sd_patterns, sd_pars) in SUBDOMAIN_PATTERNS.items():
        if parent == best and any(re.search(p, text, re.I) for p in sd_patterns):
            subdomain = sd_name
            mandatory = list(dict.fromkeys(sd_pars + mandatory))  # dedup, sd_pars first
            break
    all_paragraphs = list(dict.fromkeys(mandatory + paragraphs))
    return {
        "domain": best,
        "subdomain": subdomain,
        "confidence": round(confidence, 3),
        "paragraphs": all_paragraphs[:12],
        "mandatory_paragraphs": mandatory,
        "keywords": keywords[:5],
        "all_scores": {k: round(v, 3) for k, v in sorted(scores.items(), key=lambda x: -x[1])[:5]},
    }


def classify_domain_with_llm_fallback(
    query: str,
    classifier_model: str,
) -> dict[str, Any]:
    """Run deterministic classifier; if confidence < 0.5, use cheap LLM fallback."""
    result = classify_domain(query)
    if result["confidence"] >= 0.5:
        result["source"] = "deterministic"
        return result
    if not classifier_model:
        result["source"] = "deterministic_low_confidence"
        return result
    try:
        sys_msg = (
            "You classify Austrian legal queries into a domain. "
            "Return ONLY valid JSON: "
            '{"domain":"...","paragraphs":["§ X LAW",...],"keywords":["..."]}'
        )
        usr_msg = query[:500]
        resp, _ = openrouter_chat(
            model=classifier_model,
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": usr_msg}],
            max_tokens=200,
            temperature=0.0,
            tools=None,
            tool_choice=None,
            provider=_openrouter_provider_for_model(classifier_model),
            reasoning=None,
            models=None,
            title="legalchat-domain-classifier",
        )
        msg = ((resp.get("choices") or [{}])[0] or {}).get("message") or {}
        parsed = extract_json_object(message_text(msg))
        if isinstance(parsed, dict):
            return {
                "domain": str(parsed.get("domain") or result["domain"]),
                "confidence": 0.7,
                "paragraphs": list(parsed.get("paragraphs") or result["paragraphs"])[:8],
                "keywords": list(parsed.get("keywords") or result["keywords"])[:5],
                "source": "llm",
                "all_scores": result.get("all_scores", {}),
            }
    except Exception:
        pass
    result["source"] = "deterministic_llm_failed"
    return result


BUILTIN_TOOL_SPECS: dict[str, dict[str, Any]] = {
    "search_ogh_rechtssaetze": {
        "type": "function",
        "function": {
            "name": "search_ogh_rechtssaetze",
            "description": "Search OGH legal principles (Rechtssaetze).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["query"],
            },
        },
    },
    "get_rechtssatz": {
        "type": "function",
        "function": {
            "name": "get_rechtssatz",
            "description": "Fetch one RS by number.",
            "parameters": {
                "type": "object",
                "properties": {"rs_number": {"type": "string"}},
                "required": ["rs_number"],
            },
        },
    },
    "search_ogh_entscheidungen": {
        "type": "function",
        "function": {
            "name": "search_ogh_entscheidungen",
            "description": "Search OGH decisions (TE) and return business numbers and summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["query"],
            },
        },
    },
    "hot_rs_search": {
        "type": "function",
        "function": {
            "name": "hot_rs_search",
            "description": "Search in hot zivilrecht RS index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["query"],
            },
        },
    },
    "hot_cluster_context": {
        "type": "function",
        "function": {
            "name": "hot_cluster_context",
            "description": "Get cluster grounding context with RS and mini stories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cluster_id": {"type": "string"},
                    "topic_id": {"type": "string"},
                    "rs_limit": {"type": "integer", "minimum": 1, "maximum": 30},
                    "te_limit_per_rs": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["cluster_id"],
            },
        },
    },
    "search_kommentar_paragraph": {
        "type": "function",
        "function": {
            "name": "search_kommentar_paragraph",
            "description": "Search legal commentaries by paragraph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string"},
                    "law": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["paragraph"],
            },
        },
    },
    "search_kommentar_keyword": {
        "type": "function",
        "function": {
            "name": "search_kommentar_keyword",
            "description": "Search legal commentaries by keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                    "law": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["keyword"],
            },
        },
    },
    "search_by_paragraph": {
        "type": "function",
        "function": {
            "name": "search_by_paragraph",
            "description": "Find OGH Rechtssaetze for a specific statute paragraph, e.g. '§ 934 ABGB'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paragraph": {"type": "string", "description": "Paragraph in format '§ 934 ABGB', '§ 351 UGB'"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["paragraph"],
            },
        },
    },
    "search_by_schlagwort": {
        "type": "function",
        "function": {
            "name": "search_by_schlagwort",
            "description": "Search OGH Rechtssaetze by exact OGH taxonomy keyword tag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "schlagwort": {"type": "string", "description": "Exact keyword, e.g. 'Bereicherungsrecht', 'Schadenersatz'"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["schlagwort"],
            },
        },
    },
    "hot_rs_lookup": {
        "type": "function",
        "function": {
            "name": "hot_rs_lookup",
            "description": "Fetch a specific RS from the Hot Index with TE mini-stories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rs_number": {"type": "string", "description": "RS number, e.g. 'RS0037089'"},
                    "te_limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["rs_number"],
            },
        },
    },
    "hot_index_stats": {
        "type": "function",
        "function": {
            "name": "hot_index_stats",
            "description": "Show release info, counts and freshness of the Hot Zivil Index.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    "build_grounding_context": {
        "type": "function",
        "function": {
            "name": "build_grounding_context",
            "description": "Build grounding context for a legal question: auto-detects relevant topic clusters and returns minimal ruleset with RS citations. HIGH VALUE tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic name, e.g. 'schadenersatz', 'bereicherungsrecht', 'erbrecht', 'laesio_enormis', 'allgemeiner_teil', 'vertraege', 'sachenrecht', 'familienrecht', 'schuldrecht_bt', 'internationale_bezuege', 'mehrpersonal', 'pflichtteilsrecht'"},
                    "query": {"type": "string", "description": "Legal question or case description"},
                    "max_clusters": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1},
                    "max_tokens": {"type": "integer", "minimum": 100, "maximum": 1000, "default": 500},
                },
                "required": ["topic", "query"],
            },
        },
    },
    "detect_clusters": {
        "type": "function",
        "function": {
            "name": "detect_clusters",
            "description": "Detect relevant legal clusters for a question via keyword matching. Returns cluster IDs and match scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic name, e.g. 'schadenersatz', 'bereicherungsrecht'"},
                    "query": {"type": "string", "description": "Legal question or case description"},
                },
                "required": ["topic", "query"],
            },
        },
    },
    "ask_gemini_zivilrecht": {
        "type": "function",
        "function": {
            "name": "ask_gemini_zivilrecht",
            "description": "Ask the fine-tuned Gemini expert model for Austrian civil law (Laesio Enormis, Bereicherungsrecht, Pflichtteilsrecht). Returns expert-level legal analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Legal question in German"},
                    "context": {"type": "string", "description": "Optional case context"},
                },
                "required": ["question"],
            },
        },
    },
}

BUILTIN_DEFAULT_WORKSTREAMS = [
    {
        "name": "ogh_rs_core",
        "goal": "Find the most relevant OGH RS + TE and capture stable references.",
        "tools": ["search_ogh_rechtssaetze", "search_ogh_entscheidungen", "get_rechtssatz", "search_by_paragraph", "search_by_schlagwort"],
    },
    {
        "name": "hot_index_context",
        "goal": "Retrieve top hot-index context and mini-story evidence.",
        "tools": ["hot_rs_search", "hot_cluster_context", "hot_rs_lookup"],
    },
    {
        "name": "grounding_expert",
        "goal": "Get cluster-level grounding context and expert analysis for the legal question.",
        "tools": ["build_grounding_context", "detect_clusters", "ask_gemini_zivilrecht", "search_kommentar_paragraph", "search_kommentar_keyword"],
    },
]

MODEL_PROFILES: dict[str, dict[str, str]] = dict(BUILTIN_MODEL_PROFILES)
TOOL_SPECS: dict[str, dict[str, Any]] = dict(BUILTIN_TOOL_SPECS)
DEFAULT_WORKSTREAMS = [dict(x) for x in BUILTIN_DEFAULT_WORKSTREAMS]
ROLE_ALLOWED_TOOLS: dict[str, set[str]] = {
    "organizer": set(TOOL_SPECS.keys()),
    "worker": set(TOOL_SPECS.keys()),
    "synth": set(),
    "citation_repair": set(),
}
MCP_RUNTIME: dict[str, Any] = {
    "modes": {
        "local_http": {"base_url": DEFAULT_MCP_BASE},
        "remote_http": {"base_url": DEFAULT_MCP_BASE},
        "remote_ssh": {"ssh_host": DEFAULT_REMOTE_SSH, "container": DEFAULT_REMOTE_MCP_CONTAINER},
    },
    "guardrails": {
        "statement_timeout_ms": 30000,
        "max_result_rows": 50,
        "max_query_length": 500,
        "max_parallel_streams": 3,
    },
}
TOOL_POLICY: dict[str, dict[str, Any]] = {
    name: {
        "timeout_sec": 30,
        "retry_count": 1,
        "retry_backoff_sec": 0.8,
        "max_limit": 50,
        "max_query_length": 500,
    }
    for name in TOOL_SPECS.keys()
}
SKILL_BINDINGS: dict[str, Any] = {}


def _load_yaml_map(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _valid_tools(items: list[str]) -> set[str]:
    return {x for x in items if x in TOOL_SPECS}


def role_skill_context(role: str) -> str:
    roles = SKILL_BINDINGS.get("roles") if isinstance(SKILL_BINDINGS, dict) else None
    rec = roles.get(role) if isinstance(roles, dict) else None
    if not isinstance(rec, dict):
        return ""
    goals = _as_str_list(rec.get("goals"))
    skill_recs = rec.get("skills")
    required: list[str] = []
    optional: list[str] = []
    if isinstance(skill_recs, list):
        for item in skill_recs:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id") or "").strip()
            if not sid:
                continue
            if bool(item.get("required")):
                required.append(sid)
            else:
                optional.append(sid)
    lines: list[str] = []
    if goals:
        lines.append("Role goals:")
        lines.extend([f"- {g}" for g in goals[:6]])
    if required:
        lines.append("Required skills:")
        lines.extend([f"- {s}" for s in required[:8]])
    if optional:
        lines.append("Optional skills:")
        lines.extend([f"- {s}" for s in optional[:8]])
    return "\n".join(lines).strip()


def role_tools(role: str) -> set[str]:
    allowed = ROLE_ALLOWED_TOOLS.get(role)
    if allowed is None:
        return set(TOOL_SPECS.keys())
    return set(allowed)


def filter_tools_for_role(tools: list[str], role: str) -> list[str]:
    allowed = role_tools(role)
    return [t for t in tools if t in allowed]


def tool_policy(tool: str) -> dict[str, Any]:
    return TOOL_POLICY.get(tool) or {}


def apply_runtime_config(config_dir: Path) -> dict[str, Any]:
    global MODEL_PROFILES, ROLE_ALLOWED_TOOLS, MCP_RUNTIME, TOOL_POLICY, SKILL_BINDINGS

    applied: dict[str, Any] = {"config_dir": str(config_dir), "files": {}}
    ap_map = _load_yaml_map(config_dir / "agent_profiles.yaml")
    mcp_map = _load_yaml_map(config_dir / "mcp_registry.yaml")
    skills_map = _load_yaml_map(config_dir / "skills_bindings.yaml")

    profiles_raw = ap_map.get("profiles")
    if isinstance(profiles_raw, dict):
        parsed: dict[str, dict[str, str]] = {}
        for name, rec in profiles_raw.items():
            if not isinstance(rec, dict):
                continue
            organizer = str(rec.get("organizer") or "").strip()
            worker = str(rec.get("worker") or "").strip()
            synth = str(rec.get("synth") or "").strip()
            if organizer and worker and synth:
                entry: dict[str, str] = {"organizer": organizer, "worker": worker, "synth": synth}
                classifier = str(rec.get("classifier") or "").strip()
                if classifier:
                    entry["classifier"] = classifier
                parsed[str(name)] = entry
        if parsed:
            MODEL_PROFILES = parsed
            applied["files"]["agent_profiles"] = {"path": str(config_dir / "agent_profiles.yaml"), "profiles": len(parsed)}

    roles_raw = mcp_map.get("roles")
    if isinstance(roles_raw, dict):
        role_map = dict(ROLE_ALLOWED_TOOLS)
        for role in ("organizer", "worker", "synth", "citation_repair"):
            role_cfg = roles_raw.get(role)
            if not isinstance(role_cfg, dict):
                continue
            allow = _valid_tools(_as_str_list(role_cfg.get("allow_tools")))
            if allow:
                role_map[role] = allow
        ROLE_ALLOWED_TOOLS = role_map

    tools_raw = mcp_map.get("tools")
    if isinstance(tools_raw, dict):
        merged_policy = dict(TOOL_POLICY)
        for tool_name, cfg in tools_raw.items():
            if tool_name not in TOOL_SPECS or not isinstance(cfg, dict):
                continue
            cur = dict(merged_policy.get(tool_name) or {})
            for key in ("timeout_sec", "retry_count", "retry_backoff_sec", "max_limit", "max_query_length"):
                if key in cfg:
                    cur[key] = cfg.get(key)
            merged_policy[tool_name] = cur
        TOOL_POLICY = merged_policy

    guardrails_raw = mcp_map.get("guardrails")
    if isinstance(guardrails_raw, dict):
        merged_rt = dict(MCP_RUNTIME)
        current_guard = dict(merged_rt.get("guardrails") or {})
        for key in ("statement_timeout_ms", "max_result_rows", "max_query_length", "max_parallel_streams"):
            if key in guardrails_raw:
                current_guard[key] = guardrails_raw.get(key)
        merged_rt["guardrails"] = current_guard
        modes_raw = mcp_map.get("modes")
        if isinstance(modes_raw, dict):
            merged_rt["modes"] = modes_raw
        MCP_RUNTIME = merged_rt
        applied["files"]["mcp_registry"] = {
            "path": str(config_dir / "mcp_registry.yaml"),
            "tools_with_policy": len([k for k in TOOL_POLICY if TOOL_POLICY.get(k)]),
            "roles": {k: len(v) for k, v in ROLE_ALLOWED_TOOLS.items()},
        }

    if skills_map:
        SKILL_BINDINGS = skills_map
        applied["files"]["skills_bindings"] = {"path": str(config_dir / "skills_bindings.yaml"), "roles": len(skills_map.get("roles") or {})}
    return applied


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_runner_module():
    spec = importlib.util.spec_from_file_location("zr_runner_harness", str(ONESHOT_RUNNER))
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load runner module: {ONESHOT_RUNNER}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_openrouter_keys() -> list[str]:
    keys: list[tuple[int, str]] = []
    for k, v in os.environ.items():
        m = re.fullmatch(r"OPENROUTER_API_KEY_(\d+)", k)
        if m and v.strip():
            keys.append((int(m.group(1)), v.strip()))
    keys.sort(key=lambda x: x[0])
    out = [v for _, v in keys]
    single = os.getenv("OPENROUTER_API_KEY", "").strip()
    if single:
        out.append(single)
    return out


def message_text(msg: dict[str, Any]) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for item in c:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def maybe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text


def extract_json_object(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


NORM_LAW_CODES_UP = {
    "ABGB",
    "ZPO",
    "EO",
    "ZUSTG",
    "AVG",
    "ASVG",
    "ASGG",
    "VERSVG",
    "KSCHG",
    "AHG",
    "IO",
    "STGB",
    "SMG",
    "GEO",
    "FSG",
    "STVO",
    "EMRK",
    "HZÜ",
    "DSA",
    "EUV",
    "VVG",
    "ARB",
    "ZSTG",
    "SPG",
    "AVB",
    "UGB",
}
_OGH_GZ_RX = re.compile(
    r"\b\d{1,2}\s*(?:Ob|Os|OCg|ONc|ONs|ONe|OK|Op|Nc|Nd|Ocg|Onc|Ons|One)\s*\d{1,4}/\d{2}[a-zA-Z]?\b"
)


def _normalize_rs_number(token: str) -> str:
    t = (token or "").upper().replace(" ", "").replace("-", "")
    m = re.match(r"^RS(\d{7})$", t)
    return f"RS{m.group(1)}" if m else ""


def extract_rs_numbers(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"\bRS[\s\-]?\d{7}\b", text or "", flags=re.I):
        rs = _normalize_rs_number(m.group(0))
        if rs and rs not in seen:
            seen.add(rs)
            out.append(rs)
    return out


def _normalize_ogh_gz(token: str) -> str:
    t = re.sub(r"\s+", "", token or "")
    t = t.replace("\\", "/")
    m = re.match(r"^(\d{1,2})([A-Za-z]{1,4})(\d{1,4}/\d{2}[A-Za-z]?)$", t)
    if not m:
        return t
    senate = m.group(2)
    if len(senate) == 1:
        senate_norm = senate.upper()
    elif len(senate) == 2:
        senate_norm = senate[0].upper() + senate[1].lower()
    else:
        senate_norm = senate[0].upper() + senate[1:]
    suffix = m.group(3)
    if suffix and suffix[-1].isalpha():
        suffix = suffix[:-1] + suffix[-1].lower()
    return f"{m.group(1)}{senate_norm}{suffix}"


def extract_ogh_te_citations(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in _OGH_GZ_RX.finditer(text or ""):
        gz = _normalize_ogh_gz(m.group(0))
        if gz and gz not in seen:
            seen.add(gz)
            out.append(gz)
    return out


def extract_rw_citations(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"\bRW[\s\-]?\d{7}\b", text or "", flags=re.I):
        tok = (m.group(0) or "").upper().replace(" ", "").replace("-", "")
        if tok and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def _normalize_norm_citation(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"\bArt\.\s*", "Art ", s, flags=re.I)
    s = re.sub(r"\bAbs\.\s*", "Abs ", s, flags=re.I)
    s = re.sub(r"\bZ\.\s*", "Z ", s, flags=re.I)
    s = re.sub(r"\blit\.\s*", "lit ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*,\s*", ", ", s)
    return s.strip(" ,;:.")


def extract_norm_citations(text: str) -> list[str]:
    txt = text or ""
    law_alt = r"(?:ABGB|ZPO|EO|ZustG|AVG|ASVG|ASGG|VersVG|KSchG|AHG|IO|StGB|SMG|Geo|FSG|StVO|EMRK|HZÜ|DSA|EUV|VVG|ARB|ZStG|SPG|AVB|UGB)"
    par_pat = re.compile(rf"§{{1,2}}\s*[^.\n;:]{{0,90}}?\b{law_alt}\b")
    art_pat = re.compile(
        rf"Art\.?\s*\d+[a-zA-Z]?(?:\s*Abs\.?\s*\d+)?(?:\s*Z\s*\d+)?(?:\s*lit\.?\s*[a-z])?\s+{law_alt}\b",
        re.I,
    )
    canon: list[str] = []
    seen: set[str] = set()
    for pat in (par_pat, art_pat):
        for m in pat.finditer(txt):
            c = _normalize_norm_citation(m.group(0))
            law_m = re.search(r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöü]{1,15})\b$", c)
            law_code = law_m.group(1).upper() if law_m else None
            if not law_code or law_code not in NORM_LAW_CODES_UP:
                continue
            if c not in seen:
                seen.add(c)
                canon.append(c)
    return canon


# Prefer shared citation validator module when available.
try:
    import citation_validator as _cv

    NORM_LAW_CODES_UP = set(_cv.NORM_LAW_CODES_UP)
    _normalize_rs_number = _cv.normalize_rs_number
    extract_rs_numbers = _cv.extract_rs_numbers
    _normalize_ogh_gz = _cv.normalize_ogh_gz
    extract_ogh_te_citations = _cv.extract_ogh_te_citations
    extract_rw_citations = _cv.extract_rw_citations
    _normalize_norm_citation = _cv.normalize_norm_citation
    extract_norm_citations = _cv.extract_norm_citations
except Exception:
    _cv = None


def http_json(url: str, payload: dict[str, Any], timeout: float = 30.0) -> tuple[dict[str, Any], float]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        txt = resp.read().decode("utf-8", errors="replace")
        return json.loads(txt), (time.perf_counter() - t0) * 1000.0


def remote_ssh_tool_call(
    tool: str,
    args: dict[str, Any],
    remote_ssh: str,
    remote_mcp_container: str,
    timeout: float = 45.0,
) -> dict[str, Any]:
    helper = f"""
import json, time, urllib.request
tool = {json.dumps(tool)}
payload = json.loads({json.dumps(json.dumps(args))})
url = "http://127.0.0.1:8070/tool/" + tool
t0 = time.perf_counter()
try:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={{"Content-Type":"application/json"}})
    with urllib.request.urlopen(req, timeout=25) as r:
        txt = r.read().decode("utf-8", errors="replace")
        print(json.dumps({{"ok": True, "status": r.status, "latency_ms": round((time.perf_counter()-t0)*1000, 2), "body": json.loads(txt)}}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({{"ok": False, "status": None, "latency_ms": round((time.perf_counter()-t0)*1000, 2), "error": str(e)}}, ensure_ascii=False))
"""
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", remote_ssh, "docker", "exec", "-i", remote_mcp_container, "python3", "-"],
        input=helper,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    wrapper_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or f"ssh/docker rc={proc.returncode}"
        return {"ok": False, "status": None, "latency_ms": None, "body": None, "error": err, "wrapper_ms": wrapper_ms}
    try:
        body = json.loads(proc.stdout.strip())
        body["wrapper_ms"] = wrapper_ms
        return body
    except Exception as e:
        return {
            "ok": False,
            "status": None,
            "latency_ms": None,
            "body": None,
            "error": f"remote_parse_error: {e}; stdout={proc.stdout[:500]}",
            "wrapper_ms": wrapper_ms,
        }


def docker_exec_tool_call(
    tool: str,
    args: dict[str, Any],
    container: str,
    timeout: float = 45.0,
) -> dict[str, Any]:
    """Like remote_ssh_tool_call but runs docker exec directly (no SSH hop)."""
    helper = f"""
import json, time, urllib.request
tool = {json.dumps(tool)}
payload = json.loads({json.dumps(json.dumps(args))})
url = "http://127.0.0.1:8070/tool/" + tool
t0 = time.perf_counter()
try:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={{"Content-Type":"application/json"}})
    with urllib.request.urlopen(req, timeout=25) as r:
        txt = r.read().decode("utf-8", errors="replace")
        print(json.dumps({{"ok": True, "status": r.status, "latency_ms": round((time.perf_counter()-t0)*1000, 2), "body": json.loads(txt)}}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({{"ok": False, "status": None, "latency_ms": round((time.perf_counter()-t0)*1000, 2), "error": str(e)}}, ensure_ascii=False))
"""
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "python3", "-"],
        input=helper,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    wrapper_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or f"docker exec rc={proc.returncode}"
        return {"ok": False, "status": None, "latency_ms": None, "body": None, "error": err, "wrapper_ms": wrapper_ms}
    try:
        result = json.loads(proc.stdout.strip())
        result["wrapper_ms"] = wrapper_ms
        return result
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "ok": False,
            "status": None,
            "latency_ms": None,
            "body": None,
            "error": f"docker_parse_error: {e}; stdout={proc.stdout[:500]}",
            "wrapper_ms": wrapper_ms,
        }


def call_mcp_tool(
    tool: str,
    args: dict[str, Any],
    mcp_mode: str,
    mcp_base: str,
    remote_ssh: str,
    remote_mcp_container: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    pol = tool_policy(tool)
    timeout_sec = float(pol.get("timeout_sec") or timeout)
    retry_count = max(0, int(pol.get("retry_count") or 0))
    retry_backoff = float(pol.get("retry_backoff_sec") or 0.8)
    effective_timeout = max(5.0, timeout_sec)

    def _single_call() -> dict[str, Any]:
        if mcp_mode == "remote_ssh":
            return remote_ssh_tool_call(
                tool=tool,
                args=args,
                remote_ssh=remote_ssh,
                remote_mcp_container=remote_mcp_container,
                timeout=max(45.0, effective_timeout + 10.0),
            )
        if mcp_mode == "docker_exec":
            return docker_exec_tool_call(
                tool=tool,
                args=args,
                container=remote_mcp_container,
                timeout=max(45.0, effective_timeout + 10.0),
            )
        if mcp_mode not in {"local_http", "remote_http"}:
            return {
                "ok": False,
                "status": None,
                "latency_ms": None,
                "body": None,
                "error": f"unsupported_mcp_mode:{mcp_mode}",
            }
        try:
            body, ms = http_json(f"{mcp_base}/tool/{tool}", args, timeout=effective_timeout)
            return {
                "ok": bool(body.get("ok")) if isinstance(body, dict) else False,
                "status": 200,
                "latency_ms": round(ms, 2),
                "body": body,
                "error": None,
            }
        except urllib.error.HTTPError as e:
            try:
                txt = e.read().decode("utf-8", errors="replace")
            except Exception:
                txt = str(e)
            return {"ok": False, "status": e.code, "latency_ms": None, "body": None, "error": txt}
        except Exception as e:
            return {"ok": False, "status": None, "latency_ms": None, "body": None, "error": str(e)}

    attempts = retry_count + 1
    last: dict[str, Any] | None = None
    for idx in range(attempts):
        rec = _single_call()
        if rec.get("ok"):
            rec["attempt"] = idx + 1
            return rec
        last = rec
        status = rec.get("status")
        retriable = (status is None) or (status in {408, 409, 425, 429}) or (isinstance(status, int) and status >= 500)
        if idx + 1 >= attempts or not retriable:
            break
        time.sleep(max(0.2, retry_backoff) * (idx + 1))
    out = dict(last or {})
    out["attempt"] = attempts
    return out


def parse_tool_payload(body: dict[str, Any] | None) -> Any:
    if not isinstance(body, dict):
        return body
    result = body.get("result")
    if not isinstance(result, dict):
        return result
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and isinstance(first.get("text"), str):
            return maybe_json(first.get("text", ""))
    return result


def fallback_answer_from_tool_traces(stream_name: str, traces: list[dict[str, Any]]) -> str:
    lines = []
    lines.append(f"Fallback summary for stream {stream_name}:")
    ok = [x for x in traces if x.get("ok")]
    lines.append(f"- successful_tool_calls: {len(ok)}/{len(traces)}")
    for idx, rec in enumerate(ok[:5], start=1):
        preview = str(rec.get("payload_preview") or "").strip()
        if len(preview) > 500:
            preview = preview[:500] + "..."
        lines.append(f"- call_{idx} tool={rec.get('tool')}: {preview}")
    return "\n".join(lines)


def _openrouter_usage_snapshot(raw_resp: dict[str, Any]) -> dict[str, Any]:
    usage = raw_resp.get("usage") if isinstance(raw_resp, dict) else None
    if not isinstance(usage, dict):
        return {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    cost = usage.get("cost")
    prompt_details = usage.get("prompt_tokens_details") if isinstance(usage.get("prompt_tokens_details"), dict) else {}
    completion_details = (
        usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
    )
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost": cost,
        "cached_tokens": prompt_details.get("cached_tokens"),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
    }


_OR_SUPPORTED_PARAMS_CACHE: dict[str, set[str]] = {}


def _openrouter_supported_parameters(model: str) -> set[str]:
    mid = (model or "").strip()
    if not mid:
        return set()
    cached = _OR_SUPPORTED_PARAMS_CACHE.get(mid)
    if cached is not None:
        return cached
    keys = load_openrouter_keys()
    if not keys:
        _OR_SUPPORTED_PARAMS_CACHE[mid] = set()
        return set()
    req = urllib.request.Request(
        f"https://openrouter.ai/api/v1/parameters/{urllib.parse.quote(mid, safe='')}",
        method="GET",
        headers={"Authorization": f"Bearer {keys[0]}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        data = raw.get("data") if isinstance(raw, dict) else None
        obj = data if isinstance(data, dict) else raw
        params = obj.get("supported_parameters") if isinstance(obj, dict) else None
        out = {str(x).strip() for x in (params or []) if str(x).strip()}
        _OR_SUPPORTED_PARAMS_CACHE[mid] = out
        return out
    except Exception:
        _OR_SUPPORTED_PARAMS_CACHE[mid] = set()
        return set()


def _openrouter_provider_for_model(model: str) -> dict[str, Any]:
    provider: dict[str, Any] = {"require_parameters": True}
    if (model or "").startswith("google/gemini-3-flash-preview"):
        provider["order"] = ["google-ai-studio", "google-vertex"]
    return provider


def _openrouter_reasoning_for_role(model: str, role: str) -> dict[str, Any] | None:
    supported = _openrouter_supported_parameters(model)
    if "reasoning" not in supported:
        return None
    if not (model or "").startswith("google/gemini-3-flash-preview"):
        return None
    role_l = (role or "").strip().lower()
    if role_l == "worker":
        return {"effort": "low"}
    if role_l in {"synth", "repair"}:
        return {"effort": "medium"}
    return {"effort": "minimal"}


def _openrouter_model_fallbacks(model: str) -> list[str] | None:
    if (model or "").startswith("google/gemini-3-flash-preview"):
        return ["x-ai/grok-4.1-fast", "qwen/qwen3-coder-next"]
    return None


def _openrouter_response_format_for_model(model: str, role: str) -> dict[str, Any] | None:
    if role != "organizer":
        return None
    supported = _openrouter_supported_parameters(model)
    if "response_format" in supported:
        return {"type": "json_object"}
    return None


def openrouter_chat(
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 1200,
    temperature: float = 0.0,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    provider: dict[str, Any] | None = None,
    reasoning: dict[str, Any] | None = None,
    models: list[str] | None = None,
    response_format: dict[str, Any] | None = None,
    timeout: float = 140.0,
    title: str = "legalchat-agentic-harness",
) -> tuple[dict[str, Any], float]:
    keys = load_openrouter_keys()
    if not keys:
        raise RuntimeError("No OpenRouter API key found in OPENROUTER_API_KEY(_N)")

    last_err = None
    attempts = max(3, min(8, len(keys) * 2))
    # HTTP headers are latin-1 encoded by urllib/http.client.
    # Sanitize dynamic title fragments (stream names can contain en-dash/umlauts).
    safe_title = title.encode("ascii", errors="ignore").decode("ascii").strip() or "legalchat-agentic-harness"

    for attempt in range(attempts):
        api_key = keys[attempt % len(keys)]
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if models:
            payload["models"] = models
        if provider:
            payload["provider"] = provider
        if reasoning:
            payload["reasoning"] = reasoning
        if response_format:
            payload["response_format"] = response_format
        if tools is not None:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://legalchat.local",
                "X-Title": safe_title,
            },
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                txt = resp.read().decode("utf-8", errors="replace")
                return json.loads(txt), (time.perf_counter() - t0) * 1000.0
        except Exception as e:
            last_err = str(e)
            sleep_s = 1.5 * (attempt + 1)
            if isinstance(e, urllib.error.HTTPError) and getattr(e, "code", None) == 429:
                sleep_s = max(sleep_s, 6.0 + attempt * 2.0)
            time.sleep(sleep_s)
    raise RuntimeError(f"OpenRouter call failed for {model}: {last_err}")


_SEARCH_TOOLS = {"search_ogh_rechtssaetze", "search_ogh_entscheidungen", "search_by_paragraph", "search_by_schlagwort", "hot_rs_search"}
_DEEPEN_TOOLS = ["get_rechtssatz", "hot_rs_lookup"]
_MINIMUM_SEARCH_KIT = ["search_by_paragraph", "search_by_schlagwort", "search_ogh_rechtssaetze"]


def normalize_workstreams(raw: Any, max_workstreams: int, allowed_tools: set[str] | None = None) -> list[dict[str, Any]]:
    ws = raw if isinstance(raw, list) else []
    allowed = set(allowed_tools or TOOL_SPECS.keys())
    out: list[dict[str, Any]] = []
    for item in ws:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        goal = str(item.get("goal") or "").strip()
        tools = item.get("tools")
        if not name:
            continue
        if not goal:
            goal = "Collect legal evidence."
        if not isinstance(tools, list):
            tools = []
        cleaned_tools = [t for t in [str(x).strip() for x in tools] if t in TOOL_SPECS and t in allowed]
        if not cleaned_tools:
            fallback_tools = [x for x in DEFAULT_WORKSTREAMS[min(len(out), len(DEFAULT_WORKSTREAMS) - 1)]["tools"] if x in allowed]
            cleaned_tools = fallback_tools or sorted(allowed)
        # Auto-inject minimum search kit so every stream can search + deepen
        for st in _MINIMUM_SEARCH_KIT:
            if st in TOOL_SPECS and st in allowed and st not in cleaned_tools:
                cleaned_tools.append(st)
        for dt in _DEEPEN_TOOLS:
            if dt in TOOL_SPECS and dt in allowed and dt not in cleaned_tools:
                cleaned_tools.append(dt)
        out.append({"name": name, "goal": goal, "tools": cleaned_tools})
        if len(out) >= max_workstreams:
            break
    if out:
        return out
    fallback: list[dict[str, Any]] = []
    for w in DEFAULT_WORKSTREAMS[:max_workstreams]:
        tools = [x for x in w["tools"] if x in allowed]
        if not tools:
            tools = sorted(allowed)
        fallback.append({"name": w["name"], "goal": w["goal"], "tools": tools})
    return fallback


def _build_plan_openrouter(
    query: str,
    organizer_model: str,
    max_workstreams: int,
    fallback: dict[str, Any],
    classification: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    org_tools = sorted(role_tools("organizer"))
    role_ctx = role_skill_context("organizer")
    sys_prompt = (
        "You are an organizer agent for Austrian legal research. "
        "Return ONLY valid JSON with this schema: "
        '{"workstreams":[{"name":"...","goal":"...","tools":["..."]}],"synthesis_focus":"..."} '
        "Constraints: 2-4 workstreams, tools must come only from this set: "
        + ", ".join(org_tools)
        + "."
    )
    if role_ctx:
        sys_prompt += "\n\n" + role_ctx
    # Inject domain classification hints
    class_hint = ""
    if classification and classification.get("domain"):
        class_hint = f"\n\nDomain: {classification['domain']}"
        sd = classification.get("subdomain")
        if sd:
            class_hint += f" (Sub-domain: {sd})"
        mandatory = classification.get("mandatory_paragraphs") or []
        pars = classification.get("paragraphs") or []
        kws = classification.get("keywords") or []
        if mandatory:
            class_hint += "\nMANDATORY paragraph searches: " + ", ".join(f'search_by_paragraph("{p}")' for p in mandatory[:6])
        elif pars:
            class_hint += "\nPrioritize: " + ", ".join(f'search_by_paragraph("{p}")' for p in pars[:4])
        if kws:
            class_hint += "\nAlso try: " + ", ".join(f'search_by_schlagwort("{k}")' for k in kws[:3])
        # Guide organizer to use power tools for domain-specific questions
        if classification.get("confidence", 0) >= 0.5 and "build_grounding_context" in org_tools:
            class_hint += (
                "\nSTRATEGY: Include a workstream with build_grounding_context + detect_clusters + ask_gemini_zivilrecht "
                "to get cluster-level grounding and expert analysis for this domain."
            )
    usr_prompt = (
        "Question:\n"
        + query
        + class_hint
        + "\n\nBuild a minimal high-signal plan. Prioritize RS, hot-index context, and kommentar context."
        + " Use search_by_paragraph for specific §§ and search_by_schlagwort for OGH taxonomy keywords."
    )
    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": usr_prompt}]
    raw_resp, latency_ms = openrouter_chat(
        model=organizer_model,
        messages=messages,
        max_tokens=800,
        temperature=0.0,
        tools=None,
        tool_choice=None,
        provider=_openrouter_provider_for_model(organizer_model),
        reasoning=_openrouter_reasoning_for_role(organizer_model, "organizer"),
        models=_openrouter_model_fallbacks(organizer_model),
        response_format=_openrouter_response_format_for_model(organizer_model, "organizer"),
        title="legalchat-agentic-organizer",
    )
    msg = ((raw_resp.get("choices") or [{}])[0] or {}).get("message") or {}
    text = message_text(msg)
    parsed = extract_json_object(text)
    if not isinstance(parsed, dict):
        return fallback, {
            "latency_ms": round(latency_ms, 2),
            "raw_text": text,
            "used_fallback": True,
            "usage": _openrouter_usage_snapshot(raw_resp),
        }
    workstreams = normalize_workstreams(
        parsed.get("workstreams"),
        max_workstreams=max_workstreams,
        allowed_tools=role_tools("organizer"),
    )
    plan = {
        "workstreams": workstreams,
        "synthesis_focus": str(parsed.get("synthesis_focus") or fallback["synthesis_focus"]),
    }
    return plan, {
        "latency_ms": round(latency_ms, 2),
        "raw_text": text,
        "used_fallback": False,
        "usage": _openrouter_usage_snapshot(raw_resp),
    }


def _build_plan_opencode_sidecar(
    query: str,
    max_workstreams: int,
    fallback: dict[str, Any],
    sidecar_cmd: str,
    sidecar_timeout_sec: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not sidecar_cmd.strip():
        return fallback, {"latency_ms": None, "raw_text": "", "used_fallback": True, "error": "missing_sidecar_cmd"}
    org_tools = sorted(role_tools("organizer"))
    role_ctx = role_skill_context("organizer")
    prompt = (
        "Return ONLY valid JSON with this schema: "
        '{"workstreams":[{"name":"...","goal":"...","tools":["..."]}],"synthesis_focus":"..."}\n'
        "Constraints:\n"
        f"- max {max_workstreams} workstreams\n"
        "- use only tools from: "
        + ", ".join(org_tools)
        + "\n"
        "Question:\n"
        + query
    )
    if role_ctx:
        prompt += "\n\nRole context:\n" + role_ctx
    argv = shlex.split(sidecar_cmd)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=max(20, int(sidecar_timeout_sec)),
        )
    except Exception as e:
        return fallback, {
            "latency_ms": None,
            "raw_text": "",
            "used_fallback": True,
            "error": f"sidecar_exec_error:{e}",
            "command": sidecar_cmd,
        }
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    if proc.returncode != 0:
        return fallback, {
            "latency_ms": latency_ms,
            "raw_text": proc.stdout[:2000],
            "used_fallback": True,
            "error": proc.stderr.strip() or f"sidecar_rc={proc.returncode}",
            "command": sidecar_cmd,
        }
    raw_text = (proc.stdout or "").strip()
    parsed = extract_json_object(raw_text)
    if not isinstance(parsed, dict):
        return fallback, {
            "latency_ms": latency_ms,
            "raw_text": raw_text[:2000],
            "used_fallback": True,
            "error": "sidecar_output_not_json",
            "command": sidecar_cmd,
        }
    workstreams = normalize_workstreams(
        parsed.get("workstreams"),
        max_workstreams=max_workstreams,
        allowed_tools=role_tools("organizer"),
    )
    plan = {
        "workstreams": workstreams,
        "synthesis_focus": str(parsed.get("synthesis_focus") or fallback["synthesis_focus"]),
    }
    return plan, {
        "latency_ms": latency_ms,
        "raw_text": raw_text[:2000],
        "used_fallback": False,
        "command": sidecar_cmd,
    }


# ---------------------------------------------------------------------------
# Phase 4: Pre-Search Scatter
# ---------------------------------------------------------------------------
def _expand_queries_with_llm(
    query: str,
    classification: dict[str, Any],
    model: str,
) -> dict[str, list[str]]:
    """Use cheap LLM to expand query into paragraph, schlagwort, and keyword queries."""
    if not model:
        return _expand_queries_deterministic(query, classification)
    try:
        sys_msg = (
            "Extract search terms from this Austrian legal query. "
            "Return ONLY valid JSON: "
            '{"paragraph_queries":["§ X LAW",...],"schlagwort_queries":["keyword",...],"keyword_queries":["phrase",...]}'
        )
        resp, _ = openrouter_chat(
            model=model,
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": query[:500]}],
            max_tokens=250,
            temperature=0.0,
            tools=None,
            tool_choice=None,
            provider=_openrouter_provider_for_model(model),
            reasoning=None,
            models=None,
            title="legalchat-query-expansion",
        )
        msg = ((resp.get("choices") or [{}])[0] or {}).get("message") or {}
        parsed = extract_json_object(message_text(msg))
        if isinstance(parsed, dict):
            return {
                "paragraph_queries": list(parsed.get("paragraph_queries") or [])[:4],
                "schlagwort_queries": list(parsed.get("schlagwort_queries") or [])[:4],
                "keyword_queries": list(parsed.get("keyword_queries") or [])[:3],
            }
    except Exception:
        pass
    return _expand_queries_deterministic(query, classification)


def _expand_queries_deterministic(
    query: str,
    classification: dict[str, Any],
) -> dict[str, list[str]]:
    """Deterministic query expansion from classification results."""
    pars = classification.get("paragraphs") or []
    mandatory = classification.get("mandatory_paragraphs") or []
    all_pars = list(dict.fromkeys(mandatory + pars))
    kws = classification.get("keywords") or []
    base = _base_question_text(query)
    return {
        "paragraph_queries": all_pars[:6],
        "schlagwort_queries": kws[:6],
        "keyword_queries": [_compact_search_query(base, max_terms=6)] if base else [],
    }


def run_pre_search_scatter(
    expanded: dict[str, list[str]],
    mcp_mode: str,
    mcp_base: str,
    remote_ssh: str,
    remote_mcp_container: str,
    query: str = "",
    classification: dict[str, Any] | None = None,
) -> str:
    """Run parallel pre-search MCP calls and return formatted evidence string."""
    tasks: list[tuple[str, dict[str, Any]]] = []
    for par in expanded.get("paragraph_queries", [])[:5]:
        tasks.append(("search_by_paragraph", {"paragraph": str(par)[:120], "limit": 8}))
    for sw in expanded.get("schlagwort_queries", [])[:4]:
        tasks.append(("search_by_schlagwort", {"schlagwort": str(sw)[:120], "limit": 8}))
    for kw in expanded.get("keyword_queries", [])[:2]:
        tasks.append(("search_ogh_rechtssaetze", {"query": str(kw)[:200], "limit": 8}))
    # Auto-detect topic and add grounding context + cluster detection
    hints = _extract_retrieval_hints(query) if query else {}
    topic = _topic_hint(query, hints) if query else None
    if topic and "build_grounding_context" in TOOL_SPECS:
        compact_q = _compact_search_query(query, max_terms=12) if query else ""
        if compact_q:
            tasks.append(("build_grounding_context", {"topic": topic, "query": compact_q, "max_clusters": 2, "max_tokens": 500}))
            tasks.append(("detect_clusters", {"topic": topic, "query": compact_q}))
    if not tasks:
        return ""
    results: list[str] = []

    def _call(tool_name: str, args: dict[str, Any]) -> tuple[str, str]:
        call = call_mcp_tool(
            tool=tool_name, args=args,
            mcp_mode=mcp_mode, mcp_base=mcp_base,
            remote_ssh=remote_ssh, remote_mcp_container=remote_mcp_container,
        )
        payload = parse_tool_payload(call.get("body"))
        if call.get("ok") and payload:
            # Grounding context is high-value, give it more preview space
            limit = 1600 if tool_name == "build_grounding_context" else 800
            preview = json.dumps(payload, ensure_ascii=False)[:limit]
            return tool_name, preview
        return tool_name, ""

    with cf.ThreadPoolExecutor(max_workers=min(10, len(tasks))) as pool:
        futs = [pool.submit(_call, t, a) for t, a in tasks]
        for fut in cf.as_completed(futs):
            try:
                tool_name, preview = fut.result()
                if preview:
                    results.append(f"[{tool_name}] {preview}")
            except Exception:
                pass
    # Deduplicate: prioritize high-value tools, skip lines with only already-seen RS
    _HIGH_VALUE = {"build_grounding_context", "detect_clusters", "ask_gemini_zivilrecht"}
    _seen_rs: set[str] = set()
    deduped: list[str] = []
    # High-value tools first
    for line in results:
        if any(f"[{t}]" in line for t in _HIGH_VALUE):
            deduped.append(line)
            _seen_rs.update(rs for rs in extract_rs_numbers(line))
    # Then retrieval tools, skip if all RS already seen
    for line in results:
        if any(f"[{t}]" in line for t in _HIGH_VALUE):
            continue
        _line_rs = set(extract_rs_numbers(line))
        if not _line_rs or (_line_rs - _seen_rs):
            deduped.append(line)
            _seen_rs.update(_line_rs)
    return "\n".join(deduped)[:5000]


def build_plan_with_organizer(
    query: str,
    organizer_model: str,
    max_workstreams: int,
    dry_run: bool,
    organizer_backend: str = "openrouter",
    opencode_sidecar_cmd: str = "",
    opencode_sidecar_timeout_sec: int = 90,
    classifier_model: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    org_allowed = role_tools("organizer")
    fallback_streams: list[dict[str, Any]] = []
    for w in DEFAULT_WORKSTREAMS[:max_workstreams]:
        tools = [t for t in w["tools"] if t in org_allowed]
        if not tools:
            tools = sorted(org_allowed)
        fallback_streams.append({"name": w["name"], "goal": w["goal"], "tools": tools})
    fallback = {
        "workstreams": fallback_streams,
        "synthesis_focus": "Answer the legal question with concrete RS and commentary grounding.",
    }
    if dry_run:
        return fallback, None
    # Phase 2: Domain classification
    classification = classify_domain_with_llm_fallback(query, classifier_model)
    backend = (organizer_backend or "openrouter").strip().lower()
    if backend == "openrouter":
        try:
            plan, meta = _build_plan_openrouter(query=query, organizer_model=organizer_model, max_workstreams=max_workstreams, fallback=fallback, classification=classification)
            meta["classification"] = classification
            return plan, meta
        except Exception as e:
            return fallback, {"latency_ms": None, "raw_text": "", "used_fallback": True, "backend": "openrouter", "error": str(e)}
    if backend == "opencode_sidecar":
        return _build_plan_opencode_sidecar(
            query=query,
            max_workstreams=max_workstreams,
            fallback=fallback,
            sidecar_cmd=opencode_sidecar_cmd,
            sidecar_timeout_sec=opencode_sidecar_timeout_sec,
        )
    if backend == "ab_test":
        openrouter_plan, openrouter_meta = fallback, {
            "latency_ms": None,
            "raw_text": "",
            "used_fallback": True,
            "backend": "openrouter",
            "error": "not_executed",
        }
        sidecar_plan, sidecar_meta = fallback, {
            "latency_ms": None,
            "raw_text": "",
            "used_fallback": True,
            "backend": "opencode_sidecar",
            "error": "not_executed",
        }
        try:
            openrouter_plan, openrouter_meta = _build_plan_openrouter(
                query=query,
                organizer_model=organizer_model,
                max_workstreams=max_workstreams,
                fallback=fallback,
                classification=classification,
            )
        except Exception as e:
            openrouter_meta = {"latency_ms": None, "raw_text": "", "used_fallback": True, "backend": "openrouter", "error": str(e)}
        sidecar_plan, sidecar_meta = _build_plan_opencode_sidecar(
            query=query,
            max_workstreams=max_workstreams,
            fallback=fallback,
            sidecar_cmd=opencode_sidecar_cmd,
            sidecar_timeout_sec=opencode_sidecar_timeout_sec,
        )
        choose_sidecar = (not sidecar_meta.get("used_fallback")) and bool(sidecar_plan.get("workstreams"))
        selected_plan = sidecar_plan if choose_sidecar else openrouter_plan
        meta = {
            "backend": "ab_test",
            "selected": "opencode_sidecar" if choose_sidecar else "openrouter",
            "openrouter": openrouter_meta,
            "opencode_sidecar": sidecar_meta,
            "used_fallback": bool((selected_plan is fallback) or (sidecar_meta.get("used_fallback") and openrouter_meta.get("used_fallback"))),
            "latency_ms": sidecar_meta.get("latency_ms") if choose_sidecar else openrouter_meta.get("latency_ms"),
        }
        return selected_plan, meta
    return fallback, {"latency_ms": None, "raw_text": "", "used_fallback": True, "error": f"unknown_backend:{backend}"}


def _extract_retrieval_hints(query: str) -> dict[str, str]:
    hints: dict[str, str] = {}
    if not query:
        return hints
    rx = re.compile(r"^\s*-\s*(rs_query|hot_query|kommentar_keyword|kommentar_paragraph)\s*=\s*(.+?)\s*$", re.I | re.M)
    for m in rx.finditer(query):
        k = (m.group(1) or "").strip().lower()
        v = (m.group(2) or "").strip()
        if k and v:
            hints[k] = v
    return hints


def _base_question_text(query: str) -> str:
    if not query:
        return ""
    txt = query.split("Retrieval-Hints:")[0]
    txt = txt.strip()
    if not txt:
        txt = query.strip()
    txt = " ".join(txt.split())
    return txt[:220]


def _law_hint_from_text(text: str) -> str | None:
    t = (text or "").upper()
    for law in sorted(NORM_LAW_CODES_UP, key=len, reverse=True):
        if re.search(rf"\b{re.escape(law)}\b", t):
            return law
    return None


SEARCH_STOPWORDS = {
    "bitte",
    "nenne",
    "mir",
    "eine",
    "einen",
    "einem",
    "einer",
    "einschlagige",
    "einschlagigen",
    "einschlägige",
    "einschlägigen",
    "kurze",
    "kurzer",
    "kurzem",
    "kurzer",
    "kurzaussage",
    "kernaussage",
    "mit",
    "und",
    "oder",
    "zur",
    "zum",
    "zuerst",
    "nur",
    "osterreich",
    "österreich",
    "frage",
    "fall",
    "sachverhalt",
    "deckungsanfrage",
    "ogh",
    "rechtssatz",
    "rechtssaetze",
    "rechtssätze",
    "entscheidungen",
    "entscheidung",
    "geschaeftszahl",
    "geschäftszahl",
    "te",
    "rs",
}


def _compact_search_query(text: str, max_terms: int = 8) -> str:
    toks = re.findall(r"[A-Za-zÄÖÜäöüẞß0-9§/]+", text or "")
    keep: list[str] = []
    for tok in toks:
        low = tok.lower()
        if len(low) <= 2:
            continue
        if low in SEARCH_STOPWORDS:
            continue
        keep.append(tok)

    def _umlaut_variant(tok: str) -> str | None:
        variant = tok
        repl = [
            ("Ae", "Ä"),
            ("Oe", "Ö"),
            ("Ue", "Ü"),
            ("ae", "ä"),
            ("oe", "ö"),
            ("ue", "ü"),
        ]
        for src, dst in repl:
            variant = variant.replace(src, dst)
        if variant != tok and re.search(r"[ÄÖÜäöü]", variant):
            return variant
        return None

    expanded: list[str] = []
    seen: set[str] = set()
    for tok in keep:
        cand = _umlaut_variant(tok) or tok
        key = cand.casefold()
        if key in seen:
            continue
        seen.add(key)
        expanded.append(cand)

    if not keep:
        return " ".join((text or "").strip().split())[:120]
    return " ".join((expanded or keep)[:max_terms])[:120]


def _search_query_for_tool(tool_name: str, query: str, hints: dict[str, str]) -> str:
    base = _base_question_text(query)
    cand = ""
    if tool_name == "search_ogh_rechtssaetze":
        cand = hints.get("rs_query") or hints.get("hot_query") or base or "Rechtsschutzversicherung Verwaltungsverfahren"
        return _compact_search_query(cand, max_terms=8)
    if tool_name == "hot_rs_search":
        cand = hints.get("hot_query") or hints.get("rs_query") or base or "Rechtsschutzversicherung Deckung"
        return _compact_search_query(cand, max_terms=8)
    return _compact_search_query(base, max_terms=8)


def _keyword_hint(query: str, hints: dict[str, str]) -> str:
    if hints.get("kommentar_keyword"):
        return _compact_search_query(hints["kommentar_keyword"], max_terms=8)
    for q in (hints.get("rs_query"), hints.get("hot_query"), _base_question_text(query)):
        if q and len(q.strip()) >= 5:
            return _compact_search_query(q.strip(), max_terms=8)
    return "Rechtsschutzversicherung"


def _paragraph_hint(query: str, hints: dict[str, str]) -> str | None:
    p = (hints.get("kommentar_paragraph") or "").strip()
    if p:
        return p[:60]
    norms = extract_norm_citations(query)
    if norms:
        return norms[0][:60]
    return None


def _cluster_hint(query: str, hints: dict[str, str]) -> str | None:
    txt = " ".join([query or "", hints.get("hot_query") or "", hints.get("rs_query") or ""]).lower()
    if any(k in txt for k in ["agb", "864a", "879 abs 3", "geltungskontrolle", "inhaltskontrolle"]):
        return "AGB_GELTUNGSKONTROLLE"
    return None


# Map domain keywords → zivil-pruefung topic IDs for build_grounding_context / detect_clusters
_TOPIC_PATTERNS: list[tuple[str, list[str]]] = [
    ("schadenersatz", ["schadenersatz", "schmerzensgeld", "§ 1295", "§ 1296", "§ 1299", "§ 1301", "§ 1304", "§ 1310", "§ 1313", "§ 1315", "ekhg", "phg", "produkthaftung", "kausalität", "rechtswidrigkeit", "verschulden"]),
    ("bereicherungsrecht", ["bereicherung", "condictio", "§ 1431", "§ 1432", "§ 1435", "§ 1437", "§ 1041", "§ 1039", "verwendungsanspruch", "leistungskondiktion"]),
    ("erbrecht", ["erbrecht", "testament", "pflichtteil", "vermächtnis", "erbfolge", "§ 531", "§ 552", "§ 726", "§ 727", "§ 764", "§ 774", "§ 778"]),
    ("laesio_enormis", ["laesio", "§ 934", "§ 935", "§ 351 ugb", "verkürzung über die hälfte", "wucher"]),
    ("allgemeiner_teil", ["stellvertretung", "vollmacht", "rechtsgeschäft", "willenserklärung", "irrtum", "anfechtung", "§ 863", "§ 870", "§ 871", "§ 872", "§ 874", "§ 875", "§ 876", "§ 879", "sittenwidrigkeit", "verjährung", "§ 1478", "§ 1480", "§ 1489"]),
    ("vertraege", ["vertrag", "gewährleistung", "§ 922", "§ 923", "§ 924", "§ 932", "verzug", "rücktritt", "§ 918", "§ 919", "§ 920", "§ 921", "leistungsstörung", "unmöglichkeit"]),
    ("sachenrecht", ["eigentum", "besitz", "grundbuch", "pfandrecht", "hypothek", "servitut", "ersitzung", "§ 309", "§ 312", "§ 326", "§ 328", "§ 366", "§ 367", "§ 431", "§ 451"]),
    ("familienrecht", ["ehe", "scheidung", "unterhalt", "obsorge", "kindeswohl", "ehegattenunterhalt", "§ 55 eheg", "§ 49 eheg", "§ 90", "§ 94", "§ 97"]),
    ("schuldrecht_bt", ["mietrecht", "werkvertrag", "auftrag", "bürgschaft", "leihe", "darlehen", "§ 1090", "§ 1096", "§ 1151", "§ 1165", "§ 1346", "§ 1353", "kreditvertrag", "vkrg"]),
    ("internationale_bezuege", ["ipr", "rom i", "rom ii", "brüssel", "cisg", "un-kaufrecht", "zuständigkeit", "haag", "§ 1 iprg"]),
    ("mehrpersonal", ["gesamtschuld", "solidarschuld", "regress", "zession", "abtretung", "§ 1358", "§ 1359", "§ 1392", "§ 1393", "§ 1394", "§ 1396", "schuldbeitritt", "garantie"]),
    ("pflichtteilsrecht", ["pflichtteil", "noterbe", "enterbung", "§ 762", "§ 763", "§ 764", "§ 765", "§ 766", "§ 780", "§ 781", "§ 782", "anrechnung"]),
]


def _topic_hint(query: str, hints: dict[str, str]) -> str | None:
    """Detect the most likely zivil-pruefung topic for a query."""
    txt = " ".join([query or "", hints.get("hot_query") or "", hints.get("rs_query") or ""]).lower()
    best_topic: str | None = None
    best_score = 0
    for topic, keywords in _TOPIC_PATTERNS:
        score = sum(1 for kw in keywords if kw in txt)
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic if best_score >= 1 else None


def build_tool_args(tool_name: str, query: str, probe_limit: int) -> dict[str, Any] | None:
    limit = max(1, min(int(probe_limit), 10))
    hints = _extract_retrieval_hints(query)
    if tool_name == "search_ogh_rechtssaetze":
        return {"query": _search_query_for_tool(tool_name, query, hints), "limit": limit}
    if tool_name == "search_ogh_entscheidungen":
        return {"query": _search_query_for_tool("search_ogh_rechtssaetze", query, hints), "limit": limit}
    if tool_name == "get_rechtssatz":
        in_query = extract_rs_numbers(query)
        if in_query:
            return {"rs_number": in_query[0]}
        return None
    if tool_name == "hot_rs_search":
        return {"query": _search_query_for_tool(tool_name, query, hints), "limit": limit}
    if tool_name == "hot_cluster_context":
        cid = _cluster_hint(query, hints)
        if cid:
            return {"cluster_id": cid, "rs_limit": min(limit, 5), "te_limit_per_rs": 2}
        return None
    if tool_name == "search_kommentar_paragraph":
        par = _paragraph_hint(query, hints)
        if not par:
            return None
        law = _law_hint_from_text(par) or _law_hint_from_text(query)
        out: dict[str, Any] = {"paragraph": par, "limit": limit}
        if law:
            out["law"] = law
        return out
    if tool_name == "search_kommentar_keyword":
        kw = _keyword_hint(query, hints)
        law = _law_hint_from_text(kw) or _law_hint_from_text(query)
        out: dict[str, Any] = {"keyword": kw, "limit": limit}
        if law:
            out["law"] = law
        return out
    if tool_name == "search_by_paragraph":
        par = _paragraph_hint(query, hints)
        if par:
            return {"paragraph": par, "limit": limit}
        return None
    if tool_name == "search_by_schlagwort":
        kw = _keyword_hint(query, hints)
        return {"schlagwort": kw, "limit": limit}
    if tool_name == "hot_rs_lookup":
        in_query = extract_rs_numbers(query)
        if in_query:
            return {"rs_number": in_query[0], "te_limit": min(limit, 5)}
        return None
    if tool_name == "hot_index_stats":
        return {}
    if tool_name == "build_grounding_context":
        topic = _topic_hint(query, hints)
        if topic:
            return {"topic": topic, "query": _compact_search_query(query, max_terms=12), "max_clusters": 1, "max_tokens": 500}
        return None
    if tool_name == "detect_clusters":
        topic = _topic_hint(query, hints)
        if topic:
            return {"topic": topic, "query": _compact_search_query(query, max_terms=12)}
        return None
    if tool_name == "ask_gemini_zivilrecht":
        return {"question": _compact_search_query(query, max_terms=15)}
    return None


def sanitize_tool_args(tool_name: str, raw_args: dict[str, Any], query: str, probe_limit: int) -> dict[str, Any] | None:
    args = dict(raw_args or {})
    fallback = build_tool_args(tool_name, query=query, probe_limit=probe_limit)
    pol = tool_policy(tool_name)
    guardrails = MCP_RUNTIME.get("guardrails") if isinstance(MCP_RUNTIME, dict) else {}
    max_limit_pol = int(pol.get("max_limit") or 50)
    max_limit_gr = int((guardrails or {}).get("max_result_rows") or 50)
    max_limit = max(1, min(max_limit_pol, max_limit_gr, 50))
    max_query_pol = int(pol.get("max_query_length") or 500)
    max_query_gr = int((guardrails or {}).get("max_query_length") or 500)
    max_query_length = max(80, min(max_query_pol, max_query_gr, 500))
    limit = max(1, min(int(args.get("limit", probe_limit) or probe_limit), max_limit))

    if tool_name in {"search_ogh_rechtssaetze", "search_ogh_entscheidungen", "hot_rs_search"}:
        q = str(args.get("query") or "").strip()
        # Use model-provided query when valid; fallback only when empty/broken.
        if (not q) or (len(q) > max_query_length) or ("\n" in q) or q.lower().startswith("analysiere one-shot"):
            if fallback and str(fallback.get("query") or "").strip():
                q = str(fallback.get("query") or "").strip()
            else:
                return None
        q_compact = _compact_search_query(q, max_terms=8)
        return {"query": (q_compact or q)[:max_query_length], "limit": limit}

    if tool_name == "get_rechtssatz":
        rs = _normalize_rs_number(str(args.get("rs_number") or ""))
        if not rs:
            if fallback and fallback.get("rs_number"):
                rs = str(fallback["rs_number"])
            else:
                return None
        return {"rs_number": rs}

    if tool_name == "hot_cluster_context":
        cid = str(args.get("cluster_id") or "").strip()
        if (not cid) or (" " in cid) or (len(cid) > 80):
            if not fallback:
                return None
            cid = str(fallback.get("cluster_id") or "").strip()
        if not cid:
            return None
        rs_limit = max(1, min(int(args.get("rs_limit", 5) or 5), 10))
        te_limit = max(1, min(int(args.get("te_limit_per_rs", 2) or 2), 5))
        return {"cluster_id": cid, "rs_limit": rs_limit, "te_limit_per_rs": te_limit}

    if tool_name == "search_kommentar_paragraph":
        par = str(args.get("paragraph") or "").strip()
        if (not par) or (len(par) > min(120, max_query_length)) or ("\n" in par):
            if not fallback:
                return None
            par = str(fallback.get("paragraph") or "").strip()
        if not par:
            return None
        law = str(args.get("law") or "").strip().upper()
        if not law and fallback:
            law = str(fallback.get("law") or "").strip().upper()
        out: dict[str, Any] = {"paragraph": par, "limit": limit}
        if law in NORM_LAW_CODES_UP:
            out["law"] = law
        return out

    if tool_name == "search_kommentar_keyword":
        kw = str(args.get("keyword") or "").strip()
        if (not kw) or (len(kw) > max_query_length) or ("\n" in kw):
            if not fallback:
                return None
            kw = str(fallback.get("keyword") or "").strip()
        if not kw:
            return None
        kw = _compact_search_query(kw, max_terms=8)
        law = str(args.get("law") or "").strip().upper()
        if not law and fallback:
            law = str(fallback.get("law") or "").strip().upper()
        out: dict[str, Any] = {"keyword": kw[:max_query_length], "limit": limit}
        if law in NORM_LAW_CODES_UP:
            out["law"] = law
        return out

    if tool_name == "search_by_paragraph":
        par = str(args.get("paragraph") or "").strip()
        if (not par) or (len(par) > 120) or ("\n" in par):
            if not fallback:
                return None
            par = str(fallback.get("paragraph") or "").strip()
        if not par:
            return None
        return {"paragraph": par[:120], "limit": limit}

    if tool_name == "search_by_schlagwort":
        sw = str(args.get("schlagwort") or "").strip()
        if (not sw) or (len(sw) > 120) or ("\n" in sw):
            if not fallback:
                return None
            sw = str(fallback.get("schlagwort") or "").strip()
        if not sw:
            return None
        return {"schlagwort": sw[:120], "limit": limit}

    if tool_name == "hot_rs_lookup":
        rs = _normalize_rs_number(str(args.get("rs_number") or ""))
        if not rs:
            if fallback and fallback.get("rs_number"):
                rs = str(fallback["rs_number"])
            else:
                return None
        te_limit = max(1, min(int(args.get("te_limit", 5) or 5), 20))
        return {"rs_number": rs, "te_limit": te_limit}

    if tool_name == "hot_index_stats":
        return {}

    if tool_name == "build_grounding_context":
        topic = str(args.get("topic") or "").strip().lower()
        q = str(args.get("query") or "").strip()
        if not topic:
            if fallback and fallback.get("topic"):
                topic = str(fallback["topic"]).strip().lower()
            else:
                return None
        if not q:
            q = _compact_search_query(query, max_terms=12)
        max_cl = max(1, min(int(args.get("max_clusters", 1) or 1), 3))
        max_tk = max(100, min(int(args.get("max_tokens", 500) or 500), 1000))
        return {"topic": topic, "query": q[:300], "max_clusters": max_cl, "max_tokens": max_tk}

    if tool_name == "detect_clusters":
        topic = str(args.get("topic") or "").strip().lower()
        q = str(args.get("query") or "").strip()
        if not topic:
            if fallback and fallback.get("topic"):
                topic = str(fallback["topic"]).strip().lower()
            else:
                return None
        if not q:
            q = _compact_search_query(query, max_terms=12)
        return {"topic": topic, "query": q[:300]}

    if tool_name == "ask_gemini_zivilrecht":
        question = str(args.get("question") or "").strip()
        if not question:
            question = _compact_search_query(query, max_terms=15)
        if not question:
            return None
        ctx = str(args.get("context") or "").strip()
        out: dict[str, Any] = {"question": question[:500]}
        if ctx:
            out["context"] = ctx[:500]
        return out

    return fallback


def run_subagent_dry(
    stream: dict[str, Any],
    query: str,
    mcp_mode: str,
    mcp_base: str,
    remote_ssh: str,
    remote_mcp_container: str,
    probe_limit: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    traces: list[dict[str, Any]] = []
    stream_tools = filter_tools_for_role(list(stream.get("tools") or []), "worker")
    for tool in stream_tools:
        args = sanitize_tool_args(tool, raw_args=build_tool_args(tool, query=query, probe_limit=probe_limit) or {}, query=query, probe_limit=probe_limit)
        if not args:
            traces.append(
                {
                    "tool": tool,
                    "args": None,
                    "ok": False,
                    "status": None,
                    "latency_ms": None,
                    "error": "skipped_no_suitable_args",
                    "payload_preview": "",
                }
            )
            continue
        call = call_mcp_tool(
            tool=tool,
            args=args,
            mcp_mode=mcp_mode,
            mcp_base=mcp_base,
            remote_ssh=remote_ssh,
            remote_mcp_container=remote_mcp_container,
        )
        payload = parse_tool_payload(call.get("body"))
        traces.append(
            {
                "tool": tool,
                "args": args,
                "ok": call.get("ok"),
                "status": call.get("status"),
                "latency_ms": call.get("latency_ms"),
                "error": call.get("error"),
                "payload_preview": (json.dumps(payload, ensure_ascii=False)[:2000] if payload is not None else ""),
            }
        )
    total_ms = round((time.perf_counter() - started) * 1000.0, 2)
    ok_calls = sum(1 for x in traces if x.get("ok"))
    return {
        "name": stream["name"],
        "goal": stream["goal"],
        "mode": "dry",
        "tools": stream_tools,
        "tool_calls": traces,
        "tool_calls_total": len(traces),
        "tool_calls_ok": ok_calls,
        "tool_calls_ok_rate": round(ok_calls / len(traces), 3) if traces else None,
        "answer": f"Dry-run stream {stream['name']} completed with {ok_calls}/{len(traces)} successful MCP calls.",
        "e2e_ms": total_ms,
    }


def run_subagent_llm(
    stream: dict[str, Any],
    query: str,
    worker_model: str,
    mcp_mode: str,
    mcp_base: str,
    remote_ssh: str,
    remote_mcp_container: str,
    max_steps: int,
    pre_search_evidence: str = "",
    all_stream_names: list[str] | None = None,
    classification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    stream_tools = filter_tools_for_role(list(stream.get("tools") or []), "worker")
    enabled_tools = [TOOL_SPECS[t] for t in stream_tools if t in TOOL_SPECS]
    allowed = set(stream_tools)
    worker_ctx = role_skill_context("worker")
    # Phase-aware worker system prompt
    sys_prompt = (
        "You are a specialist legal subagent for Austrian law. "
        "Use ONLY allowed tools. Gather high-signal evidence with explicit RS/GZ references. "
        "Do not invent case facts.\n\n"
        "WORK IN PHASES:\n"
        "PHASE 1 - TARGETED SEARCH (2-3 calls):\n"
        "  - For EVERY § in the classification: call search_by_paragraph\n"
        "  - search_by_schlagwort for OGH taxonomy keywords\n"
        "  - search_ogh_rechtssaetze for broader keyword search\n\n"
        "PHASE 2 - DEEPEN (2-3 calls):\n"
        "  - get_rechtssatz or hot_rs_lookup for promising RS numbers found in Phase 1\n"
        "  - build_grounding_context for cluster-level minimal ruleset with RS citations\n"
        "  - If distinct legal regimes exist (e.g. Kunstfehler vs Aufklärungsfehler, "
        "    Wandlung vs Preisminderung, §25c vs §879 ABGB): search each regime separately\n"
        "  - Note Beweislast for each claim found\n"
        "  - If 0 results: rewrite query with different terms, synonyms, or try different tool\n\n"
        "PHASE 3 - SUMMARIZE (final call):\n"
        "  - Compile findings with RS/GZ references\n"
        "  - Note which party bears Beweislast for each issue\n\n"
        "CRITICAL: After Phase 1, do NOT stop. ALWAYS deepen RS numbers found. "
        "If a tool returns 0 results, try broader terms or a different tool. "
        "Never give up after one empty result.\n\n"
        "DOMAIN-SPECIFIC RULES:\n"
        "- Arzthaftung: Search BOTH tracks separately: (1) Behandlungsfehler/Kunstfehler "
        "(§1299 Sorgfaltsmaßstab, §1298 Beweislastumkehr) AND (2) Aufklärungsfehler "
        "(hypothetische Einwilligung, Risikoaufklärung). Always search deliktisch (§1295/§1325) "
        "AND vertraglich (§1299/§1313a).\n"
        "- Interzession/Bürgschaft: Search §25c KSchG AND §879 ABGB (Sittenwidrigkeit) "
        "as SEPARATE regimes. If Exekution mentioned, also search §35 EO (Oppositionsklage).\n"
        "- Gewährleistung: Search §§922/932 AND §870/§874 ABGB (Arglist/Irreführung) separately."
    )
    if worker_ctx:
        sys_prompt += "\n\n" + worker_ctx
    # Build user message with optional classification and pre-search
    usr_parts = ["Main question:\n" + query]
    if classification and classification.get("domain"):
        usr_parts.append(f"\nDomain: {classification['domain']}")
        sd = classification.get("subdomain")
        if sd:
            usr_parts.append(f"Sub-domain: {sd}")
        mandatory = classification.get("mandatory_paragraphs") or []
        pars = classification.get("paragraphs") or []
        if mandatory:
            usr_parts.append("MANDATORY paragraphs to search: " + ", ".join(mandatory[:6]))
        elif pars:
            usr_parts.append("Key paragraphs: " + ", ".join(pars[:4]))
    usr_parts.append("\nYour stream goal:\n" + stream["goal"])
    usr_parts.append("\nAllowed tools: " + ", ".join(stream_tools))
    # Cross-stream awareness: tell worker what other streams are covering
    if all_stream_names:
        others = [n for n in all_stream_names if n != stream.get("name")]
        if others:
            usr_parts.append(f"\nParallel streams covering other aspects: {', '.join(others)}. Focus on YOUR goal, avoid duplication.")
    if pre_search_evidence:
        usr_parts.append("\nPre-search evidence (CRITICAL starting context — integrate RS numbers into your searches, deepen the most relevant ones):\n" + pre_search_evidence[:5000])
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "\n".join(usr_parts)},
    ]
    tool_traces: list[dict[str, Any]] = []
    llm_calls: list[dict[str, Any]] = []
    final_answer = ""
    llm_error: str | None = None
    _zero_result_sigs: set[str] = set()  # track tool+args combos that returned 0 results

    for step in range(1, max_steps + 1):
        _step_ok = False
        for _retry in range(3):
            try:
                raw_resp, latency_ms = openrouter_chat(
                    model=worker_model,
                    messages=messages,
                    max_tokens=1600,
                    temperature=0.0,
                    tools=(enabled_tools if enabled_tools else None),
                    tool_choice="auto",
                    provider=_openrouter_provider_for_model(worker_model),
                    reasoning=_openrouter_reasoning_for_role(worker_model, "worker"),
                    models=_openrouter_model_fallbacks(worker_model),
                    title=f"legalchat-agentic-subagent-{stream['name']}",
                )
                _step_ok = True
                break
            except Exception as e:
                if _retry >= 2:
                    llm_error = str(e)
                    llm_calls.append(
                        {
                            "step": step,
                            "latency_ms": None,
                            "finish_reason": "error",
                            "tool_calls_count": 0,
                            "error": llm_error,
                        }
                    )
                else:
                    time.sleep(2.0 * (_retry + 1))
        if not _step_ok:
            break
        choice = ((raw_resp.get("choices") or [{}])[0] or {})
        msg = choice.get("message") or {}
        finish_reason = choice.get("finish_reason")
        text = message_text(msg)
        tool_calls = msg.get("tool_calls")
        llm_calls.append(
            {
                "step": step,
                "latency_ms": round(latency_ms, 2),
                "finish_reason": finish_reason,
                "tool_calls_count": len(tool_calls) if isinstance(tool_calls, list) else 0,
                "usage": _openrouter_usage_snapshot(raw_resp),
            }
        )
        if isinstance(tool_calls, list) and tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": text,
                    "tool_calls": tool_calls,
                }
            )
            for tc in tool_calls:
                tc_id = tc.get("id") or f"call_{step}_{len(tool_traces)+1}"
                fn = ((tc.get("function") or {}).get("name") or "").strip()
                raw_args = (tc.get("function") or {}).get("arguments") or "{}"
                try:
                    fn_args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                except Exception:
                    fn_args = {}
                if fn not in allowed:
                    payload = {"ok": False, "error": f"tool_not_allowed:{fn}"}
                    tool_traces.append(
                        {
                            "step": step,
                            "tool_call_id": tc_id,
                            "tool": fn,
                            "args": fn_args,
                            "ok": False,
                            "status": None,
                            "latency_ms": None,
                            "error": "tool_not_allowed",
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "name": fn,
                            "content": json.dumps(payload, ensure_ascii=False),
                        }
                    )
                    continue

                # Block duplicate queries that already returned 0 results
                _call_sig = f"{fn}:{json.dumps(fn_args, sort_keys=True, ensure_ascii=False)}"
                if _call_sig in _zero_result_sigs:
                    payload = {"ok": False, "error": "duplicate_zero_result_query", "hint": "This exact query already returned 0 results. Use different keywords or a different tool."}
                    tool_traces.append({"step": step, "tool_call_id": tc_id, "tool": fn, "args": fn_args, "ok": False, "status": None, "latency_ms": None, "error": "duplicate_zero_result"})
                    messages.append({"role": "tool", "tool_call_id": tc_id, "name": fn, "content": json.dumps(payload, ensure_ascii=False)})
                    messages.append({"role": "system", "content": f"BLOCKED: You already searched {fn} with identical args and got 0 results. You MUST use different keywords (shorter, 2-4 words) or switch to a different tool like search_by_paragraph or search_by_schlagwort."})
                    continue

                safe_args = sanitize_tool_args(
                    fn,
                    raw_args=fn_args,
                    query=query,
                    probe_limit=5,
                )
                if not safe_args:
                    payload = {"ok": False, "error": f"tool_args_unsuitable:{fn}"}
                    tool_traces.append(
                        {
                            "step": step,
                            "tool_call_id": tc_id,
                            "tool": fn,
                            "args": fn_args,
                            "ok": False,
                            "status": None,
                            "latency_ms": None,
                            "error": "tool_args_unsuitable",
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "name": fn,
                            "content": json.dumps(payload, ensure_ascii=False),
                        }
                    )
                    continue

                call = call_mcp_tool(
                    tool=fn,
                    args=safe_args,
                    mcp_mode=mcp_mode,
                    mcp_base=mcp_base,
                    remote_ssh=remote_ssh,
                    remote_mcp_container=remote_mcp_container,
                )
                payload = parse_tool_payload(call.get("body"))
                trace = {
                    "step": step,
                    "tool_call_id": tc_id,
                    "tool": fn,
                    "args": safe_args,
                    "ok": call.get("ok"),
                    "status": call.get("status"),
                    "latency_ms": call.get("latency_ms"),
                    "error": call.get("error"),
                    "payload_preview": (json.dumps(payload, ensure_ascii=False)[:2400 if fn in ("build_grounding_context", "hot_rs_lookup", "hot_cluster_context", "ask_gemini_zivilrecht") else 1600] if payload is not None else ""),
                }
                tool_traces.append(trace)
                tool_payload_for_llm = payload if payload is not None else {"ok": False, "error": call.get("error")}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": fn,
                        "content": json.dumps(tool_payload_for_llm, ensure_ascii=False),
                    }
                )
                # Phase 3c: Zero-result retry hint
                _is_empty = False
                if isinstance(payload, dict):
                    _is_empty = not payload.get("found") and not payload.get("results") and not payload.get("data")
                elif isinstance(payload, list):
                    _is_empty = len(payload) == 0
                if _is_empty and call.get("ok"):
                    _used_query = str(safe_args.get("query") or safe_args.get("keyword") or "")
                    _hint_parts = [
                        f"Tool {fn} returned 0 results for {json.dumps(safe_args, ensure_ascii=False)[:200]}.",
                        "IMPORTANT: You MUST change your query. Do NOT repeat the same search.",
                    ]
                    if len(_used_query) > 60:
                        _hint_parts.append(
                            f"Your query was too long ({len(_used_query)} chars). Use 2-4 keywords only, e.g. "
                            f"'Invaliditätspension Zumutbarkeit' instead of the full question text."
                        )
                    _hint_parts.append(
                        "Try: (1) shorter query with 2-4 German legal keywords, "
                        "(2) a different tool (search_by_paragraph, search_by_schlagwort), or "
                        "(3) synonyms/broader terms."
                    )
                    messages.append({"role": "system", "content": " ".join(_hint_parts)})
                    # Track this combo so duplicates are blocked
                    _zero_sig = f"{fn}:{json.dumps(safe_args, sort_keys=True, ensure_ascii=False)}"
                    _zero_result_sigs.add(_zero_sig)
            continue
        final_answer = text.strip()
        break

    # Phase 3d: Forced deep-dive — RS numbers found in traces but never looked up
    if tool_traces:
        _looked_up_rs: set[str] = set()
        _found_rs: set[str] = set()
        for tt in tool_traces:
            if tt.get("tool") in ("get_rechtssatz", "hot_rs_lookup"):
                rs_arg = (tt.get("args") or {}).get("rs_number", "")
                if rs_arg:
                    _looked_up_rs.add(rs_arg)
            prev = tt.get("payload_preview") or ""
            _found_rs.update(extract_rs_numbers(prev))
        _unlooked = sorted(_found_rs - _looked_up_rs, reverse=True)[:5]
        for rs in _unlooked:
            _deep_tool = "hot_rs_lookup" if "hot_rs_lookup" in allowed else ("get_rechtssatz" if "get_rechtssatz" in allowed else "")
            if not _deep_tool:
                break
            _deep_args = {"rs_number": rs, "te_limit": 5} if _deep_tool == "hot_rs_lookup" else {"rs_number": rs}
            _deep_call = call_mcp_tool(
                tool=_deep_tool, args=_deep_args,
                mcp_mode=mcp_mode, mcp_base=mcp_base,
                remote_ssh=remote_ssh, remote_mcp_container=remote_mcp_container,
            )
            _deep_payload = parse_tool_payload(_deep_call.get("body"))
            tool_traces.append({
                "step": "deep_dive",
                "tool_call_id": f"deep_{rs}",
                "tool": _deep_tool,
                "args": _deep_args,
                "ok": _deep_call.get("ok"),
                "status": _deep_call.get("status"),
                "latency_ms": _deep_call.get("latency_ms"),
                "error": _deep_call.get("error"),
                "payload_preview": (json.dumps(_deep_payload, ensure_ascii=False)[:2400] if _deep_payload is not None else ""),
            })

    if not final_answer and not llm_error:
        messages.append(
            {
                "role": "system",
                "content": "Stop tool usage and provide a final concise evidence summary now.",
            }
        )
        try:
            raw_resp, latency_ms = openrouter_chat(
                model=worker_model,
                messages=messages,
                max_tokens=700,
                temperature=0.0,
                tools=(enabled_tools if enabled_tools else None),
                tool_choice="none",
                provider=_openrouter_provider_for_model(worker_model),
                reasoning=_openrouter_reasoning_for_role(worker_model, "worker"),
                models=_openrouter_model_fallbacks(worker_model),
                title=f"legalchat-agentic-subagent-final-{stream['name']}",
            )
            msg = ((raw_resp.get("choices") or [{}])[0] or {}).get("message") or {}
            final_answer = message_text(msg).strip()
            llm_calls.append(
                {
                    "step": max_steps + 1,
                    "latency_ms": round(latency_ms, 2),
                    "finish_reason": "forced_final",
                    "tool_calls_count": 0,
                    "usage": _openrouter_usage_snapshot(raw_resp),
                }
            )
        except Exception as e:
            llm_error = str(e)
            llm_calls.append(
                {
                    "step": max_steps + 1,
                    "latency_ms": None,
                    "finish_reason": "error_forced_final",
                    "tool_calls_count": 0,
                    "error": llm_error,
                }
            )
    if not final_answer:
        fallback = fallback_answer_from_tool_traces(stream["name"], tool_traces)
        if llm_error:
            fallback += f"\n- llm_error: {llm_error}"
        final_answer = fallback

    # Guardrail: if the model never called tools, force deterministic probe calls
    # using ALL classifier paragraphs and keywords so no §§ are missed.
    if not tool_traces and stream_tools:
        _probe_calls: list[tuple[str, dict[str, Any]]] = []
        cls_pars = list(dict.fromkeys((classification or {}).get("paragraphs") or []))  # dedupe, preserve order
        cls_kws = list(dict.fromkeys((classification or {}).get("keywords") or []))
        # Search every classifier paragraph
        if "search_by_paragraph" in allowed:
            for par in cls_pars[:4]:
                _probe_calls.append(("search_by_paragraph", {"paragraph": str(par)[:120], "limit": 5}))
        # Search every classifier keyword as schlagwort
        if "search_by_schlagwort" in allowed:
            for kw in cls_kws[:3]:
                _probe_calls.append(("search_by_schlagwort", {"schlagwort": str(kw)[:120], "limit": 5}))
        # Fallback: one broad RS search
        if "search_ogh_rechtssaetze" in allowed and not _probe_calls:
            compact_q = _compact_search_query(_base_question_text(query), max_terms=6)
            _probe_calls.append(("search_ogh_rechtssaetze", {"query": compact_q, "limit": 5}))
        # If no classifier data, fall back to old behavior
        if not _probe_calls:
            for tool in list(stream_tools)[:3]:
                args = build_tool_args(tool, query=query, probe_limit=5)
                args = sanitize_tool_args(tool, raw_args=args or {}, query=query, probe_limit=5)
                if args:
                    _probe_calls.append((tool, args))
        for tool, args in _probe_calls[:8]:
            call = call_mcp_tool(
                tool=tool,
                args=args,
                mcp_mode=mcp_mode,
                mcp_base=mcp_base,
                remote_ssh=remote_ssh,
                remote_mcp_container=remote_mcp_container,
            )
            payload = parse_tool_payload(call.get("body"))
            tool_traces.append(
                {
                    "step": "forced_probe",
                    "tool_call_id": f"forced_{tool}_{len(tool_traces)}",
                    "tool": tool,
                    "args": args,
                    "ok": call.get("ok"),
                    "status": call.get("status"),
                    "latency_ms": call.get("latency_ms"),
                    "error": call.get("error"),
                    "payload_preview": (json.dumps(payload, ensure_ascii=False)[:2400 if tool in ("build_grounding_context", "hot_rs_lookup", "hot_cluster_context", "ask_gemini_zivilrecht") else 1600] if payload is not None else ""),
                }
            )

    ok_calls = sum(1 for x in tool_traces if x.get("ok"))
    total_ms = round((time.perf_counter() - started) * 1000.0, 2)
    return {
        "name": stream["name"],
        "goal": stream["goal"],
        "mode": "llm",
        "tools": stream_tools,
        "llm_model": worker_model,
        "llm_calls": llm_calls,
        "tool_calls": tool_traces,
        "tool_calls_total": len(tool_traces),
        "tool_calls_ok": ok_calls,
        "tool_calls_ok_rate": round(ok_calls / len(tool_traces), 3) if tool_traces else None,
        "llm_error": llm_error,
        "answer": final_answer,
        "answer_chars": len(final_answer),
        "e2e_ms": total_ms,
    }


def _build_synthesis_evidence_chunks(
    subagent_results: list[dict[str, Any]],
    postgres_only: bool,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for rec in subagent_results:
        item: dict[str, Any] = {
            "stream": rec.get("name"),
            "goal": rec.get("goal"),
            "tool_calls_ok_rate": rec.get("tool_calls_ok_rate"),
        }
        if not postgres_only:
            item["answer"] = rec.get("answer")
            chunks.append(item)
            continue
        tool_evidence: list[dict[str, Any]] = []
        for tc in rec.get("tool_calls") or []:
            if not isinstance(tc, dict) or not tc.get("ok"):
                continue
            prev = tc.get("payload_preview")
            if not isinstance(prev, str) or not prev.strip():
                continue
            _hv = tc.get("tool") in ("build_grounding_context", "hot_rs_lookup", "hot_cluster_context", "ask_gemini_zivilrecht")
            tool_evidence.append(
                {
                    "tool": tc.get("tool"),
                    "payload_preview": prev[:3000 if _hv else 1800],
                }
            )
            if len(tool_evidence) >= 20:
                break
        item["tool_evidence"] = tool_evidence
        item["tool_evidence_count"] = len(tool_evidence)
        chunks.append(item)
    return chunks


def synthesize_answer(
    query: str,
    synth_model: str,
    plan: dict[str, Any],
    subagent_results: list[dict[str, Any]],
    dry_run: bool,
    postgres_only: bool,
) -> tuple[str, dict[str, Any] | None]:
    if dry_run:
        lines = []
        lines.append("Dry-run synthesis")
        lines.append("")
        lines.append(f"Question: {query}")
        lines.append("")
        for rec in subagent_results:
            lines.append(f"- [{rec.get('name')}] {rec.get('answer')}")
        return "\n".join(lines), None

    evidence_chunks = _build_synthesis_evidence_chunks(
        subagent_results=subagent_results,
        postgres_only=postgres_only,
    )
    grounded = collect_citation_evidence(subagent_results, include_stream_answers=False)
    synth_ctx = role_skill_context("synth")
    structured_format = (
        "\n\nStructure your answer in these sections:\n"
        "1. KERNFRAGEN — 2-3 zentrale Rechtsfragen, jeweils mit kurzer Einordnung\n"
        "2. RECHTSGRUNDLAGEN — konkrete §§ mit Gesetzen. Bei mehreren Anspruchsgrundlagen: Stufenbau/Doppelgleisigkeit darstellen\n"
        "3. RELEVANTE JUDIKATUR — RS-Nummern mit 1-Satz-Zusammenfassung und Relevanz für den Fall\n"
        "4. SUBSUMTION — Anwendung auf den konkreten Fall, GETRENNT nach Anspruchsgrundlagen\n"
        "5. BEWEISLASTVERTEILUNG — Wer muss was beweisen? Welche Beweise liegen vor/fehlen?\n"
        "6. PROZESSSTRATEGIE — Haupt- und Eventualbegehren, priorisiert nach Erfolgsaussicht\n"
        "7. RISIKEN / GEGENARGUMENTE — mind. 4 mit konkreten Repliken/Entkräftungen (RS-gestützt)\n"
        "8. ERFOLGSAUSSICHTEN — pro Anspruchsgrundlage mit Prozent-Einschätzung\n\n"
        "WICHTIG:\n"
        "- Bei mehreren Anspruchsgrundlagen: IMMER Haupt- und Eventualbegehren ordnen\n"
        "- Konkurrierende Ansprüche (zB Wandlung UND Preisminderung) als Stufen darstellen\n"
        "- Beweislast EXPLIZIT für jede strittige Tatsache angeben\n"
        "- Mind. 4 Risiken, jedes mit RS-Nummer und konkreter Replik. KEINE Füll-Risiken ohne Fallbezug\n"
        "- Arzthaftung: IMMER Doppelgleisigkeit prüfen (Delikt §1295/§1325 + Vertrag §1299/§1313a), "
        "Behandlungsfehler UND Aufklärungsfehler getrennt subsumieren\n"
        "- Interzession: IMMER §25c KSchG + §879 ABGB als getrennte Anspruchsgrundlagen prüfen, "
        "bei Exekution auch §35 EO (Oppositionsklage) berücksichtigen"
    )
    if postgres_only:
        sys_prompt = (
            "You are the final legal synthesizer for Austrian law. "
            "Use ONLY provided tool evidence from PostgreSQL-backed MCP calls. "
            "Do not use model memory or external legal knowledge for RS/TE. "
            "Do not invent citations. Use only citations in allowed citation lists. "
            "Do not cite RW identifiers. "
            "Do not invent or enrich case facts beyond the provided evidence. "
            "If evidence is insufficient, state this explicitly."
            + structured_format
        )
    else:
        sys_prompt = (
            "You are the final legal synthesizer for Austrian law. "
            "Build one coherent answer grounded in stream evidence. "
            "Use explicit references (RS numbers, paragraph markers) when present. "
            "Do not invent citations. Use only citations from allowed lists. "
            "Prefer Austrian legal framing."
            + structured_format
        )
    if synth_ctx:
        sys_prompt += "\n\n" + synth_ctx
    usr_prompt = (
        "Question:\n"
        + query
        + "\n\nPlan focus:\n"
        + str(plan.get("synthesis_focus") or "")
        + "\n\nEvidence (JSON):\n"
        + json.dumps(evidence_chunks, ensure_ascii=False)
        + "\n\nAllowed citations (JSON):\n"
        + json.dumps(
            {
                "allowed_rs": grounded.get("rs", [])[:120],
                "allowed_ogh_te": grounded.get("te_ogh", [])[:120],
                "allowed_norms": grounded.get("norms", [])[:160],
            },
            ensure_ascii=False,
        )
    )
    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": usr_prompt}]
    try:
        raw_resp, latency_ms = openrouter_chat(
            model=synth_model,
            messages=messages,
            max_tokens=4500,
            temperature=0.0,
            tools=None,
            tool_choice=None,
            provider=_openrouter_provider_for_model(synth_model),
            reasoning=_openrouter_reasoning_for_role(synth_model, "synth"),
            models=_openrouter_model_fallbacks(synth_model),
            title="legalchat-agentic-synthesis",
        )
        msg = ((raw_resp.get("choices") or [{}])[0] or {}).get("message") or {}
        answer = message_text(msg).strip()
        return answer, {
            "latency_ms": round(latency_ms, 2),
            "model": synth_model,
            "answer_chars": len(answer),
            "usage": _openrouter_usage_snapshot(raw_resp),
        }
    except Exception as e:
        if postgres_only:
            grounded = collect_citation_evidence(subagent_results, include_stream_answers=False)
            rs_list = list(grounded.get("rs") or [])[:5]
            te_list = list(grounded.get("te_ogh") or [])[:5]
            norm_list = list(grounded.get("norms") or [])[:5]
            lines = []
            lines.append("PostgreSQL-only Ergebnis (deterministisch aus Tool-Evidenz).")
            lines.append("")
            lines.append(f"Frage: {query}")
            lines.append("")
            if rs_list or te_list or norm_list:
                lines.append("Verfügbare Fundstellen aus PostgreSQL-Evidenz:")
                for rs in rs_list:
                    lines.append(f"- {rs}")
                for gz in te_list:
                    lines.append(f"- {gz}")
                for norm in norm_list:
                    lines.append(f"- {norm}")
            else:
                lines.append("Nicht genügend PostgreSQL-Evidenz für belastbare RS/TE-Aussagen.")
            answer = "\n".join(lines)
            return answer, {"latency_ms": None, "model": synth_model, "answer_chars": len(answer), "error": str(e), "deterministic_postgres_only": True}
        lines = ["Fallback synthesis due to model error.", "", f"Error: {e}", "", f"Question: {query}", ""]
        for rec in subagent_results:
            lines.append(f"- [{rec.get('name')}] {rec.get('answer')}")
        answer = "\n".join(lines)
        return answer, {"latency_ms": None, "model": synth_model, "answer_chars": len(answer), "error": str(e)}


def collect_citation_evidence(subagent_results: list[dict[str, Any]], include_stream_answers: bool = False) -> dict[str, Any]:
    rs: set[str] = set()
    te: set[str] = set()
    norms: set[str] = set()
    for rec in subagent_results:
        texts: list[str] = []
        ans = rec.get("answer")
        if include_stream_answers and isinstance(ans, str):
            texts.append(ans)
        for tc in rec.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            prev = tc.get("payload_preview")
            if isinstance(prev, str) and prev.strip():
                texts.append(prev)
        for txt in texts:
            rs.update(extract_rs_numbers(txt))
            te.update(extract_ogh_te_citations(txt))
            norms.update(extract_norm_citations(txt))
    return {
        "rs": sorted(rs),
        "te_ogh": sorted(te),
        "norms": sorted(norms),
        "stats": {"rs_count": len(rs), "te_ogh_count": len(te), "norm_count": len(norms)},
    }


def validate_rs_citations_via_mcp(
    rs_numbers: list[str],
    mcp_mode: str,
    mcp_base: str,
    remote_ssh: str,
    remote_mcp_container: str,
) -> dict[str, Any]:
    uniq = sorted(set(rs_numbers))[:50]
    if not uniq:
        return {"cited": 0, "checked": 0, "valid": 0, "invalid": [], "sample_valid": []}
    valid: list[str] = []
    invalid: list[str] = []
    for rs in uniq:
        call = call_mcp_tool(
            tool="get_rechtssatz",
            args={"rs_number": rs},
            mcp_mode=mcp_mode,
            mcp_base=mcp_base,
            remote_ssh=remote_ssh,
            remote_mcp_container=remote_mcp_container,
            timeout=20.0,
        )
        payload = parse_tool_payload(call.get("body") if isinstance(call, dict) else None)
        found = bool(payload.get("found")) if isinstance(payload, dict) else False
        if call.get("ok") and found:
            valid.append(rs)
        else:
            invalid.append(rs)
    return {"cited": len(uniq), "checked": len(uniq), "valid": len(valid), "invalid": invalid, "sample_valid": valid[:10]}


def _repair_answer_citations(
    answer: str,
    repair_model: str,
    valid_rs: list[str],
    grounded_te: list[str],
    grounded_norms: list[str],
    require_judicature: bool,
    evidence_snippets: list[str] | None = None,
    query_context_excerpt: str = "",
) -> tuple[str, dict[str, Any]]:
    repair_ctx = role_skill_context("citation_repair")
    sys_prompt = (
        "You are a legal citation repair assistant. "
        "Rewrite the answer conservatively. Keep legal reasoning, but remove or correct unsupported citations. "
        "Only keep RS/OGH-TE/norm citations from the allowed lists."
    )
    if repair_ctx:
        sys_prompt += "\n\n" + repair_ctx
    payload = {
        "allowed_rs": valid_rs[:120],
        "allowed_ogh_te": grounded_te[:120],
        "allowed_norms": grounded_norms[:120],
        "require_judicature": require_judicature,
        "query_context_excerpt": (query_context_excerpt or "")[:2500],
        "evidence_snippets": list(evidence_snippets or [])[:16],
        "answer": answer,
        "rules": [
            "Do not invent citations.",
            "If no valid citation exists for a statement, keep statement but remove explicit citation.",
            "Preserve structure and practical recommendations.",
            "If require_judicature is true and allowed_rs/allowed_ogh_te are available, include at least one concrete RS or OGH-TE citation.",
            "Never output RS-like identifiers unless they are in allowed_rs.",
            "Remove any paragraph/article norm citation that is not in allowed_norms.",
            "Remove factual details that are not explicitly supported by query_context_excerpt or evidence_snippets.",
            "Do not add or keep specific diagnoses, timelines, or party/event details unless explicitly present in evidence_snippets.",
            "Do not mark allowed RS/OGH-TE citations as irrelevant unless evidence_snippets explicitly justify that conclusion.",
            "If uncertain, keep neutral wording and omit unsupported specifics.",
        ],
    }
    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
    try:
        resp, ms = openrouter_chat(
            model=repair_model,
            messages=messages,
            max_tokens=4500,
            temperature=0.0,
            tools=None,
            tool_choice=None,
            provider=_openrouter_provider_for_model(repair_model),
            reasoning=_openrouter_reasoning_for_role(repair_model, "repair"),
            models=_openrouter_model_fallbacks(repair_model),
            title="legalchat-agentic-citation-repair",
        )
        msg = ((resp.get("choices") or [{}])[0] or {}).get("message") or {}
        repaired = message_text(msg).strip()
        return repaired or answer, {
            "latency_ms": round(ms, 2),
            "model": repair_model,
            "error": None,
            "usage": _openrouter_usage_snapshot(resp),
        }
    except Exception as e:
        return answer, {"latency_ms": None, "model": repair_model, "error": str(e)}


def _strip_disallowed_norm_citations(answer: str, disallowed_norms: list[str]) -> str:
    txt = answer or ""
    norms = [x for x in (disallowed_norms or []) if isinstance(x, str) and x.strip()]
    if not txt or not norms:
        return txt
    for norm in sorted(set(norms), key=len, reverse=True):
        n = re.escape(norm.strip())
        n = n.replace(r"Art\ ", r"Art\.?\s+")
        n = n.replace(r"Abs\ ", r"Abs\.?\s+")
        n = n.replace(r"\ ", r"\s+")
        # Remove standalone norm references and common bracketed forms.
        txt = re.sub(rf"[\(\[]?\s*{n}\s*[\)\]]?", "", txt)
    txt = re.sub(r"\(\s*\)", "", txt)
    txt = re.sub(r"\[\s*\]", "", txt)
    # Remove malformed leftovers created by partial norm stripping, e.g. "§ 1480, /KSchG".
    txt = re.sub(r"§\s*\d+[a-zA-Z]?\s*,\s*/\s*[A-Za-zÄÖÜäöü]{2,15}", "", txt)
    txt = re.sub(r",\s*,", ", ", txt)
    txt = re.sub(r"\s+([,.;:])", r"\1", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt.strip()


def _strip_disallowed_judicature_citations(
    answer: str,
    disallowed_rs: list[str],
    disallowed_te: list[str],
) -> str:
    txt = answer or ""
    rs_list = [x for x in (disallowed_rs or []) if isinstance(x, str) and x.strip()]
    te_list = [x for x in (disallowed_te or []) if isinstance(x, str) and x.strip()]
    if not txt or (not rs_list and not te_list):
        return txt
    for rs in sorted(set(rs_list), key=len, reverse=True):
        r = re.escape(rs.strip())
        r = r.replace(r"\ ", r"\s*")
        txt = re.sub(rf"[\(\[]?\s*{r}\s*[\)\]]?", "", txt)
    for te in sorted(set(te_list), key=len, reverse=True):
        te_norm = _normalize_ogh_gz(te.strip())
        m = re.match(r"^(\d{1,2})([A-Za-z]{1,4})(\d{1,4})/(\d{2})([a-z]?)$", te_norm)
        if m:
            # Accept formats like "3Ob224/12y", "3 Ob 224/12y", "3 Ob 224 / 12 y".
            senate = re.escape(m.group(2))
            pattern = rf"{m.group(1)}\s*{senate}\s*{m.group(3)}\s*/\s*{m.group(4)}\s*{re.escape(m.group(5))}"
        else:
            pattern = re.escape(te.strip()).replace(r"\ ", r"\s*")
        txt = re.sub(rf"[\(\[]?\s*{pattern}\s*[\)\]]?", "", txt)
    txt = re.sub(r"\(\s*\)", "", txt)
    txt = re.sub(r"\[\s*\]", "", txt)
    txt = re.sub(r",\s*,", ", ", txt)
    txt = re.sub(r"\s+([,.;:])", r"\1", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt.strip()


def _build_repair_evidence_snippets(
    subagent_results: list[dict[str, Any]],
    max_items: int = 12,
    max_chars: int = 380,
) -> list[str]:
    snippets: list[str] = []
    seen: set[str] = set()
    for rec in subagent_results or []:
        for tc in rec.get("tool_calls") or []:
            if not isinstance(tc, dict) or not tc.get("ok"):
                continue
            prev = tc.get("payload_preview")
            if not isinstance(prev, str) or not prev.strip():
                continue
            compact = re.sub(r"\s+", " ", prev).strip()
            if len(compact) > max_chars:
                compact = compact[:max_chars].rstrip() + "..."
            tool_name = str(tc.get("tool") or "tool")
            item = f"[{tool_name}] {compact}"
            if item in seen:
                continue
            seen.add(item)
            snippets.append(item)
            if len(snippets) >= max_items:
                return snippets
    return snippets


_DISMISSIVE_CITATION_RX = re.compile(
    r"\b(irrelevant|nicht\s+einschl[aä]gig|nicht\s+relevant|kein(?:en|e)?\s+unmittelbar(?:en|e)?\s+inhaltlich(?:en|e)?\s+bezug|nicht\s+herangezogen|nicht\s+anwendbar)\b",
    flags=re.I,
)


def _has_dismissive_citation_risk(answer: str, cited_rs: list[str], cited_te: list[str]) -> bool:
    text = answer or ""
    if not text or (not cited_rs and not cited_te):
        return False
    sentences = re.split(r"(?<=[\.\!\?])\s+|\n+", text)
    rs_set = {x for x in cited_rs if isinstance(x, str) and x.strip()}
    te_set = {_normalize_ogh_gz(x) for x in cited_te if isinstance(x, str) and x.strip()}
    for sent in sentences:
        if not sent or not _DISMISSIVE_CITATION_RX.search(sent):
            continue
        sent_norm = sent.strip()
        if any(rs in sent_norm for rs in rs_set):
            return True
        sent_compact_l = re.sub(r"\s+", "", sent_norm).lower()
        if any(re.sub(r"\s+", "", te).lower() in sent_compact_l for te in te_set):
            return True
    return False


def apply_hard_citation_gate(
    answer: str,
    query: str,
    subagent_results: list[dict[str, Any]],
    citation_gate_mode: str,
    repair_model: str,
    mcp_mode: str,
    mcp_base: str,
    remote_ssh: str,
    remote_mcp_container: str,
    postgres_only: bool,
) -> dict[str, Any]:
    mode = (citation_gate_mode or "warn").strip().lower()
    if mode == "off":
        return {
            "mode": "off",
            "applied": False,
            "before": None,
            "after": None,
            "repair": None,
            "answer": answer,
        }

    evidence = collect_citation_evidence(subagent_results, include_stream_answers=False)
    repair_evidence_snippets = _build_repair_evidence_snippets(subagent_results=subagent_results)
    query_requires_citations = bool(
        re.search(
            r"\b(fundstellen|judikatur|ziti(?:ere|erung|ert)|rechtssatz|rs\b|geschäftszahl|gz\b|nenne)\b",
            query or "",
            flags=re.I,
        )
    )
    # Case context snippets are part of the user-provided input and may contain
    # pre-curated RS/TE references. Treat them as admissible grounding evidence.
    query_context_rs = set(extract_rs_numbers(query))
    query_context_te = {_normalize_ogh_gz(x) for x in extract_ogh_te_citations(query)}
    query_context_norms = set(extract_norm_citations(query))

    def _evaluate(text: str) -> dict[str, Any]:
        cited_rs = extract_rs_numbers(text)
        cited_te = extract_ogh_te_citations(text)
        cited_rw = extract_rw_citations(text)
        cited_norms = extract_norm_citations(text)
        rs_validation = validate_rs_citations_via_mcp(
            cited_rs,
            mcp_mode=mcp_mode,
            mcp_base=mcp_base,
            remote_ssh=remote_ssh,
            remote_mcp_container=remote_mcp_container,
        )
        evidence_rs = set(evidence["rs"]) | query_context_rs
        evidence_te = {_normalize_ogh_gz(x) for x in evidence["te_ogh"]} | query_context_te
        evidence_norms = set(evidence["norms"]) | query_context_norms
        if _cv is not None:
            base_eval = _cv.evaluate_against_evidence(
                answer=text,
                evidence_rs=evidence_rs,
                evidence_te=evidence_te,
                evidence_norms=evidence_norms,
                rs_validation=rs_validation,
                require_judicature=query_requires_citations,
                postgres_only=bool(postgres_only),
            )
        else:
            invalid_rs = rs_validation.get("invalid") or []
            valid_rs = [x for x in cited_rs if x not in set(invalid_rs)]
            ungrounded_valid_rs = [x for x in valid_rs if x not in evidence_rs]
            ungrounded_te = [x for x in cited_te if _normalize_ogh_gz(x) not in evidence_te]
            ungrounded_norms = [x for x in cited_norms if x not in evidence_norms]
            unknown_law_norms: list[str] = []
            missing_required_citations = query_requires_citations and not (cited_rs or cited_te)
            missing_postgres_judicature = bool(postgres_only) and not (
                [x for x in valid_rs if x not in set(ungrounded_valid_rs)] or [x for x in cited_te if _normalize_ogh_gz(x) not in {_normalize_ogh_gz(y) for y in ungrounded_te}]
            )
            base_eval = {
                "pass_hard": (
                    (len(cited_rw) == 0)
                    and (len(invalid_rs) == 0)
                    and (len(ungrounded_valid_rs) == 0)
                    and (len(ungrounded_te) == 0)
                    and (len(ungrounded_norms) == 0)
                    and (not missing_required_citations)
                    and (not missing_postgres_judicature)
                ),
                "missing_required_citations": missing_required_citations,
                "missing_postgres_judicature": missing_postgres_judicature,
                "rw": {"cited": cited_rw},
                "rs": {
                    "cited": cited_rs,
                    "validation": rs_validation,
                    "valid": valid_rs,
                    "ungrounded_valid": ungrounded_valid_rs[:30],
                },
                "te_ogh": {"cited": cited_te, "ungrounded": ungrounded_te[:30]},
                "norms": {"cited": cited_norms, "ungrounded": ungrounded_norms[:30], "unknown_law_code": unknown_law_norms[:30]},
            }

        valid_rs = list(base_eval.get("rs", {}).get("valid") or [])
        ungrounded_valid_rs = list(base_eval.get("rs", {}).get("ungrounded_valid") or [])
        ungrounded_te = list(base_eval.get("te_ogh", {}).get("ungrounded") or [])
        ungrounded_norms = list(base_eval.get("norms", {}).get("ungrounded") or [])
        unknown_law_norms = list(base_eval.get("norms", {}).get("unknown_law_code") or [])
        dismissive_citation_risk = _has_dismissive_citation_risk(
            answer=text,
            cited_rs=valid_rs,
            cited_te=list(base_eval.get("te_ogh", {}).get("cited") or []),
        )
        text_lc = (text or "").lower()
        fallback_detected = ("fallback synthesis due to model error" in text_lc) or ("llm_error:" in text_lc)
        deterministic_postgres_only = "postgresql-only ergebnis (deterministisch aus tool-evidenz" in text_lc
        deterministic_gate_fallback = deterministic_postgres_only and ("gate-fallback" in text_lc)
        likely_prompt_echo = deterministic_postgres_only and (
            ("retrieval-hints:" in text_lc) or ("kontextauszug aus fallmaterial:" in text_lc)
        )
        norm_quality_risk = bool(postgres_only and (ungrounded_norms or unknown_law_norms))
        quality_degraded = fallback_detected or likely_prompt_echo or norm_quality_risk or dismissive_citation_risk
        has_any_citation = bool(cited_rs or cited_te or cited_norms)
        has_judicature_citation = bool(cited_rs or cited_te)
        missing_required_citations = bool(base_eval.get("missing_required_citations"))
        missing_postgres_judicature = bool(base_eval.get("missing_postgres_judicature"))
        has_forbidden_rw = bool(cited_rw)
        pass_hard = bool(base_eval.get("pass_hard")) and (not fallback_detected) and (not has_forbidden_rw)
        out = {
            "pass_hard": bool(pass_hard),
            "fallback_detected": fallback_detected,
            "missing_required_citations": missing_required_citations,
            "missing_postgres_judicature": missing_postgres_judicature,
            "has_forbidden_rw": has_forbidden_rw,
            "query_requires_citations": query_requires_citations,
            "has_any_citation": has_any_citation,
            "has_judicature_citation": has_judicature_citation,
            "quality_degraded": quality_degraded,
            "deterministic_postgres_only": deterministic_postgres_only,
            "deterministic_gate_fallback": deterministic_gate_fallback,
            "likely_prompt_echo": likely_prompt_echo,
            "norm_quality_risk": norm_quality_risk,
            "dismissive_citation_risk": dismissive_citation_risk,
            "rw": base_eval.get("rw") or {"cited": cited_rw},
            "rs": base_eval.get("rs") or {
                "cited": cited_rs,
                "validation": rs_validation,
                "valid": valid_rs,
                "ungrounded_valid": ungrounded_valid_rs[:30],
            },
            "te_ogh": base_eval.get("te_ogh") or {
                "cited": cited_te,
                "ungrounded": ungrounded_te[:30],
            },
            "norms": base_eval.get("norms") or {
                "cited": cited_norms,
                "ungrounded": ungrounded_norms[:30],
                "unknown_law_code": unknown_law_norms[:30],
            },
            "evidence": evidence,
        }
        return out

    before = _evaluate(answer)
    report: dict[str, Any] = {
        "mode": mode,
        "applied": False,
        "before": before,
        "after": before,
        "repair": None,
        "answer": answer,
    }
    before_norm_issues = list((before.get("norms") or {}).get("ungrounded") or []) + list((before.get("norms") or {}).get("unknown_law_code") or [])
    if before.get("pass_hard") and not (
        mode in {"repair", "enforce"} and (before_norm_issues or before.get("dismissive_citation_risk"))
    ):
        return report
    if mode in {"repair", "enforce"}:
        repaired, repair_meta = _repair_answer_citations(
            answer=answer,
            repair_model=repair_model,
            valid_rs=[x for x in before["rs"]["valid"] if x not in set(before["rs"]["ungrounded_valid"])],
            grounded_te=before["evidence"]["te_ogh"],
            grounded_norms=before["evidence"]["norms"],
            require_judicature=(query_requires_citations or bool(postgres_only)),
            evidence_snippets=repair_evidence_snippets,
            query_context_excerpt=query,
        )
        after = _evaluate(repaired)
        report["applied"] = repaired != answer
        report["repair"] = repair_meta
        report["after"] = after
        report["answer"] = repaired
        after_norm_issues = list((after.get("norms") or {}).get("ungrounded") or []) + list((after.get("norms") or {}).get("unknown_law_code") or [])
        if after_norm_issues and bool(postgres_only):
            current_answer = report["answer"]
            current_eval = report.get("after") or after
            current_norm_issues = after_norm_issues
            norm_iter = 0
            while current_norm_issues and norm_iter < 3:
                norm_iter += 1
                stripped = _strip_disallowed_norm_citations(current_answer, current_norm_issues)
                if not stripped or stripped == current_answer:
                    break
                stripped_after = _evaluate(stripped)
                stripped_norm_issues = list((stripped_after.get("norms") or {}).get("ungrounded") or []) + list(
                    (stripped_after.get("norms") or {}).get("unknown_law_code") or []
                )
                if len(stripped_norm_issues) > len(current_norm_issues):
                    break
                report["applied"] = True
                report["answer"] = stripped
                report["after"] = stripped_after
                if set(stripped_norm_issues) == set(current_norm_issues):
                    break
                current_answer = stripped
                current_eval = stripped_after
                current_norm_issues = stripped_norm_issues
            if isinstance(report.get("repair"), dict):
                final_norm_issues = list(((report.get("after") or {}).get("norms") or {}).get("ungrounded") or []) + list(
                    ((report.get("after") or {}).get("norms") or {}).get("unknown_law_code") or []
                )
                report["repair"]["auto_strip_disallowed_norms"] = True
                report["repair"]["auto_strip_disallowed_norms_count_before"] = len(after_norm_issues)
                report["repair"]["auto_strip_disallowed_norms_count_after"] = len(final_norm_issues)
        current_after = report.get("after") or after
        rs_validation = current_after.get("rs", {}).get("validation", {}) if isinstance(current_after, dict) else {}
        after_rs_issues = list((current_after.get("rs") or {}).get("ungrounded_valid") or []) + list(rs_validation.get("invalid") or [])
        after_te_issues = list((current_after.get("te_ogh") or {}).get("ungrounded") or [])
        if (after_rs_issues or after_te_issues) and bool(postgres_only):
            current_answer = report["answer"]
            current_after = report.get("after") or after
            current_rs_issues = after_rs_issues
            current_te_issues = after_te_issues
            jud_iter = 0
            while (current_rs_issues or current_te_issues) and jud_iter < 3:
                jud_iter += 1
                stripped = _strip_disallowed_judicature_citations(
                    answer=current_answer,
                    disallowed_rs=current_rs_issues,
                    disallowed_te=current_te_issues,
                )
                if not stripped or stripped == current_answer:
                    break
                stripped_after = _evaluate(stripped)
                stripped_rs_issues = list((stripped_after.get("rs") or {}).get("ungrounded_valid") or []) + list(
                    ((stripped_after.get("rs") or {}).get("validation") or {}).get("invalid") or []
                )
                stripped_te_issues = list((stripped_after.get("te_ogh") or {}).get("ungrounded") or [])
                if (len(stripped_rs_issues) + len(stripped_te_issues)) > (len(current_rs_issues) + len(current_te_issues)):
                    break
                report["applied"] = True
                report["answer"] = stripped
                report["after"] = stripped_after
                if set(stripped_rs_issues) == set(current_rs_issues) and set(stripped_te_issues) == set(current_te_issues):
                    break
                current_answer = stripped
                current_after = stripped_after
                current_rs_issues = stripped_rs_issues
                current_te_issues = stripped_te_issues
            if isinstance(report.get("repair"), dict):
                final_after = report.get("after") or after
                final_rs_issues = list((final_after.get("rs") or {}).get("ungrounded_valid") or []) + list(
                    ((final_after.get("rs") or {}).get("validation") or {}).get("invalid") or []
                )
                final_te_issues = list((final_after.get("te_ogh") or {}).get("ungrounded") or [])
                report["repair"]["auto_strip_disallowed_judicature"] = True
                report["repair"]["auto_strip_disallowed_judicature_count_before"] = len(after_rs_issues) + len(after_te_issues)
                report["repair"]["auto_strip_disallowed_judicature_count_after"] = len(final_rs_issues) + len(final_te_issues)
        current_after = report.get("after") or after
        if current_after.get("missing_required_citations") or current_after.get("missing_postgres_judicature"):
            ev = before.get("evidence") or {}
            rs_candidates_raw = list(ev.get("rs") or [])[:10]
            if not rs_candidates_raw:
                rs_candidates_raw = sorted(query_context_rs)[:10]
            rs_candidates: list[str] = []
            if rs_candidates_raw:
                rs_check = validate_rs_citations_via_mcp(
                    rs_numbers=rs_candidates_raw,
                    mcp_mode=mcp_mode,
                    mcp_base=mcp_base,
                    remote_ssh=remote_ssh,
                    remote_mcp_container=remote_mcp_container,
                )
                rs_candidates = list(rs_check.get("sample_valid") or [])[:3]
            if not rs_candidates:
                hints = _extract_retrieval_hints(query)
                probe_query = _search_query_for_tool("search_ogh_rechtssaetze", query, hints)
                probe = call_mcp_tool(
                    tool="search_ogh_rechtssaetze",
                    args={"query": probe_query, "limit": 5},
                    mcp_mode=mcp_mode,
                    mcp_base=mcp_base,
                    remote_ssh=remote_ssh,
                    remote_mcp_container=remote_mcp_container,
                    timeout=20.0,
                )
                payload = parse_tool_payload(probe.get("body") if isinstance(probe, dict) else None)
                probe_rs_raw: list[str] = []
                if isinstance(payload, dict):
                    for it in list(payload.get("results") or [])[:5]:
                        if not isinstance(it, dict):
                            continue
                        rs = _normalize_rs_number(str(it.get("rs_number") or ""))
                        if rs:
                            probe_rs_raw.append(rs)
                if probe_rs_raw:
                    rs_check = validate_rs_citations_via_mcp(
                        rs_numbers=probe_rs_raw,
                        mcp_mode=mcp_mode,
                        mcp_base=mcp_base,
                        remote_ssh=remote_ssh,
                        remote_mcp_container=remote_mcp_container,
                    )
                    rs_candidates = list(rs_check.get("sample_valid") or [])[:3]
                    if isinstance(report.get("repair"), dict):
                        report["repair"]["auto_probe_query"] = probe_query
                        report["repair"]["auto_probe_rs_candidates"] = rs_candidates
            te_candidates = list(ev.get("te_ogh") or [])[:3]
            if rs_candidates or te_candidates:
                appendix: list[str] = []
                appendix.append("Fundstellen (aus Tool-Evidenz):")
                for rs in rs_candidates:
                    appendix.append(f"- {rs}")
                for gz in te_candidates:
                    appendix.append(f"- {gz}")
                base_answer = str(report.get("answer") or repaired).rstrip()
                auto_cited = base_answer + "\n\n" + "\n".join(appendix)
                after2 = _evaluate(auto_cited)
                report["applied"] = True
                report["after"] = after2
                report["answer"] = auto_cited
                if isinstance(report.get("repair"), dict):
                    report["repair"]["auto_append_grounded_citations"] = True
                    report["repair"]["auto_append_rs"] = rs_candidates
                    report["repair"]["auto_append_te"] = te_candidates
        current_after = report.get("after") or after
        if mode == "enforce" and not current_after.get("pass_hard"):
            # Final hard fallback: deterministic answer from validated PostgreSQL evidence
            # instead of returning a blocked payload whenever possible.
            ev = before.get("evidence") or {}
            rs_raw = list(ev.get("rs") or [])[:12]
            if not rs_raw:
                rs_raw = sorted(query_context_rs)[:12]
            rs_fallback: list[str] = []
            if rs_raw:
                rs_check = validate_rs_citations_via_mcp(
                    rs_numbers=rs_raw,
                    mcp_mode=mcp_mode,
                    mcp_base=mcp_base,
                    remote_ssh=remote_ssh,
                    remote_mcp_container=remote_mcp_container,
                )
                rs_fallback = list(rs_check.get("sample_valid") or [])[:5]
            te_fallback = list(ev.get("te_ogh") or [])[:5]
            if not te_fallback:
                te_fallback = sorted(query_context_te)[:5]
            norm_fallback = list(ev.get("norms") or [])[:8]
            if not norm_fallback:
                norm_fallback = sorted(query_context_norms)[:8]

            if rs_fallback or te_fallback:
                lines: list[str] = []
                lines.append("PostgreSQL-only Ergebnis (deterministisch aus Tool-Evidenz, Gate-Fallback).")
                lines.append("")
                lines.append(f"Frage: {query}")
                lines.append("")
                lines.append("Belastbare Fundstellen aus PostgreSQL-Evidenz:")
                for rs in rs_fallback:
                    lines.append(f"- {rs}")
                for gz in te_fallback:
                    lines.append(f"- {gz}")
                for norm in norm_fallback:
                    lines.append(f"- {norm}")
                det_answer = "\n".join(lines)
                det_after = _evaluate(det_answer)
                if det_after.get("pass_hard"):
                    report["applied"] = True
                    report["after"] = det_after
                    report["answer"] = det_answer
                    if isinstance(report.get("repair"), dict):
                        report["repair"]["deterministic_gate_fallback"] = True
                        report["repair"]["deterministic_gate_fallback_rs"] = rs_fallback
                        report["repair"]["deterministic_gate_fallback_te"] = te_fallback
                    return report
            report["answer"] = (
                "Citation gate blocked final answer because hard citation constraints were not met.\n\n"
                + json.dumps(
                    {
                        "missing_postgres_judicature": bool(current_after.get("missing_postgres_judicature")),
                        "forbidden_rw": (current_after.get("rw") or {}).get("cited", []),
                        "invalid_rs": (current_after.get("rs") or {}).get("validation", {}).get("invalid", []),
                        "ungrounded_rs": (current_after.get("rs") or {}).get("ungrounded_valid", []),
                        "ungrounded_te": (current_after.get("te_ogh") or {}).get("ungrounded", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
    return report


def render_summary(
    query: str,
    organizer_model: str,
    worker_model: str,
    synth_model: str,
    model_profile: str,
    organizer_backend: str,
    mcp_mode: str,
    plan: dict[str, Any],
    organizer_meta: dict[str, Any] | None,
    synth_meta: dict[str, Any] | None,
    citation_gate: dict[str, Any] | None,
    subagent_results: list[dict[str, Any]],
    dry_run: bool,
) -> str:
    total_stream_ms = sum(float(x.get("e2e_ms") or 0.0) for x in subagent_results)
    total_tool_calls = sum(int(x.get("tool_calls_total") or 0) for x in subagent_results)
    total_tool_ok = sum(int(x.get("tool_calls_ok") or 0) for x in subagent_results)
    lines: list[str] = []
    lines.append("# LegalChat Agentic Harness Minimal Run")
    lines.append("")
    lines.append(f"- Timestamp (UTC): `{utc_now()}`")
    lines.append(f"- Dry run: `{dry_run}`")
    lines.append(f"- Query: `{query}`")
    lines.append(f"- Model profile: `{model_profile}`")
    lines.append(f"- Organizer backend: `{organizer_backend}`")
    lines.append(f"- MCP mode: `{mcp_mode}`")
    lines.append(f"- Organizer model: `{organizer_model}`")
    lines.append(f"- Worker model: `{worker_model}`")
    lines.append(f"- Synth model: `{synth_model}`")
    lines.append("")
    if organizer_meta:
        lines.append("## Organizer")
        lines.append(f"- latency_ms: `{organizer_meta.get('latency_ms')}`")
        lines.append(f"- used_fallback: `{organizer_meta.get('used_fallback')}`")
        lines.append("")
    lines.append("## Workstreams")
    for i, ws in enumerate(plan.get("workstreams") or [], start=1):
        lines.append(f"{i}. `{ws.get('name')}`")
        lines.append(f"   goal: `{ws.get('goal')}`")
        lines.append(f"   tools: `{ws.get('tools')}`")
    lines.append("")
    lines.append("## Execution Stats")
    lines.append(f"- subagent_count: `{len(subagent_results)}`")
    lines.append(f"- stream_total_ms: `{round(total_stream_ms, 2)}`")
    lines.append(f"- tool_calls_total: `{total_tool_calls}`")
    lines.append(f"- tool_calls_ok: `{total_tool_ok}`")
    lines.append(f"- tool_ok_rate: `{round(total_tool_ok / total_tool_calls, 3) if total_tool_calls else None}`")
    if synth_meta:
        lines.append(f"- synth_latency_ms: `{synth_meta.get('latency_ms')}`")
        lines.append(f"- final_answer_chars: `{synth_meta.get('answer_chars')}`")
    if citation_gate:
        before = citation_gate.get("before") or {}
        after = citation_gate.get("after") or {}
        lines.append(f"- citation_gate_mode: `{citation_gate.get('mode')}`")
        lines.append(f"- citation_gate_applied: `{citation_gate.get('applied')}`")
        lines.append(f"- citation_gate_pass_before: `{before.get('pass_hard')}`")
        lines.append(f"- citation_gate_pass_after: `{after.get('pass_hard')}`")
    lines.append("")
    lines.append("## Stream Details")
    for rec in subagent_results:
        lines.append(f"- `{rec.get('name')}`: ms={rec.get('e2e_ms')} | tools_ok={rec.get('tool_calls_ok')}/{rec.get('tool_calls_total')} | answer_chars={rec.get('answer_chars', len(rec.get('answer') or ''))}")
    lines.append("")
    return "\n".join(lines) + "\n"


def resolve_models(
    model_profile: str,
    organizer_model_override: str,
    worker_model_override: str,
    synth_model_override: str,
) -> tuple[str, str, str, str]:
    prof = MODEL_PROFILES.get(model_profile) or MODEL_PROFILES["default"]
    organizer_model = organizer_model_override.strip() or prof["organizer"]
    worker_model = worker_model_override.strip() or prof["worker"]
    synth_model = synth_model_override.strip() or prof["synth"]
    classifier_model = prof.get("classifier") or ""
    return organizer_model, worker_model, synth_model, classifier_model


def discover_config_dir(argv: list[str]) -> Path:
    cfg = DEFAULT_CONFIG_DIR
    for idx, arg in enumerate(argv):
        if arg == "--config-dir" and idx + 1 < len(argv):
            return Path(argv[idx + 1]).expanduser()
        if arg.startswith("--config-dir="):
            return Path(arg.split("=", 1)[1]).expanduser()
    return cfg


def main() -> int:
    raw_argv = sys.argv[1:]
    config_dir = discover_config_dir(raw_argv)
    config_meta = apply_runtime_config(config_dir)
    modes = MCP_RUNTIME.get("modes") if isinstance(MCP_RUNTIME.get("modes"), dict) else {}
    local_mode = modes.get("local_http") if isinstance(modes.get("local_http"), dict) else {}
    remote_ssh_mode = modes.get("remote_ssh") if isinstance(modes.get("remote_ssh"), dict) else {}
    guardrails = MCP_RUNTIME.get("guardrails") if isinstance(MCP_RUNTIME.get("guardrails"), dict) else {}
    max_parallel = max(1, int(guardrails.get("max_parallel_streams") or 3))

    ap = argparse.ArgumentParser(
        description="Minimal agentic harness for LegalChat (Organizer -> Subagents -> Synthesis) using MCP tools."
    )
    ap.add_argument("--config-dir", default=str(config_dir), help="Directory with agent_profiles.yaml + mcp_registry.yaml")
    ap.add_argument("--query", required=True, help="Legal question to process")
    ap.add_argument("--model-profile", choices=sorted(MODEL_PROFILES.keys()), default="default")
    ap.add_argument("--organizer-model", default="")
    ap.add_argument("--worker-model", default="")
    ap.add_argument("--synth-model", default="")
    ap.add_argument("--organizer-backend", choices=["openrouter", "opencode_sidecar", "ab_test"], default="openrouter")
    ap.add_argument("--opencode-sidecar-cmd", default="", help="Command used for organizer sidecar (reads prompt from stdin, returns plan JSON on stdout)")
    ap.add_argument("--opencode-sidecar-timeout-sec", type=int, default=90)
    ap.add_argument("--mcp-mode", choices=["local_http", "remote_http", "remote_ssh", "docker_exec"], default="local_http")
    ap.add_argument("--mcp-base", default=str(local_mode.get("base_url") or DEFAULT_MCP_BASE))
    ap.add_argument("--remote-ssh", default=str(remote_ssh_mode.get("ssh_host") or DEFAULT_REMOTE_SSH))
    ap.add_argument("--remote-mcp-container", default=str(remote_ssh_mode.get("container") or DEFAULT_REMOTE_MCP_CONTAINER))
    ap.add_argument("--max-workstreams", type=int, default=3)
    ap.add_argument("--max-steps", type=int, default=8)
    ap.add_argument("--parallelism", type=int, default=max_parallel)
    ap.add_argument("--citation-gate-mode", choices=["off", "warn", "repair", "enforce"], default="enforce")
    ap.add_argument("--citation-gate-repair-model", default="", help="Override model for citation repair (defaults to synth model)")
    ap.add_argument(
        "--grounding-policy",
        choices=["default", "postgres_only"],
        default="postgres_only",
        help="postgres_only = RS/TE statements must be grounded in PostgreSQL tool evidence.",
    )
    ap.add_argument("--dry-run", action="store_true", help="No OpenRouter calls; runs deterministic MCP probes only")
    ap.add_argument("--probe-limit", type=int, default=5, help="Tool result limit for dry-run probes")
    ap.add_argument("--keep-local-mcp", action="store_true")
    args = ap.parse_args(raw_argv)

    parsed_cfg = Path(args.config_dir).expanduser()
    if parsed_cfg != config_dir:
        config_dir = parsed_cfg
        config_meta = apply_runtime_config(config_dir)
        guardrails = MCP_RUNTIME.get("guardrails") if isinstance(MCP_RUNTIME.get("guardrails"), dict) else {}
        max_parallel = max(1, int(guardrails.get("max_parallel_streams") or max_parallel))

    organizer_model, worker_model, synth_model, classifier_model = resolve_models(
        model_profile=args.model_profile,
        organizer_model_override=args.organizer_model,
        worker_model_override=args.worker_model,
        synth_model_override=args.synth_model,
    )

    started_pid = None
    mcp_start_meta: dict[str, Any] | None = None
    if args.mcp_mode == "local_http" and args.mcp_base.rstrip("/") == DEFAULT_MCP_BASE:
        runner = load_runner_module()
        startup = runner.ensure_local_mcp_ready(auto_start=True)
        mcp_start_meta = startup
        if startup.get("started"):
            started_pid = int(startup.get("pid"))

    started_at = time.perf_counter()
    plan, organizer_meta = build_plan_with_organizer(
        query=args.query,
        organizer_model=organizer_model,
        max_workstreams=max(1, min(args.max_workstreams, 4)),
        dry_run=bool(args.dry_run),
        organizer_backend=args.organizer_backend,
        opencode_sidecar_cmd=args.opencode_sidecar_cmd,
        opencode_sidecar_timeout_sec=int(args.opencode_sidecar_timeout_sec),
        classifier_model=classifier_model,
    )

    streams = plan.get("workstreams") or []
    stream_results: list[dict[str, Any]] = []
    run_fn = run_subagent_dry if args.dry_run else run_subagent_llm

    # Phase 4: Pre-search scatter
    classification = (organizer_meta or {}).get("classification") or classify_domain(args.query)
    pre_search_evidence = ""
    if not args.dry_run:
        expanded = _expand_queries_with_llm(args.query, classification, classifier_model)
        pre_search_evidence = run_pre_search_scatter(
            expanded=expanded,
            mcp_mode=args.mcp_mode,
            mcp_base=args.mcp_base.rstrip("/"),
            remote_ssh=args.remote_ssh,
            remote_mcp_container=args.remote_mcp_container,
            query=args.query,
            classification=classification,
        )

    effective_parallelism = max(1, min(args.parallelism, max_parallel, len(streams) or 1))
    with cf.ThreadPoolExecutor(max_workers=effective_parallelism) as pool:
        futures = []
        for stream in streams:
            if args.dry_run:
                fut = pool.submit(
                    run_fn,  # type: ignore[arg-type]
                    stream,
                    args.query,
                    args.mcp_mode,
                    args.mcp_base.rstrip("/"),
                    args.remote_ssh,
                    args.remote_mcp_container,
                    args.probe_limit,
                )
            else:
                _all_names = [s.get("name", "") for s in streams]
                fut = pool.submit(
                    run_fn,  # type: ignore[arg-type]
                    stream,
                    args.query,
                    worker_model,
                    args.mcp_mode,
                    args.mcp_base.rstrip("/"),
                    args.remote_ssh,
                    args.remote_mcp_container,
                    args.max_steps,
                    pre_search_evidence,
                    _all_names,
                    classification,
                )
            futures.append(fut)
        for fut in cf.as_completed(futures):
            try:
                stream_results.append(fut.result())
            except Exception as e:
                stream_results.append(
                    {
                        "name": "unknown_stream",
                        "goal": "",
                        "mode": "error",
                        "tools": [],
                        "llm_error": str(e),
                        "tool_calls": [],
                        "tool_calls_total": 0,
                        "tool_calls_ok": 0,
                        "tool_calls_ok_rate": None,
                        "answer": f"Stream execution failed: {e}",
                        "answer_chars": len(f"Stream execution failed: {e}"),
                        "e2e_ms": None,
                    }
                )

    stream_results.sort(key=lambda x: str(x.get("name")))
    final_answer, synth_meta = synthesize_answer(
        query=args.query,
        synth_model=synth_model,
        plan=plan,
        subagent_results=stream_results,
        dry_run=bool(args.dry_run),
        postgres_only=(args.grounding_policy == "postgres_only"),
    )
    citation_gate = apply_hard_citation_gate(
        answer=final_answer,
        query=args.query,
        subagent_results=stream_results,
        citation_gate_mode=args.citation_gate_mode,
        repair_model=(args.citation_gate_repair_model.strip() or synth_model),
        mcp_mode=args.mcp_mode,
        mcp_base=args.mcp_base.rstrip("/"),
        remote_ssh=args.remote_ssh,
        remote_mcp_container=args.remote_mcp_container,
        postgres_only=(args.grounding_policy == "postgres_only"),
    )
    final_answer = citation_gate.get("answer") or final_answer
    elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 2)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = REPORT_ROOT / f"legalchat_agentic_harness_minimal_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "ok": True,
        "started_at_utc": utc_now(),
        "config": {
            "config_dir": str(config_dir),
            "query": args.query,
            "model_profile": args.model_profile,
            "organizer_model": organizer_model,
            "worker_model": worker_model,
            "synth_model": synth_model,
            "organizer_backend": args.organizer_backend,
            "opencode_sidecar_cmd": args.opencode_sidecar_cmd or None,
            "opencode_sidecar_timeout_sec": args.opencode_sidecar_timeout_sec,
            "mcp_mode": args.mcp_mode,
            "mcp_base": args.mcp_base.rstrip("/"),
            "remote_ssh": args.remote_ssh,
            "remote_mcp_container": args.remote_mcp_container,
            "max_workstreams": args.max_workstreams,
            "max_steps": args.max_steps,
            "parallelism": args.parallelism,
            "effective_parallelism": effective_parallelism,
            "citation_gate_mode": args.citation_gate_mode,
            "citation_gate_repair_model": args.citation_gate_repair_model or None,
            "grounding_policy": args.grounding_policy,
            "dry_run": bool(args.dry_run),
            "probe_limit": args.probe_limit,
        },
        "runtime_config": config_meta,
        "mcp_startup": mcp_start_meta,
        "classification": classification,
        "pre_search_evidence_chars": len(pre_search_evidence),
        "plan": plan,
        "organizer_meta": organizer_meta,
        "streams": stream_results,
        "synth_meta": synth_meta,
        "citation_gate": citation_gate,
        "final_answer": final_answer,
        "elapsed_ms": elapsed_ms,
    }
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "subagents.json").write_text(json.dumps(stream_results, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "final_answer.md").write_text(final_answer + "\n", encoding="utf-8")
    summary = render_summary(
        query=args.query,
        organizer_model=organizer_model,
        worker_model=worker_model,
        synth_model=synth_model,
        model_profile=args.model_profile,
        organizer_backend=args.organizer_backend,
        mcp_mode=args.mcp_mode,
        plan=plan,
        organizer_meta=organizer_meta,
        synth_meta=synth_meta,
        citation_gate=citation_gate,
        subagent_results=stream_results,
        dry_run=bool(args.dry_run),
    )
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")

    if started_pid and not args.keep_local_mcp:
        try:
            runner._terminate_pid_or_group(int(started_pid))
        except Exception:
            pass

    print(
        json.dumps(
            {
                "ok": True,
                "out_dir": str(out_dir),
                "summary_md": str(out_dir / "summary.md"),
                "result_json": str(out_dir / "result.json"),
                "elapsed_ms": elapsed_ms,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
