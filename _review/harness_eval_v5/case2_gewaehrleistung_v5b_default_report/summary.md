# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:19:16.594045+00:00`
- Dry run: `False`
- Query: `Eine Käuferin hat eine Eigentumswohnung um 320.000 Euro gekauft, die als komplett saniert beworben wurde. Nach dem Einzug stellt sich heraus: massiver Schimmelbefall hinter den Wandverkleidungen, die Dachterrassenerweiterung ist nicht baubewilligt (Abbruchauftrag droht), und der Energieausweis wurde gefälscht. Ein Gutachten beziffert den tatsächlichen Wert auf 165.000 Euro. Der Verkäufer ist gewerblicher Immobilienhändler.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `7385.74`
- used_fallback: `False`

## Workstreams
1. `Zivilrechtliche Anspruchsgrundlagen prüfen (WGBG, BGB)`
   goal: `Identifizierung und Prüfung von Anspruchsgrundlagen gegen den gewerblichen Verkäufer (u.a. Mangelbeseitigung, Schadensersatz, Rücktritt)`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'search_by_schlagwort', 'hot_rs_lookup']`
2. `Hot-Index & RS-Kontext für Schlagwörter 'Schimmel', 'Energieausweis', 'Baubewilligung' abrufen`
   goal: `Schneller Zugriff auf aktuelle OGH-Rechtsprechung und Hot-Index-Cluster zu zentralen Sachverhaltsmerkmalen`
   tools: `['hot_index_stats', 'hot_cluster_context', 'hot_rs_lookup', 'search_by_schlagwort', 'search_by_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
3. `Kommentar-Kontext zu §§ 9, 10, 13 WGBG und § 1395 BGB herstellen`
   goal: `Systematische Einordnung der Rechtsfragen in juristischen Kommentaren (z.B. Palandt, Juslet) zur Absicherung der Argumentation`
   tools: `['search_kommentar_paragraph', 'search_kommentar_keyword', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `235411.34`
- tool_calls_total: `76`
- tool_calls_ok: `76`
- tool_ok_rate: `1.0`
- synth_latency_ms: `19689.28`
- final_answer_chars: `6082`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Hot-Index & RS-Kontext für Schlagwörter 'Schimmel', 'Energieausweis', 'Baubewilligung' abrufen`: ms=74759.91 | tools_ok=24/24 | answer_chars=3497
- `Kommentar-Kontext zu §§ 9, 10, 13 WGBG und § 1395 BGB herstellen`: ms=87024.2 | tools_ok=30/30 | answer_chars=3677
- `Zivilrechtliche Anspruchsgrundlagen prüfen (WGBG, BGB)`: ms=73627.23 | tools_ok=22/22 | answer_chars=3601

