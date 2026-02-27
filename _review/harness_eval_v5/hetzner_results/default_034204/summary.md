# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T03:42:04.130429+00:00`
- Dry run: `False`
- Query: `Ein Tischlermeister wird wegen Knieproblemen operiert. Bei der OP kommt es zu einem Lagerungsfehler, der zu einer Peroneusschädigung (Nervenschaden am Bein) führt. Folgen: Dauerschmerzen, Berufsunfähigkeit als Tischler, lebenslange Einschränkungen. Der Patient hatte nur ein allgemeines OP-Aufklärungsformular unterschrieben, das Lagerungsrisiken nicht erwähnt. Welche Ansprüche hat der Patient gegen das Krankenhaus und den Arzt?`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3374.55`
- used_fallback: `False`

## Workstreams
1. `Haftungsansprüche gegen Arzt/Krankenhaus (medizinische Behandlung)`
   goal: `Ermitteln von Anspruchsgrundlagen aus § 1328 ABGB (Schadensersatz bei Verletzung der Sorgfaltspflicht) und § 634a BGB (Rechtsfolgen beim Behandlungsfehler), insbesondere bei fehlender spezifischer Aufklärung über Lagerungsrisiken`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup', 'search_by_schlagwort']`
2. `Sozialversicherungsansprüche (Invaliditäts- und Krankengeld)`
   goal: `Prüfen von Ansprüchen auf Invaliditätsrente (IV), Krankengeld oder Rehabilitation im Zusammenhang mit Berufsunfähigkeit nach medizinischem Behandlungsfehler`
   tools: `['search_by_schlagwort', 'search_kommentar_keyword', 'build_grounding_context', 'hot_cluster_context', 'search_by_paragraph', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Aufklärungsfehler und informierte Einwilligung`
   goal: `Klären, ob das allgemeine OP-Aufklärungsformular (ohne Erwähnung von Lagerungsrisiken) einen Aufklärungsfehler iSd § 634a Abs 2 BGB darstellt und welche Rechtsfolgen daraus resultieren`
   tools: `['search_kommentar_paragraph', 'hot_rs_search', 'detect_clusters', 'ask_gemini_zivilrecht', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `107852.46`
- tool_calls_total: `73`
- tool_calls_ok: `73`
- tool_ok_rate: `1.0`
- synth_latency_ms: `20089.52`
- final_answer_chars: `5338`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Aufklärungsfehler und informierte Einwilligung`: ms=41274.87 | tools_ok=27/27 | answer_chars=3443
- `Haftungsansprüche gegen Arzt/Krankenhaus (medizinische Behandlung)`: ms=28470.46 | tools_ok=21/21 | answer_chars=3452
- `Sozialversicherungsansprüche (Invaliditäts- und Krankengeld)`: ms=38107.13 | tools_ok=25/25 | answer_chars=3662

