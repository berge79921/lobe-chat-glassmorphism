# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T04:07:12.012535+00:00`
- Dry run: `False`
- Query: `Hannes Grubmair lässt nach einem Unfall seinen PKW günstig vom Freund reparieren und gibt ihn der Gebrauchtwagen-GmbH (Geschäftsführerin Paula Gabler) zum Weiterverkauf. Vereinbart: Bei Verkauf erhält Grubmair EUR 17.000. Die GmbH verkauft den PKW an Marius um EUR 22.000 mit Kreditkarte. Marius fährt auf eine Tankstelle und tankt um EUR 80, fährt ohne zu zahlen davon. Ein Jahr später stellt sich heraus, dass die Kreditkartenzahlung des Marius nicht gedeckt war. Die GmbH geht insolvent. Grubmair hat nie Geld erhalten. Welche Ansprüche hat Grubmair? Welche Ansprüche hat der Tankstellenbetreiber?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `4155.42`
- used_fallback: `False`

## Workstreams
1. `Ansprüche Grubmair gegen GmbH/Gabler`
   goal: `Ermitteln von Ansprüchen des Verkäufer-Grubmair gegen die GmbH/Geschäftsführerin auf Zahlung des vereinbarten Verkaufspreisanteils (EUR 17.000) und ggf. Schadensersatz`
   tools: `['search_by_paragraph', 'search_kommentar_paragraph', 'get_rechtssatz', 'hot_rs_lookup', 'build_grounding_context', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Ansprüche Tankstellenbetreiber`
   goal: `Klären, ob und gegen wen (GmbH, Gabler, Marius, Grubmair?) Ansprüche auf Zahlung des Tankpreises (EUR 80) bestehen, insb. im Insolvenzfall`
   tools: `['search_by_paragraph', 'search_kommentar_paragraph', 'search_ogh_entscheidungen', 'hot_cluster_context', 'detect_clusters', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Insolvenz- und Sicherheitenfragen`
   goal: `Prüfen, ob Grubmair oder Tankstelle Sicherheitsrechte (z.B. Eigentumsvorbehalt, Rechtsmitteln im Insolvenzverfahren) geltend machen können`
   tools: `['search_by_schlagwort', 'search_kommentar_keyword', 'hot_index_stats', 'hot_rs_search', 'search_by_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `260902.02`
- tool_calls_total: `81`
- tool_calls_ok: `81`
- tool_ok_rate: `1.0`
- synth_latency_ms: `28327.57`
- final_answer_chars: `5769`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Ansprüche Grubmair gegen GmbH/Gabler`: ms=111571.47 | tools_ok=36/36 | answer_chars=3909
- `Ansprüche Tankstellenbetreiber`: ms=105957.6 | tools_ok=28/28 | answer_chars=2458
- `Insolvenz- und Sicherheitenfragen`: ms=43372.95 | tools_ok=17/17 | answer_chars=3066

