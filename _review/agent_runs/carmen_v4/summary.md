# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T13:33:36.626608+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Fasse den Fall CARMEN als strategische anwaltliche Ersteinschaetzung zusammen: welche 2-3 Rechtsfragen sind entscheidend? Wie sind EO-/Praeklusion-/Interzessions-Aspekte zu priorisieren? §14 IO (Akzessorietaet in Insolvenz), §7 Abs 3 EO, §25c KSchG, §40 EO, §35 EO, §42 EO. Welche Schritte bringen kurzfristig den groessten Nutzen? Nenne die wichtigsten RS/TE zur Absicherung.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12043` chars, `2` files, `0` OCR

## Organizer
- latency_ms: `6283.14`
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
- stream_total_ms: `48064.14`
- tool_calls_total: `53`
- tool_calls_ok: `53`
- tool_ok_rate: `1.0`
- synth_latency_ms: `42041.33`
- final_answer_chars: `7450`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `grounding_expert`: ms=15462.19 | tools_ok=9/9 | answer_chars=3232
- `hot_index_context`: ms=16643.09 | tools_ok=22/22 | answer_chars=2940
- `ogh_rs_core`: ms=15958.86 | tools_ok=22/22 | answer_chars=3547

