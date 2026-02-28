# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:39:51.800877+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Erstelle eine anwaltliche Ersteinschaetzung zum Fall ULLRICH (Invaliditaetspension, Klaeger geb. 19.07.1967, LG St. Poelten): Berufsschutz (§255 Abs 1 ASVG erlernter Beruf, §255 Abs 2 ASVG Ueberwiegen qualifizierter Pflichtversicherungsmonate 90 Monate im 15-Jahres-Rahmen, Post-Lehrzeit-Monate zaehlen), Verweisbarkeit (§255 Abs 3 ASVG Lohnhaelfte-Massstab, Verweisungsberuf zumutbar wenn aehnliches Umfeld und Teilfaehigkeiten), Anrechnung Krankengeld (§255 Abs 4 ASVG max 24 Monate bei beruflicher Kausalitaet), Rehabilitationsgeld (§143a ASVG voruebergehende Invaliditaet, kein Stichtag, Bemessung §125 ASVG). Pruefe insbesondere: Ueberwiegen qualifizierter vs unqualifizierter Monate, ob nur Post-Lehrzeit zaehlt, ob Verweisung auf aehnliches Arbeitsumfeld beschraenkt ist. Nenne die wichtigsten RS/TE zum Berufsschutz, Verweisbarkeit und Rehabilitationsgeld nach ASVG.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12108` chars, `3` files, `0` OCR

## Organizer
- latency_ms: `5997.43`
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
- stream_total_ms: `52832.24`
- tool_calls_total: `57`
- tool_calls_ok: `57`
- tool_ok_rate: `1.0`
- synth_latency_ms: `43965.72`
- final_answer_chars: `7689`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `grounding_expert`: ms=17109.2 | tools_ok=14/14 | answer_chars=3132
- `hot_index_context`: ms=13291.6 | tools_ok=16/16 | answer_chars=3135
- `ogh_rs_core`: ms=22431.44 | tools_ok=27/27 | answer_chars=3871

