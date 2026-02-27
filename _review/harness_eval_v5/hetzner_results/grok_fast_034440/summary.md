# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:44:40.897418+00:00`
- Dry run: `False`
- Query: `Eine Käuferin erwirbt eine als komplett saniert beworbene Eigentumswohnung um 320.000 Euro von einem gewerblichen Verkäufer. Nach dem Einzug stellt sich heraus: massiver Schimmelbefall hinter den Wandverkleidungen, die Dachterrassen-Erweiterung hat keine Baubewilligung (droht Abbruchbescheid), und der vorgelegte Energieausweis war gefälscht. Ein Gutachten beziffert den tatsächlichen Wert der Wohnung auf 165.000 Euro. Welche Ansprüche hat die Käuferin?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3485.89`
- used_fallback: `False`

## Workstreams
1. `Anspruchsgrundlagen aus dem Kaufrecht (BGB)`
   goal: `Identify core claims under Austrian civil law (BGB) for defective performance, fraud, and warranty (Gewährleistung) against a commercial seller`
   tools: `['search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup', 'search_ogh_rechtssaetze']`
2. `Fehlende Baubewilligung & rechtliche Unzulänglichkeit`
   goal: `Assess claims related to unauthorized construction (Dachterrassen-Erweiterung), potential nullity or rescission under public law constraints affecting title`
   tools: `['search_by_schlagwort', 'hot_cluster_context', 'search_ogh_entscheidungen', 'build_grounding_context', 'search_by_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Gefälschter Energieausweis & Täuschung (arglistige Verschweigung)`
   goal: `Evaluate fraud (§ 147 ABGB), misrepresentation, and liability for false statements under commercial seller obligations`
   tools: `['search_by_paragraph', 'search_kommentar_keyword', 'hot_rs_search', 'detect_clusters', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `156672.84`
- tool_calls_total: `66`
- tool_calls_ok: `66`
- tool_ok_rate: `1.0`
- synth_latency_ms: `20677.53`
- final_answer_chars: `5755`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anspruchsgrundlagen aus dem Kaufrecht (BGB)`: ms=51685.8 | tools_ok=23/23 | answer_chars=3397
- `Fehlende Baubewilligung & rechtliche Unzulänglichkeit`: ms=65755.79 | tools_ok=25/25 | answer_chars=2967
- `Gefälschter Energieausweis & Täuschung (arglistige Verschweigung)`: ms=39231.25 | tools_ok=18/18 | answer_chars=3368

