# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T13:52:13.166220+00:00`
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
- latency_ms: `6221.06`
- used_fallback: `False`

## Workstreams
1. `Strategische Rechtsfragen & Akzessorietät in Insolvenz`
   goal: `Klärung, ob die Bürgschaftsforderung nach vollständiger Tilgung der Hauptschuld durch den Insolvenzschuldner noch bestehen bleibt (§14 IO, §7 Abs 3 EO, §25c KSchG), und ob eine Überbefriedigung vorliegt (§40 EO, §42 EO)`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Zustellungsfehler & Präklusion / Verwirkung`
   goal: `Prüfung, ob der Zustellungsfehler (§25c KSchG, §9 KSchG) zur Nichtanrechenbarkeit des Zahlungsbefehls führt, und ob eine Präklusion durch Verzug oder Verwirkung (§6 KSchG) vorliegt`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
3. `Interzession & Schadensersatz / Unrechtmäßige Exekution`
   goal: `Beurteilung, ob die Erste Bank durch Exekution gegen die Bürgschaftsforderung nach Insolvenzerfüllung eine unzulässige Überbefriedigung (§40 EO) darbringt, und ob Schadensersatzansprüche (§25c KSchG, §35 EO) geltend gemacht werden können`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `53349.85`
- tool_calls_total: `78`
- tool_calls_ok: `78`
- tool_ok_rate: `1.0`
- synth_latency_ms: `38156.37`
- final_answer_chars: `7194`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Interzession & Schadensersatz / Unrechtmäßige Exekution`: ms=21615.14 | tools_ok=34/34 | answer_chars=3348
- `Strategische Rechtsfragen & Akzessorietät in Insolvenz`: ms=16559.88 | tools_ok=21/21 | answer_chars=3380
- `Zustellungsfehler & Präklusion / Verwirkung`: ms=15174.83 | tools_ok=23/23 | answer_chars=3455

