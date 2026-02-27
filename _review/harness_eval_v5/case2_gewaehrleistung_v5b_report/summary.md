# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:14:08.575052+00:00`
- Dry run: `False`
- Query: `Eine Käuferin hat eine Eigentumswohnung um 320.000 Euro gekauft, die als komplett saniert beworben wurde. Nach dem Einzug stellt sich heraus: massiver Schimmelbefall hinter den Wandverkleidungen, die Dachterrassenerweiterung ist nicht baubewilligt (Abbruchauftrag droht), und der Energieausweis wurde gefälscht. Ein Gutachten beziffert den tatsächlichen Wert auf 165.000 Euro. Der Verkäufer ist gewerblicher Immobilienhändler.`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `6881.34`
- used_fallback: `False`

## Workstreams
1. `Zivilrechtliche Gewährleistung & Mängelbeseitigung (§§ 934 ff. ABGB)`
   goal: `Ermittlung der rechtlichen Ansprüche der Käuferin gegen den gewerblichen Verkäufer auf Nacherfüllung, Minderung oder Schadensersatz aufgrund von Sachmängeln und Rechtsmängeln`
   tools: `['search_by_paragraph', 'get_rechtssatz', 'hot_rs_lookup', 'search_kommentar_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Täuschung & arglistige Verschweigen (§§ 178, 179 ABGB)`
   goal: `Prüfung, ob der Verkäufer durch falsche Angaben (Energieausweis, Sanierungsstatus, Baubewilligung) vorsätzlich getäuscht hat und ob dies zur Anfechtung oder Schadensersatzpflicht führt`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'hot_rs_search', 'search_kommentar_keyword', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Gewerblicher Verkäufer – besonderer Schutz (WBO, UWG, Gewährleistungserklärung)`
   goal: `Ermittlung zusätzlicher Anspruchsgrundlagen durch gewerbliche Tätigkeit des Verkäufers (z. B. Gewährleistungserklärung nach WBO, unlauterer Wettbewerb nach UWG)`
   tools: `['search_by_schlagwort', 'hot_index_stats', 'hot_cluster_context', 'build_grounding_context', 'search_by_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `244871.64`
- tool_calls_total: `60`
- tool_calls_ok: `60`
- tool_ok_rate: `1.0`
- synth_latency_ms: `20164.03`
- final_answer_chars: `5921`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Gewerblicher Verkäufer – besonderer Schutz (WBO, UWG, Gewährleistungserklärung)`: ms=101802.65 | tools_ok=24/24 | answer_chars=3972
- `Täuschung & arglistige Verschweigen (§§ 178, 179 ABGB)`: ms=68202.17 | tools_ok=18/18 | answer_chars=4117
- `Zivilrechtliche Gewährleistung & Mängelbeseitigung (§§ 934 ff. ABGB)`: ms=74866.82 | tools_ok=18/18 | answer_chars=4166

