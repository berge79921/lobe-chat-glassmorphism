# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:32:38.855342+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Erstelle eine anwaltliche Ersteinschaetzung zum Fall ULLRICH (Invaliditaetspension): Berufsschutz (§255 Abs 1 ASVG erlernter Beruf, §255 Abs 2 ASVG qualifizierte Pflichtversicherungsmonate 90 Monate im 15-Jahres-Rahmen), Verweisbarkeit (§255 Abs 3 ASVG Lohnhaelfte-Massstab), Anrechnung Krankengeld (§255 Abs 4 ASVG max 24 Monate), Rehabilitationsgeld (§143a ASVG voruebergehende Invaliditaet). Nenne die wichtigsten RS/TE zum Berufsschutz und zur Verweisbarkeit nach ASVG.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `5565.93`
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
- stream_total_ms: `50075.1`
- tool_calls_total: `55`
- tool_calls_ok: `55`
- tool_ok_rate: `1.0`
- synth_latency_ms: `35605.88`
- final_answer_chars: `6303`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `grounding_expert`: ms=14931.81 | tools_ok=12/12 | answer_chars=3912
- `hot_index_context`: ms=14362.86 | tools_ok=19/19 | answer_chars=3742
- `ogh_rs_core`: ms=20780.43 | tools_ok=24/24 | answer_chars=4488

