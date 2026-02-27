# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:12:17.464168+00:00`
- Dry run: `False`
- Query: `Karl beauftragt die Ofenbau AG mit dem Einbau eines Kachelofens (EUR 9.000). Die Montage wird durch Mitarbeiter der Subunternehmerin Allerlei GmbH durchgeführt. Mängel: vergessene Ausschnittslöcher (Sichtfenster verrußt), Luftschieber schließt nicht, Herdeinsatz fällt beim Reparaturversuch aus der Halterung. Ein Sachverständiger stellt fest, dass ein kompletter Neuaufbau nötig ist (Kosten EUR 10.000 über Marktwert). Bei der Demontage wird der Ofen mit Gabelstapler statt Kran transportiert – Mitarbeiter hatten es eilig wegen Feierabend. Dabei entsteht zusätzlicher Gebäudeschaden. Welche Ansprüche hat Karl gegen die Ofenbau AG?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `7547.87`
- used_fallback: `False`

## Workstreams
1. `Identify core legal claims under Austrian civil law`
   goal: `Determine applicable claims (e.g., warranty, tort, contract) against Ofenbau AG based on factual defects and additional damage`
   tools: `['search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup', 'search_ogh_rechtssaetze']`
2. `Analyze subcontractor liability and principal responsibility`
   goal: `Clarify whether Ofenbau AG is liable for acts of Allerlei GmbH under § 1306 ABGB (vicarious liability) and relevant RS`
   tools: `['hot_rs_search', 'search_by_paragraph', 'hot_cluster_context', 'detect_clusters', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Assess damages and mitigation (Neuaufbau vs. Marktwert)`
   goal: `Evaluate whether full replacement cost (EUR 10.000) is claimable or limited to market value; examine duty to mitigate under § 1323 ABGB`
   tools: `['search_kommentar_paragraph', 'hot_index_stats', 'build_grounding_context', 'search_ogh_rechtssaetze', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `178554.77`
- tool_calls_total: `66`
- tool_calls_ok: `66`
- tool_ok_rate: `1.0`
- synth_latency_ms: `27463.02`
- final_answer_chars: `6054`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Analyze subcontractor liability and principal responsibility`: ms=49784.93 | tools_ok=18/18 | answer_chars=2861
- `Assess damages and mitigation (Neuaufbau vs. Marktwert)`: ms=61575.67 | tools_ok=25/25 | answer_chars=3644
- `Identify core legal claims under Austrian civil law`: ms=67194.17 | tools_ok=23/23 | answer_chars=2952

