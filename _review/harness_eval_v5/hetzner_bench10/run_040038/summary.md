# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T04:00:38.210975+00:00`
- Dry run: `False`
- Query: `Unternehmer X betreibt Weinanbau in Wien. Er bestellt bei Großhändler Y ein Harz zur Ertragssteigerung der Rebstöcke. Das Harz wurde von Chemiefabrik Z in Linz hergestellt. Nach Aufbringung im Mai werden bis September sämtliche Rebstöcke zerstört. Neubepflanzungskosten: 500.000 Euro. X verlangt von Y vollen Schadenersatz. Y wendet ein, das Harz sei von Z fehlerhaft produziert worden. Welche Ansprüche hat X gegen Y und Z? Greift das PHG?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `6676.2`
- used_fallback: `False`

## Workstreams
1. `Anspruchsgrundlagen gegen Y (Verkäufer)`
   goal: `Ermitteln, ob X Anspruch auf Schadenersatz gegen Y gemäß Kaufrecht, Mangelhaftersatzpflicht und/oder PHG hat`
   tools: `['hot_rs_lookup', 'search_kommentar_paragraph', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
2. `Anspruchsgrundlagen gegen Z (Hersteller)`
   goal: `Prüfen, ob X Anspruch gegen Z aufgrund Herstellerschutz (PHG), Delikt (§ 1321 ABGB) oder Produkthaftung hat`
   tools: `['search_ogh_entscheidungen', 'hot_rs_search', 'get_rechtssatz', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'hot_rs_lookup']`
3. `PHG-Anwendbarkeit und Haftungsausschluss`
   goal: `Klären, ob PHG greift (Produktdefinition, Inverkehrbringen, Verbraucherbezug) und ob Y/Z Haftungsausschlüsse geltend machen können`
   tools: `['hot_index_stats', 'hot_cluster_context', 'detect_clusters', 'ask_gemini_zivilrecht', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `151696.11`
- tool_calls_total: `57`
- tool_calls_ok: `57`
- tool_ok_rate: `1.0`
- synth_latency_ms: `20608.29`
- final_answer_chars: `4675`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anspruchsgrundlagen gegen Y (Verkäufer)`: ms=53028.75 | tools_ok=23/23 | answer_chars=3050
- `Anspruchsgrundlagen gegen Z (Hersteller)`: ms=45090.95 | tools_ok=19/19 | answer_chars=3318
- `PHG-Anwendbarkeit und Haftungsausschluss`: ms=53576.41 | tools_ok=15/15 | answer_chars=4586

