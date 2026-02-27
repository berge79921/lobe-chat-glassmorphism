# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:08:02.322915+00:00`
- Dry run: `False`
- Query: `Unternehmer X betreibt Weinanbau in Wien. Er bestellt bei Großhändler Y ein Harz zur Ertragssteigerung der Rebstöcke. Das Harz wurde von Chemiefabrik Z in Linz hergestellt. Nach Aufbringung im Mai werden bis September sämtliche Rebstöcke zerstört. Neubepflanzungskosten: 500.000 Euro. X verlangt von Y vollen Schadenersatz. Y wendet ein, das Harz sei von Z fehlerhaft produziert worden. Welche Ansprüche hat X gegen Y und Z? Greift das PHG?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `26134.24`
- used_fallback: `False`

## Workstreams
1. `Anspruchsgrundlagen gegen Y (Verkäufer)`
   goal: `Ermitteln, ob X Anspruch auf Schadenersatz gegen Y gemäß Kaufrecht, insb. Mangelhaftigkeit (§ 936 ff. ABGB iVm § 1295, § 1298, § 1299 ABGB) und/oder Geschäftsuntauglichkeit (§ 1313a ABGB) hat`
   tools: `['search_ogh_entscheidungen', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
2. `Anspruchsgrundlagen gegen Z (Hersteller)`
   goal: `Prüfen, ob X Anspruch gegen Z auf Schadenersatz gemäß Produkthaftungsgesetz (PHG) oder Delikt (§ 1325 ABGB) hat, insb. bei fehlerhafter Herstellung`
   tools: `['search_ogh_rechtssaetze', 'hot_cluster_context', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'hot_rs_lookup']`
3. `PHG-Anwendbarkeit & Haftungsausschluss durch Drittverschulden`
   goal: `Klären, ob PHG greift (Herstellerdefinition, Produktbegriff, Haftungsausschluss bei Zulassung/Entwicklung), und ob Y sich auf Verschulden des Herstellers (Z) berufen kann`
   tools: `['hot_rs_search', 'search_kommentar_paragraph', 'search_kommentar_keyword', 'detect_clusters', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `176298.35`
- tool_calls_total: `60`
- tool_calls_ok: `59`
- tool_ok_rate: `0.983`
- synth_latency_ms: `27164.15`
- final_answer_chars: `6087`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anspruchsgrundlagen gegen Y (Verkäufer)`: ms=62541.89 | tools_ok=17/17 | answer_chars=4569
- `Anspruchsgrundlagen gegen Z (Hersteller)`: ms=50026.91 | tools_ok=15/16 | answer_chars=3191
- `PHG-Anwendbarkeit & Haftungsausschluss durch Drittverschulden`: ms=63729.55 | tools_ok=27/27 | answer_chars=3344

