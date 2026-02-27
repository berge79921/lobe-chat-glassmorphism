# Agentic Harness Architecture (External Review)

Stand: 27. Februar 2026 (V3 Update)

## 1. Scope

Diese Architektur beschreibt nur den LegalChat-Agentic-Harness:

- Rollenorchestrierung (Organizer, Worker, Synthese, Citation-Repair)
- MCP-Tool-Nutzung inkl. Power-Tools (Cluster-Grounding, Expert-Modell)
- Domain-Klassifikation und Query-Expansion
- Pre-Search Scatter (parallele MCP-Vorrecherche)
- Guardrails fuer Zitate und Grounding
- Local/Remote Ausfuehrungsmodi
- Multi-Model-Profile mit konfigurierbarem Worker/Synth/Organizer

Nicht Teil dieses Dokuments:

- Vollstaendige Super-RIS Datenmigration
- Vollstaendige MCP-Server-Implementierung im Detail
- UI/Login-Proxy Gesamtarchitektur

## 2. Zielbild

Ein reproduzierbarer, modellagnostischer Harness, der fachliche Antworten nur auf PostgreSQL-geerdeter Evidenz erzeugt und unsafe Halluzinationen ueber harte Gates blockiert oder repariert.

## 3. Runtime-Komponenten

1. Harness Runner:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/scripts/legalchat_agentic_harness_minimal.py`
2. Policy/Runtime-Config:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/config/agent_profiles.yaml`
   - `/Users/reinhardberger/HCS/lobe-chat-custom/config/mcp_registry.yaml`
   - `/Users/reinhardberger/HCS/lobe-chat-custom/config/skills_bindings.yaml`
3. MCP Layer:
   - `mcp-zivilrecht` (HTTP Bridge oder via SSH+container exec)
4. Evidence Store:
   - PostgreSQL (`super_ris`, `hot_*`, `kommentar.*`)
5. LLM Layer:
   - OpenRouter Modelle je Rolle (profilgesteuert)

## 4. Request-Flow (V3)

1. Input Query.
2. **Domain-Klassifikation** (deterministisch + LLM-Fallback): Erkennt Rechtsgebiet und §§.
3. **Query-Expansion** (cheap LLM): Erzeugt paragraph_queries, schlagwort_queries, keyword_queries.
4. **Pre-Search Scatter** (parallel, 8-10 MCP-Calls): search_by_paragraph, search_by_schlagwort, search_ogh_rechtssaetze, build_grounding_context, detect_clusters — Ergebnisse als Worker-Startkontext (bis 5000 Zeichen).
5. Organizer baut Workstreams (Tool-Plan) mit Domain-Guidance fuer Power-Tools.
6. Worker fuehren Tool-Calls je Stream aus (phasengesteuerter Prompt, max 8 Steps, Cross-Stream-Awareness).
7. Forced Deep-Dive: RS-Nummern aus Tool-Traces die nicht vertieft wurden, werden automatisch nachgeladen.
8. Synthese erzeugt finale Antwort aus Stream-Evidenz (strukturiertes 6-Sektionen-Format, max 2800 Tokens).
9. Hard Citation Gate validiert RS/TE/Normen gegen Evidenz.
10. Optional: Repair-Schritt mit erlaubtem Citation-Set.
11. Persistenz von Run-Artefakten (`result.json`, `subagents.json`, `summary.md`).

## 5. Modes und Isolation

Unterstuetzte MCP-Modi:

- `local_http`
- `remote_http`
- `remote_ssh`

Sicherheits-/Stabilitaetsguardrails aus `mcp_registry.yaml`:

- `statement_timeout_ms=30000`
- `max_result_rows=50`
- `max_query_length=500`
- `max_parallel_streams=3`

## 6. Tool-Policy und Rollenmodell

Rollen:

- `organizer`: Routing/Planung, begrenzte Toolliste.
- `worker`: Evidenzsammlung, gleiche juristische Kern-Tools.
- `synth`: keine Tools.
- `citation_repair`: keine Tools.

Kern-Tools (Retrieval):

- `search_ogh_rechtssaetze`
- `search_ogh_entscheidungen`
- `get_rechtssatz`
- `search_by_paragraph` (V3: neu)
- `search_by_schlagwort` (V3: neu)
- `hot_rs_search`
- `hot_rs_lookup` (V3: neu)
- `hot_cluster_context`
- `hot_index_stats` (V3: neu)
- `search_kommentar_paragraph`
- `search_kommentar_keyword`

Power-Tools (V3: Cluster-Grounding und Expert-Analyse):

- `build_grounding_context` — Cluster-Level Minimal-Ruleset mit RS-Zitaten aus TopicPreprocessor
- `detect_clusters` — Automatische Cluster-Erkennung via Keyword-Matching
- `ask_gemini_zivilrecht` — Fine-tuned Gemini Experte fuer Laesio/Bereicherung/Pflichtteil

## 7. Hard Grounding Contract

Erzwingung ueber Runtime-Flags:

- `--grounding-policy postgres_only`
- `--citation-gate-mode enforce|repair`

Contract:

- Juridische Claims duerfen nur aus MCP-Evidence stammen.
- Freies "Vorwissen" ohne Evidence ist nicht zulaessig.
- Ungueltige oder ungegroundete Zitate werden als Gate-Verstoss markiert.

## 8. State und Artefakte

Pro Run:

- `plan.json`
- `subagents.json`
- `result.json`
- `final_answer.md`
- `summary.md`

Run-Verzeichnisse liegen unter:

- `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/`

## 9. 10-Faelle Validierung (current snapshot)

Eingefrorene Baseline:

- `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/baselines/qwen_all_2026-02-26_final/summary.json`

Kernwerte:

- `case_count=10`, local/remote `ok=10/10`
- Citation gate pass local/remote: `1.0/1.0`
- Invalid RS total local/remote: `0/0`
- Ungrounded RS/TE total local/remote: `0/0`
- Unknown norms total local/remote: `0/0`

Interpretation:

- Safety und Grounding sind im Snapshot durchgehend gruen.
- Latenz remote > lokal, fachliche Mindestqualitaet jedoch gehalten.

## 10. V3 Worker-Optimierungen (27.02.2026)

5 Optimierungen im Worker-Loop und Evidence-Pipeline:

1. Pre-search Evidence Limit 3000→5000 Zeichen (+67% Worker-Startkontext).
2. Power-Tools im Worker-System-Prompt (Phase 2B: build_grounding_context, ask_gemini_zivilrecht).
3. Payload Preview 1600→2400 fuer High-Value-Tools (+50% RS-Diversitaet in Synthese).
4. Organizer Domain Guidance: Bei confidence>=0.5 wird Power-Tool-Workstream empfohlen.
5. Cross-Stream Awareness: Worker sehen Namen paralleler Streams zur Duplikationsvermeidung.

## 11. Modellprofile (V3)

| Profil | Organizer | Worker | Synth | Einsatz |
|--------|-----------|--------|-------|---------|
| `grok_worker` (Default) | qwen/qwen3-coder-next | x-ai/grok-4.1-fast | google/gemini-3-flash-preview | Beste Qualitaet |
| `minimax_worker` | qwen/qwen3-coder-next | minimax/minimax-m2.5 | google/gemini-3-flash-preview | Budget-Alternative |
| `cheap_default` | qwen/qwen3-coder-next | google/gemini-2.5-flash-lite | google/gemini-3-flash-preview | Legacy Baseline |
| `qwen_all` | qwen/qwen3-coder-next | qwen/qwen3-coder-next | qwen/qwen3-coder-next | Gefrorene Baseline |
| `premium_champion` | openai/gpt-5.3-codex | x-ai/grok-4.1-fast | openai/gpt-5.3-codex | Premium |

## 12. Offene Architektur-Themen

1. Organizer-Qualitaet fuer komplexe Multi-Hop-Queries weiter stabilisieren.
2. Optionaler OpenCode-Sidecar als austauschbarer Organizer-Backend-Pfad.
3. Erweiterte Skill-Runtime (heute: policy-contract, nicht vollautomatisches Skill-Exec).
4. Deterministische Replay-Option fuer noch engere Reproduzierbarkeit.
5. MiniMax M2.5: 33-Tool-Limit untersuchen (internes Modell-Limit vs. Konfiguration).
6. ask_gemini_zivilrecht: Breitere Domain-Abdeckung ueber Laesio/Bereicherung/Pflichtteil hinaus.
