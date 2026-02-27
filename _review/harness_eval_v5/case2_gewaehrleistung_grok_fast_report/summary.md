# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T02:55:40.859888+00:00`
- Dry run: `False`
- Query: `Kaeuferin erwirbt eine als komplett saniert beworbene Eigentumswohnung (BJ 1965) von einem gewerblichen Immobilienhaendler um 320.000 EUR. Nach Einzug entdeckt sie: (1) massiven Schimmelbefall hinter Verkleidungen in 3 Raeumen, (2) eine nicht bewilligte Dachterrassenerweiterung mit drohendem Abbruchbescheid, (3) einen gefaelschten Energieausweis. Ein Gutachten beziffert den tatsaechlichen Verkehrswert auf 165.000 EUR. Welche Ansprueche hat die Kaeuferin?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `4674.17`
- used_fallback: `False`

## Workstreams
1. `Anspruchsnachweis gem. § 9 ABGB (Sachmangel / Gewährleistung)`
   goal: `Ermitteln der Anspruchsgrundlagen bei Sachmängeln bei Kaufverträgen mit gewerblichen Verkäufern, insb. bei verdeckten Mängeln und falschen Angaben zur Beschaffenheit`
   tools: `['search_by_paragraph', 'search_kommentar_paragraph', 'hot_rs_search', 'get_rechtssatz', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'hot_rs_lookup']`
2. `Anspruchsnachweis gem. §§ 17, 18 KSchG (Konsumentenschutz bei Fern- / Haustürgeschäften)`
   goal: `Prüfen, ob KSchG-Ansprüche (z.B. Widerruf, Schadensersatz) aufgrund irreführender Angaben (z.B. Energieausweis, Sanierungsstatus) greifen`
   tools: `['search_by_paragraph', 'search_kommentar_keyword', 'search_ogh_rechtssaetze', 'hot_rs_lookup', 'search_by_schlagwort', 'get_rechtssatz']`
3. `Anspruchsnachweis gem. § 1042 ABGB (Vermögensschaden durch arglistige Verschweigen / § 1059 ABGB)`
   goal: `Prüfen auf Schadensersatzanspruch bei arglistiger Verschweigung von Mängeln (Schimmel, nicht genehmigte Bauwerke) und Fälschung des Energieausweises`
   tools: `['search_by_paragraph', 'hot_cluster_context', 'detect_clusters', 'build_grounding_context', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `256642.74`
- tool_calls_total: `85`
- tool_calls_ok: `85`
- tool_ok_rate: `1.0`
- synth_latency_ms: `17011.99`
- final_answer_chars: `5629`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anspruchsnachweis gem. § 1042 ABGB (Vermögensschaden durch arglistige Verschweigen / § 1059 ABGB)`: ms=106063.99 | tools_ok=31/31 | answer_chars=4316
- `Anspruchsnachweis gem. § 9 ABGB (Sachmangel / Gewährleistung)`: ms=68196.32 | tools_ok=26/26 | answer_chars=2008
- `Anspruchsnachweis gem. §§ 17, 18 KSchG (Konsumentenschutz bei Fern- / Haustürgeschäften)`: ms=82382.43 | tools_ok=28/28 | answer_chars=2411

