# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:42:50.971438+00:00`
- Dry run: `False`
- Query: `Ein Tischlermeister wird wegen Knieproblemen operiert. Bei der OP kommt es zu einem Lagerungsfehler, der zu einer Peroneusschädigung (Nervenschaden am Bein) führt. Folgen: Dauerschmerzen, Berufsunfähigkeit als Tischler, lebenslange Einschränkungen. Der Patient hatte nur ein allgemeines OP-Aufklärungsformular unterschrieben, das Lagerungsrisiken nicht erwähnt. Welche Ansprüche hat der Patient gegen das Krankenhaus und den Arzt?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3148.82`
- used_fallback: `False`

## Workstreams
1. `Anspruchsgrundlagen klären (§§ 1321, 1322 ABGB, KHEntgG)`
   goal: `Identifizierung der rechtlichen Anspruchsgrundlagen bei Behandlungsfehlern und Aufklärungsmangel im Krankenhausverhältnis`
   tools: `['search_by_paragraph', 'search_ogh_rechtssaetze', 'search_kommentar_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`
2. `Aufklärungsmangel prüfen (§ 1326a ABGB, informierte Einwilligung)`
   goal: `Ermittlung, ob das allgemeine Formular ausreicht und ob Lagerungsrisiken explizit aufgeklärt werden müssen`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'search_kommentar_keyword', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Sozialversicherungsrechtliche Folgen (Invaliditäts- / Krankengeldanspruch)`
   goal: `Zuordnung der Folgen (Berufsunfähigkeit, Dauerschmerzen) zu sozialversicherungsrechtlichen Leistungsansprüchen`
   tools: `['search_by_schlagwort', 'hot_cluster_context', 'hot_rs_lookup', 'search_by_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `175029.26`
- tool_calls_total: `63`
- tool_calls_ok: `62`
- tool_ok_rate: `0.984`
- synth_latency_ms: `18984.1`
- final_answer_chars: `5546`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anspruchsgrundlagen klären (§§ 1321, 1322 ABGB, KHEntgG)`: ms=72106.14 | tools_ok=28/29 | answer_chars=3533
- `Aufklärungsmangel prüfen (§ 1326a ABGB, informierte Einwilligung)`: ms=47599.55 | tools_ok=17/17 | answer_chars=2868
- `Sozialversicherungsrechtliche Folgen (Invaliditäts- / Krankengeldanspruch)`: ms=55323.57 | tools_ok=17/17 | answer_chars=3886

