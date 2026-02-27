# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:15:08.716397+00:00`
- Dry run: `False`
- Query: `Hannes Grubmair lässt nach einem Unfall seinen PKW günstig vom Freund reparieren und gibt ihn der Gebrauchtwagen-GmbH (Geschäftsführerin Paula Gabler) zum Weiterverkauf. Vereinbart: Bei Verkauf erhält Grubmair EUR 17.000. Die GmbH verkauft den PKW an Marius um EUR 22.000 mit Kreditkarte. Marius fährt auf eine Tankstelle und tankt um EUR 80, fährt ohne zu zahlen davon. Ein Jahr später stellt sich heraus, dass die Kreditkartenzahlung des Marius nicht gedeckt war. Die GmbH geht insolvent. Grubmair hat nie Geld erhalten. Welche Ansprüche hat Grubmair? Welche Ansprüche hat der Tankstellenbetreiber?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3912.53`
- used_fallback: `False`

## Workstreams
1. `Ansprüche Grubmair gegen GmbH/Gabler`
   goal: `Ermitteln von Ansprüchen des Grubmair gegen die GmbH und deren Geschäftsführerin auf Zahlung des vereinbarten Verkaufspreisanteils (EUR 17.000)`
   tools: `['search_by_paragraph', 'search_by_schlagwort', 'hot_rs_lookup', 'search_kommentar_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
2. `Ansprüche Tankstellenbetreiber`
   goal: `Prüfen, ob und gegen wen (Marius, GmbH, Grubmair) der Tankstellenbetreiber Ansprüche auf Zahlung des Tankpreises (EUR 80) hat`
   tools: `['search_by_paragraph', 'search_by_schlagwort', 'hot_rs_lookup', 'search_kommentar_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
3. `Insolvenzrechtliche Abwicklung & Sicherheiten`
   goal: `Klären, ob Grubmair oder Tankstelle als Gläubiger in der Insolvenz der GmbH berücksichtigt werden können (z. B. Eigentumsvorbehalt, Rechtsfolgen der Unbezahltheit)`
   tools: `['search_by_paragraph', 'hot_rs_search', 'search_kommentar_keyword', 'build_grounding_context', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `283888.97`
- tool_calls_total: `78`
- tool_calls_ok: `78`
- tool_ok_rate: `1.0`
- synth_latency_ms: `31524.63`
- final_answer_chars: `6441`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Ansprüche Grubmair gegen GmbH/Gabler`: ms=84994.56 | tools_ok=27/27 | answer_chars=3573
- `Ansprüche Tankstellenbetreiber`: ms=111083.03 | tools_ok=29/29 | answer_chars=3016
- `Insolvenzrechtliche Abwicklung & Sicherheiten`: ms=87811.38 | tools_ok=22/22 | answer_chars=3296

