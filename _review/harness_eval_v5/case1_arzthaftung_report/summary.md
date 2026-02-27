# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T02:44:53.133405+00:00`
- Dry run: `False`
- Query: `Ein 45-jaehriger Tischler erleidet bei einer Knieoperation im Krankenhaus durch fehlerhafte Lagerung einen dauerhaften Peronaeusschaden (Fussheberschwaehe). Er kann seinen Beruf nicht mehr ausueben. Das Krankenhaus bestreitet den Kausalzusammenhang und verweist auf die unterzeichnete Risikoaufklaerung. Ueber Lagerungsrisiken wurde nicht aufgeklaert. Er fordert Schmerzengeld, Verdienstentgang und Feststellung der Haftung fuer Zukunftsschaeden.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `4781.79`
- used_fallback: `False`

## Workstreams
1. `Core liability framework (§§ 1295, 1298, 1299 ABGB)`
   goal: `Establish fault-based liability elements: Rechtsgutsverletzung, Kausalität, Verschulden, Rechtswidrigkeit`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Informed consent & causation defense (§ 1313a, § 1325 ABGB)`
   goal: `Assess validity of consent defense and impact of omitted specific risk disclosure on causation`
   tools: `['hot_cluster_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Damages & future loss (Schmerzengeld, Verdienstentgang, Feststellung)`
   goal: `Determine compensability, quantification, and legal basis for future damage recognition`
   tools: `['search_ogh_rechtssaetze', 'detect_clusters', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `98196.85`
- tool_calls_total: `57`
- tool_calls_ok: `57`
- tool_ok_rate: `1.0`
- synth_latency_ms: `26171.54`
- final_answer_chars: `6400`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Core liability framework (§§ 1295, 1298, 1299 ABGB)`: ms=31552.28 | tools_ok=19/19 | answer_chars=3106
- `Damages & future loss (Schmerzengeld, Verdienstentgang, Feststellung)`: ms=33253.64 | tools_ok=20/20 | answer_chars=3250
- `Informed consent & causation defense (§ 1313a, § 1325 ABGB)`: ms=33390.93 | tools_ok=18/18 | answer_chars=3776

