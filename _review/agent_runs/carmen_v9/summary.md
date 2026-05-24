# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T13:57:02.757024+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Fasse den Fall CARMEN als strategische anwaltliche Ersteinschaetzung zusammen: welche 2-3 Rechtsfragen sind entscheidend? Wie sind EO-/Praeklusion-/Interzessions-Aspekte zu priorisieren? §14 IO (Akzessorietaet in Insolvenz), §7 Abs 3 EO, §25c KSchG, §40 EO, §35 EO, §42 EO. Welche Schritte bringen kurzfristig den groessten Nutzen? Nenne die wichtigsten RS/TE zur Absicherung.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12043` chars, `2` files, `0` OCR

## Organizer
- latency_ms: `5391.78`
- used_fallback: `False`

## Workstreams
1. `Strategische Rechtsfragen & Akzessoriät in Insolvenz`
   goal: `Klärung, ob die Bürgschaftsforderung nach vollständiger Tilgung der Hauptschuld durch den Insolvenzschuldner noch bestehen bleibt (§14 IO, §7 Abs 3 EO, §25c KSchG)`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Zustellungsfehler & Präklusion / Verwirkung`
   goal: `Prüfung, ob der Zustellungsfehler (§40 EO, §35 EO) zur Nichtanrechenbarkeit der Fristen führt und ob eine Präklusion der Einwendungen vorliegt (§42 EO, §9 KSchG)`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
3. `Interzession, Überbefriedigung & KSchG-Schutz`
   goal: `Beurteilung, ob die Erste Bank durch Zahlung des Insolvenzschuldners bereits vollständig befriedigt wurde (§25c KSchG, §6 KSchG) und ob eine interzessionelle Überbefriedigung vorliegt`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `61314.85`
- tool_calls_total: `82`
- tool_calls_ok: `82`
- tool_ok_rate: `1.0`
- synth_latency_ms: `46646.59`
- final_answer_chars: `8038`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Interzession, Überbefriedigung & KSchG-Schutz`: ms=19883.27 | tools_ok=27/27 | answer_chars=3678
- `Strategische Rechtsfragen & Akzessoriät in Insolvenz`: ms=20226.78 | tools_ok=25/25 | answer_chars=3776
- `Zustellungsfehler & Präklusion / Verwirkung`: ms=21204.8 | tools_ok=30/30 | answer_chars=3254

