# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:08:36.042131+00:00`
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
- latency_ms: `5007.81`
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
- stream_total_ms: `63310.97`
- tool_calls_total: `61`
- tool_calls_ok: `61`
- tool_ok_rate: `1.0`
- synth_latency_ms: `36407.01`
- final_answer_chars: `6964`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `grounding_expert`: ms=20224.11 | tools_ok=15/15 | answer_chars=3774
- `hot_index_context`: ms=18845.47 | tools_ok=21/21 | answer_chars=3800
- `ogh_rs_core`: ms=24241.39 | tools_ok=25/25 | answer_chars=5110

