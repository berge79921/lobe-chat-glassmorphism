# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:13:04.661086+00:00`
- Dry run: `False`
- Query: `Eine einkommenslose Ehefrau hat fuer den Geschaeftskredit ihres Mannes eine Hoechstbetragsburgschaft ueber EUR 150.000 uebernommen. Die Bank hat nicht ueber die wirtschaftliche Lage des Mannes aufgeklaert (Verletzung §25c KSchG). Der Kredit ist notleidend, die Bank hat bereits Fahrnisexekution beantragt. Die Ehefrau hat keinen Einspruch erhoben (Versaeumungsurteil). Welche Verteidigungsmoeglichkeiten bestehen noch?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3408.5`
- used_fallback: `False`

## Workstreams
1. `KSchG-Vorgaben prüfen (§§ 6, 9, 25c, 25d)`
   goal: `Klären, ob die Bank durch Nicht-Erfüllung der Aufklärungspflicht nach § 25c KSchG die Wirksamkeit der Bürgschaft beeinträchtigt hat; Prüfung der Schutznormcharakteristik und Folgen bei Verletzung`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Bürgschaftsrechtliche Verteidigungsszenarien`
   goal: `Ermitteln, ob die Bürgschaft aufgrund mangelnder Kenntnisnahme der wirtschaftlichen Lage (§ 25c KSchG) oder aufgrund Versäumnisurteil-Defiziten anfechtbar ist; Prüfung auf Unwirksamkeit nach § 9 KSchG iVm § 25c KSchG`
   tools: `['hot_cluster_context', 'detect_clusters', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Exekutionsrechtliche Hebel & OGH-Rechtsprechung`
   goal: `Prüfen, ob die bereits eingeleitete Fahrnisexekution juristisch gestoppt oder eingeschränkt werden kann (z. B. durch Aufschub, Prüfung der Exekutionsvoraussetzungen iVm KSchG)`
   tools: `['search_ogh_entscheidungen', 'search_ogh_rechtssaetze', 'hot_index_stats', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `199226.79`
- tool_calls_total: `54`
- tool_calls_ok: `54`
- tool_ok_rate: `1.0`
- synth_latency_ms: `20399.11`
- final_answer_chars: `5703`
- citation_gate_mode: `enforce`
- citation_gate_applied: `False`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Bürgschaftsrechtliche Verteidigungsszenarien`: ms=66208.03 | tools_ok=17/17 | answer_chars=3876
- `Exekutionsrechtliche Hebel & OGH-Rechtsprechung`: ms=62276.45 | tools_ok=16/16 | answer_chars=4521
- `KSchG-Vorgaben prüfen (§§ 6, 9, 25c, 25d)`: ms=70742.31 | tools_ok=21/21 | answer_chars=4532

