# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:21:47.881792+00:00`
- Dry run: `False`
- Query: `In einer Wohnungseigentumsanlage entdeckt ein Eigentümer (Top 16, Anteil 174/2742) einen aktiven Ölaustritt an der gemeinsamen Öltankanlage im Heizraum. Er ergreift Sofortmaßnahmen (Dokumentation, Öl auffangen), meldet den Schaden schriftlich an die Hausverwaltung mit Fotodokumentation und setzt eine Nachfrist. Die Hausverwaltung reagiert nicht substantiell. Die Öltankanlage ist allgemeiner Teil der Liegenschaft (§ 2 Abs 4 WEG). Welche Ansprüche hat der Eigentümer gegen die Hausverwaltung und die Eigentümergemeinschaft? Muss die HV sofort handeln (§ 20 Abs 2 WEG)?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `12870.58`
- used_fallback: `False`

## Workstreams
1. `Legal Framework & Hot Index Context`
   goal: `Establish binding legal framework and identify relevant OGH rulings and commentary clusters on maintenance obligations in Wohnungseigentum, especially regarding common facilities and delayed response by management.`
   tools: `['hot_index_stats', 'hot_rs_search', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
2. `Claim Analysis & Grounding Context`
   goal: `Determine actionable claims (Schadensersatz, Erfüllung, Unterlassung) against HV and Eigentümergemeinschaft based on factual scenario and statutory duties, using expert synthesis.`
   tools: `['build_grounding_context', 'detect_clusters', 'ask_gemini_zivilrecht', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'hot_rs_lookup']`
3. `Immediate Obligation Check (§ 20 Abs 2 WEG)`
   goal: `Clarify whether § 20 Abs 2 WEG imposes *immediate* duty on Hausverwaltung to act upon discovery of damage to common property, especially environmental hazard.`
   tools: `['hot_rs_lookup', 'hot_cluster_context', 'search_ogh_entscheidungen', 'search_ogh_rechtssaetze', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `196692.82`
- tool_calls_total: `75`
- tool_calls_ok: `75`
- tool_ok_rate: `1.0`
- synth_latency_ms: `21830.99`
- final_answer_chars: `5578`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Claim Analysis & Grounding Context`: ms=67378.97 | tools_ok=24/24 | answer_chars=4268
- `Immediate Obligation Check (§ 20 Abs 2 WEG)`: ms=71562.12 | tools_ok=26/26 | answer_chars=3033
- `Legal Framework & Hot Index Context`: ms=57751.73 | tools_ok=25/25 | answer_chars=4063

