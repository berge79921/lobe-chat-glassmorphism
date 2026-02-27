# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:44:39.860108+00:00`
- Dry run: `False`
- Query: `Eine einkommenslose Ehefrau hat auf Druck ihres Mannes eine Bürgschaft über 150.000 Euro für dessen Geschäftskredit bei der Hausbank mitunterschrieben. Die Bank hat sie nicht über die wirtschaftliche Lage ihres Mannes aufgeklärt. Der Mann ist insolvent, die Bank betreibt jetzt aus einem Versäumungsurteil gegen die Ehefrau Fahrnisexekution. Die Ehefrau hat den Einspruch gegen das Versäumungsurteil versäumt. Welche Möglichkeiten hat die Ehefrau noch?`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `4635.15`
- used_fallback: `False`

## Workstreams
1. `Rechtliche Grundlagen der Interzession & Bürgschaftsrechtsfolgen`
   goal: `Klären der Haftungs- und Anfechtbarkeitsvoraussetzungen bei Interzessionsbürgschaft, insb. unter Berücksichtigung von § 25c/d KSchG, § 879 ABGB, § 1346 ABGB`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Anfechtungsmöglichkeiten nach Versäumung des Einspruchs`
   goal: `Prüfen, ob und wie der versäumte Einspruch gegen das Versäumungsurteil nach § 35 EO rechtsmittelfähig und -zulässig angefochten werden kann (z. B. über Rechtsbeschwerde, Wiedereinsetzung)`
   tools: `['search_ogh_entscheidungen', 'hot_rs_search', 'search_kommentar_paragraph', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Exekutionsrechtliche Schutzinstrumente`
   goal: `Identifikation von exekutionsrechtlichen Hemmnissen (z. B. Einrede der Unwirksamkeit, Exekutionsaufschub, § 25c KSchG-Anwendung) gegen die Fahrnisexekution`
   tools: `['search_ogh_rechtssaetze', 'hot_cluster_context', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `79755.68`
- tool_calls_total: `64`
- tool_calls_ok: `64`
- tool_ok_rate: `1.0`
- synth_latency_ms: `21154.46`
- final_answer_chars: `6620`
- citation_gate_mode: `enforce`
- citation_gate_applied: `False`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Anfechtungsmöglichkeiten nach Versäumung des Einspruchs`: ms=29822.48 | tools_ok=22/22 | answer_chars=3650
- `Exekutionsrechtliche Schutzinstrumente`: ms=27935.76 | tools_ok=26/26 | answer_chars=3319
- `Rechtliche Grundlagen der Interzession & Bürgschaftsrechtsfolgen`: ms=21997.44 | tools_ok=16/16 | answer_chars=3568

