# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:03:19.023980+00:00`
- Dry run: `False`
- Query: `Eine einkommenslose Ehefrau hat fuer den Geschaeftskredit ihres Mannes eine Hoechstbetragsburgschaft ueber EUR 150.000 uebernommen. Die Bank hat nicht ueber die wirtschaftliche Lage des Mannes aufgeklaert (Verletzung §25c KSchG). Der Kredit ist notleidend, die Bank hat bereits Fahrnisexekution beantragt. Die Ehefrau hat keinen Einspruch erhoben (Versaeumungsurteil). Welche Verteidigungsmoeglichkeiten bestehen noch?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `16733.28`
- used_fallback: `False`

## Workstreams
1. `KSchG-Vorgaben prüfen (§§ 6, 9, 25c, 25d)`
   goal: `Klären, ob die Bank durch Verletzung von § 25c KSchG (Informationspflicht bei Krediten an Verbraucher) die Wirksamkeit der Bürgschaft beeinträchtigt hat – insb. ob die Bürgschaft nach § 6 KSchG oder § 9 KSchG anfechtbar/nichtig ist`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Bürgschaftsrechtliche Verteidigungsszenarien`
   goal: `Identifikation von Verteidigungsmöglichkeiten gegen die Durchsetzung der Bürgschaft (z.B. sittenwidrige Konditionen nach § 879 ABGB iVm KSchG, Versäumungsurteil anfechtbar?, Exekutionserlass widersprechen)`
   tools: `['search_ogh_entscheidungen', 'hot_cluster_context', 'detect_clusters', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Exekutionsrechtliche Hebel prüfen`
   goal: `Prüfen, ob die bereits beantragte Fahrnisexekution rechtswidrig ist (z.B. aufgrund unwirksamer Vollstreckungstitel oder Verletzung von KSchG-Vorgaben) und ob Widerspruch nach § 15 ZPO oder Antrag auf Aufhebung des Exekutionserlasses möglich ist`
   tools: `['search_ogh_rechtssaetze', 'hot_index_stats', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `194376.15`
- tool_calls_total: `54`
- tool_calls_ok: `54`
- tool_ok_rate: `1.0`
- synth_latency_ms: `16469.78`
- final_answer_chars: `6100`
- citation_gate_mode: `enforce`
- citation_gate_applied: `False`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Bürgschaftsrechtliche Verteidigungsszenarien`: ms=64507.27 | tools_ok=19/19 | answer_chars=4867
- `Exekutionsrechtliche Hebel prüfen`: ms=68875.29 | tools_ok=18/18 | answer_chars=4797
- `KSchG-Vorgaben prüfen (§§ 6, 9, 25c, 25d)`: ms=60993.59 | tools_ok=17/17 | answer_chars=4365

