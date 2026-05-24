# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:16:17.907389+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Analysiere den Fall KOLAR gegen PFEFFER aus Sicht der betreibenden Partei (Kolar): Wirksamkeit der Hinterlegungszustellung (§17 ZustG, RSb-Hinterlegung 12.12.2025, retourniert 30.12.2025), Beweiskraft des Zustellscheins als oeffentliche Urkunde (§292 ZPO, Rueckschein beurkundet Zustellvollzug), Abwehr eines erwarteten Wiedereinsetzungsantrags der Beklagten (§146 ZPO, Verschulden, auffallende Sorglosigkeit, treuwidrige Abwesenheit/Verhinderung des Zugangs), Ortsabwesenheit pensionierte Beklagte (geb. 07.01.1940). Nenne die wichtigsten RS/TE insb. zur Beweiskraft des Zustellscheins als oeffentliche Urkunde und zur Hinterlegungszustellung.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12043` chars, `2` files, `0` OCR

## Organizer
- latency_ms: `6899.92`
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
- stream_total_ms: `49535.37`
- tool_calls_total: `47`
- tool_calls_ok: `47`
- tool_ok_rate: `1.0`
- synth_latency_ms: `37901.79`
- final_answer_chars: `7534`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `grounding_expert`: ms=17482.94 | tools_ok=13/13 | answer_chars=3972
- `hot_index_context`: ms=13111.25 | tools_ok=12/12 | answer_chars=3215
- `ogh_rs_core`: ms=18941.18 | tools_ok=22/22 | answer_chars=3703

