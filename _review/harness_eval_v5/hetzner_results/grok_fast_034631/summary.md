# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:46:31.581037+00:00`
- Dry run: `False`
- Query: `Eine einkommenslose Ehefrau hat auf Druck ihres Mannes eine Bürgschaft über 150.000 Euro für dessen Geschäftskredit bei der Hausbank mitunterschrieben. Die Bank hat sie nicht über die wirtschaftliche Lage ihres Mannes aufgeklärt. Der Mann ist insolvent, die Bank betreibt jetzt aus einem Versäumungsurteil gegen die Ehefrau Fahrnisexekution. Die Ehefrau hat den Einspruch gegen das Versäumungsurteil versäumt. Welche Möglichkeiten hat die Ehefrau noch?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `6785.2`
- used_fallback: `False`

## Workstreams
1. `Rechtliche Grundlagen der Interzession & Bürgschaftsrechtsfolgen`
   goal: `Klären der Haftungs- und Anfechtbarkeitsvoraussetzungen für die ehefrauengebundene Bürgschaft unter Berücksichtigung von § 25c/d KSchG, § 879 ABGB, § 1346 ABGB`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Anfechtungsmöglichkeiten nach Versäumung des Einspruchs`
   goal: `Prüfen, ob nach Versäumung des Einspruchs gegen das Versäumungsurteil noch Rechtsbehelfe (z. B. Wiedereinsetzung, Anfechtungsklage, Exekutionsverbot nach § 35 EO) bestehen`
   tools: `['search_ogh_entscheidungen', 'search_kommentar_paragraph', 'hot_cluster_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Bankaufklärungspflicht & Vertragswidrigkeit`
   goal: `Prüfen, ob die Bank durch Unterlassung der Aufklärung über die wirtschaftliche Lage des Schuldners in die Vertragswidrigkeit der Bürgschaft eingegriffen hat (§ 25c KSchG iVm § 879 ABGB)`
   tools: `['search_kommentar_keyword', 'build_grounding_context', 'detect_clusters', 'hot_index_stats', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `139582.92`
- tool_calls_total: `61`
- tool_calls_ok: `61`
- tool_ok_rate: `1.0`
- synth_latency_ms: `23954.34`
- final_answer_chars: `6344`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anfechtungsmöglichkeiten nach Versäumung des Einspruchs`: ms=47265.2 | tools_ok=18/18 | answer_chars=3668
- `Bankaufklärungspflicht & Vertragswidrigkeit`: ms=53639.71 | tools_ok=24/24 | answer_chars=4155
- `Rechtliche Grundlagen der Interzession & Bürgschaftsrechtsfolgen`: ms=38678.01 | tools_ok=19/19 | answer_chars=4492

