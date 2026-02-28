# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:05:03.405628+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Gib eine One-Shot-Rekursanalyse zum Fall MITTER:CELSIUS mit Schwerpunkt Zustellmaengel: Wirksamkeit der Zustellung ohne deutsche Uebersetzung (Art 5 Abs 3 HZUE oesterreichische Erklaerung), Abgabestelle bei Hinterlegung (§17 ZustG iVm §2 Z4 ZustG), Heilung (§8 Abs 2 ZustG), ZMR-Abfragepflicht (§163 Abs 4 Geo), Belehrungspflicht GeoForm 44 (§163 Abs 5 Geo, §12 ZustG), Gehoerverletzung/Nichtigkeit (§477 Abs 1 Z 4 ZPO, Art 6 EMRK), Bindungswirkung Zustellzeugnis Art 6 HZUE (RS0134713). Nenne die wichtigsten RS/TE zur Absicherung und priorisiere die Standbeine.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12047` chars, `2` files, `0` OCR

## Organizer
- latency_ms: `4770.26`
- used_fallback: `True`

## Workstreams
1. `ogh_rs_core`
   goal: `Find the most relevant OGH RS + TE and capture stable references.`
   tools: `['search_ogh_rechtssaetze', 'search_ogh_entscheidungen', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort']`
2. `hot_index_context`
   goal: `Retrieve top hot-index context and mini-story evidence.`
   tools: `['hot_rs_search', 'hot_cluster_context', 'hot_rs_lookup']`
3. `grounding_expert`
   goal: `Get cluster-level grounding context and expert analysis for the legal question.`
   tools: `['build_grounding_context', 'detect_clusters', 'ask_gemini_zivilrecht', 'search_kommentar_paragraph', 'search_kommentar_keyword']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `54001.71`
- tool_calls_total: `56`
- tool_calls_ok: `56`
- tool_ok_rate: `1.0`
- synth_latency_ms: `43222.07`
- final_answer_chars: `7154`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `grounding_expert`: ms=16561.16 | tools_ok=12/12 | answer_chars=3816
- `hot_index_context`: ms=17551.48 | tools_ok=21/21 | answer_chars=3450
- `ogh_rs_core`: ms=19889.07 | tools_ok=23/23 | answer_chars=4302

