# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T02:50:27.289484+00:00`
- Dry run: `False`
- Query: `Eine einkommenslose Ehefrau hat fuer den Geschaeftskredit ihres Mannes eine Hoechstbetragsburgschaft ueber EUR 150.000 uebernommen. Die Bank hat nicht ueber die wirtschaftliche Lage des Mannes aufgeklaert (Verletzung §25c KSchG). Der Kredit ist notleidend, die Bank hat bereits Fahrnisexekution beantragt. Die Ehefrau hat keinen Einspruch erhoben (Versaeumungsurteil). Welche Verteidigungsmoeglichkeiten bestehen noch?`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `6193.67`
- used_fallback: `False`

## Workstreams
1. `KSchG-Vorgaben prüfen (§§ 6, 9, 25c, 25d)`
   goal: `Klären, ob die Bank durch Verletzung von § 25c KSchG (Informationspflicht bei Krediten an Verbraucher) die Wirksamkeit der Bürgschaft beeinträchtigt hat – insb. ob die Bürgschaft aufgrund Verbraucherschutzvorschriften anfechtbar oder nichtig ist`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Rechtsprechung & Kommentar zu Bürgschaft & Verbraucherschutz`
   goal: `Ermitteln, wie OGH und Literatur mit Bürgschaften durch einkommensschwache Ehegatten umgehen – insb. bei Verletzung von § 25c KSchG und Versäumungsurteil`
   tools: `['search_ogh_entscheidungen', 'search_ogh_rechtssaetze', 'hot_cluster_context', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Exekutionsrechtliche Hebel & Versäumungsurteil`
   goal: `Prüfen, ob noch exekutionsrechtliche Mittel (z. B. Widerspruch gegen die Exekution, § 15 ZPO iVm Versäumungsurteil) oder Revisionsweg (§ 279 ZPO) offenstehen – insbesondere bei Vorliegen eines formellen Rechtsmittelsgrundes (z. B. Verletzung zwingenden Rechts)`
   tools: `['search_ogh_entscheidungen', 'hot_index_stats', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `256412.14`
- tool_calls_total: `59`
- tool_calls_ok: `59`
- tool_ok_rate: `1.0`
- synth_latency_ms: `19707.41`
- final_answer_chars: `5833`
- citation_gate_mode: `enforce`
- citation_gate_applied: `False`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Exekutionsrechtliche Hebel & Versäumungsurteil`: ms=91009.26 | tools_ok=22/22 | answer_chars=4022
- `KSchG-Vorgaben prüfen (§§ 6, 9, 25c, 25d)`: ms=85158.27 | tools_ok=21/21 | answer_chars=3671
- `Rechtsprechung & Kommentar zu Bürgschaft & Verbraucherschutz`: ms=80244.61 | tools_ok=16/16 | answer_chars=3825

