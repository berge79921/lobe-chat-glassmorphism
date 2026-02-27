# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T02:48:00.941270+00:00`
- Dry run: `False`
- Query: `Kaeuferin erwirbt eine als komplett saniert beworbene Eigentumswohnung (BJ 1965) von einem gewerblichen Immobilienhaendler um 320.000 EUR. Nach Einzug entdeckt sie: (1) massiven Schimmelbefall hinter Verkleidungen in 3 Raeumen, (2) eine nicht bewilligte Dachterrassenerweiterung mit drohendem Abbruchbescheid, (3) einen gefaelschten Energieausweis. Ein Gutachten beziffert den tatsaechlichen Verkehrswert auf 165.000 EUR. Welche Ansprueche hat die Kaeuferin?`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `remote_ssh`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `19083.55`
- used_fallback: `False`

## Workstreams
1. `Anspruchsnachweis gem. § 9 WEG iVm § 1042 ABGB (Sachmangel bei Sacheinkauf)`
   goal: `Ermitteln der Ansprüche auf Mangelbeseitigung oder Minderung/ Rücktritt aufgrund des Schimmelbefalls und des gefälschten Energieausweises im Rahmen des WEG-Sachmangelrechts`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'search_kommentar_paragraph', 'hot_rs_lookup', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
2. `Anspruch auf Schadensersatz gem. § 1231a ABGB (Gefährdungshaftung des gewerblichen Verkäufers)`
   goal: `Prüfen, ob der gewerbliche Verkäufer aufgrund der unsachgemäßen Sanierung (Schimmel) und der rechtswidrigen Dachterrassenerweiterung Schadensersatz schuldet – insb. Differenz zwischen vereinbarten und tatsächlichen Wert`
   tools: `['search_by_paragraph', 'search_ogh_rechtssaetze', 'search_kommentar_keyword', 'hot_cluster_context', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Anspruch auf Rückabwicklung / Rücktritt aufgrund arglistiger Täuschung (§§ 178, 123 ABGB)`
   goal: `Prüfen, ob die falschen Angaben (saniert, Energieausweis) arglistige Täuschung iSd § 178 ABGB darstellen und Rücktrittsmöglichkeit begründen`
   tools: `['search_by_schlagwort', 'get_rechtssatz', 'build_grounding_context', 'hot_rs_search', 'search_by_paragraph', 'search_ogh_rechtssaetze', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `244318.78`
- tool_calls_total: `70`
- tool_calls_ok: `70`
- tool_ok_rate: `1.0`
- synth_latency_ms: `20566.04`
- final_answer_chars: `5478`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anspruch auf Rückabwicklung / Rücktritt aufgrund arglistiger Täuschung (§§ 178, 123 ABGB)`: ms=70570.81 | tools_ok=17/17 | answer_chars=2912
- `Anspruch auf Schadensersatz gem. § 1231a ABGB (Gefährdungshaftung des gewerblichen Verkäufers)`: ms=92959.28 | tools_ok=31/31 | answer_chars=3307
- `Anspruchsnachweis gem. § 9 WEG iVm § 1042 ABGB (Sachmangel bei Sacheinkauf)`: ms=80788.69 | tools_ok=22/22 | answer_chars=3073

