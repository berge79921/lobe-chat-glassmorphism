# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:43:35.879174+00:00`
- Dry run: `False`
- Query: `Eine Käuferin erwirbt eine als komplett saniert beworbene Eigentumswohnung um 320.000 Euro von einem gewerblichen Verkäufer. Nach dem Einzug stellt sich heraus: massiver Schimmelbefall hinter den Wandverkleidungen, die Dachterrassen-Erweiterung hat keine Baubewilligung (droht Abbruchbescheid), und der vorgelegte Energieausweis war gefälscht. Ein Gutachten beziffert den tatsächlichen Wert der Wohnung auf 165.000 Euro. Welche Ansprüche hat die Käuferin?`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `2976.98`
- used_fallback: `False`

## Workstreams
1. `Anspruchsgrundlagen aus dem Kaufvertragsrecht (BGB)`
   goal: `Identify statutory and jurisprudential bases for claims (e.g., Mängelbeseitigung, Rücktritt, Schadensersatz) under §§ 935 ff. BGB, especially regarding hidden defects and fraudulent misrepresentation`
   tools: `['search_by_paragraph', 'get_rechtssatz', 'hot_rs_lookup', 'search_kommentar_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Gefälschter Energieausweis & irrtümliche Erklärung`
   goal: `Assess liability under §§ 117, 119 BGB (fraudulent misrepresentation / erroneous declaration) and relevance of falsified energy certificate`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'hot_cluster_context', 'search_kommentar_keyword', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Baubewilligungsmangel & bauliche Unzulässigkeit`
   goal: `Determine whether unapproved extension constitutes material defect (§ 935 BGB) or violates public order (§ 879 BGB), and implications for value depreciation`
   tools: `['search_by_schlagwort', 'hot_rs_search', 'build_grounding_context', 'search_ogh_rechtssaetze', 'search_by_paragraph', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `141303.48`
- tool_calls_total: `57`
- tool_calls_ok: `57`
- tool_ok_rate: `1.0`
- synth_latency_ms: `23134.24`
- final_answer_chars: `5350`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Anspruchsgrundlagen aus dem Kaufvertragsrecht (BGB)`: ms=41432.98 | tools_ok=15/15 | answer_chars=3647
- `Baubewilligungsmangel & bauliche Unzulässigkeit`: ms=49631.44 | tools_ok=21/21 | answer_chars=3344
- `Gefälschter Energieausweis & irrtümliche Erklärung`: ms=50239.06 | tools_ok=21/21 | answer_chars=3366

