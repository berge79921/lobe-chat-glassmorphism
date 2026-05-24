# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T13:17:17.520682+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Fasse den Fall CARMEN als strategische anwaltliche Ersteinschaetzung zusammen: welche 2-3 Rechtsfragen sind entscheidend? Wie sind EO-/Praeklusion-/Interzessions-Aspekte zu priorisieren? §14 IO (Akzessorietaet in Insolvenz), §7 Abs 3 EO, §25c KSchG, §40 EO, §35 EO, §42 EO. Welche Schritte bringen kurzfristig den groessten Nutzen? Nenne die wichtigsten RS/TE zur Absicherung.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12152` chars, `5` files, `0` OCR

## Organizer
- latency_ms: `5482.66`
- used_fallback: `False`

## Workstreams
1. `Strategische Rechtsfragen & Akzessorietät in Insolvenz`
   goal: `Klärung, ob die Exekution gegen die Mandantin nach vollständiger Tilgung der Insolvenzforderung durch den Hauptschuldner rechtswidrig ist (§14 IO, §7 Abs 3 EO, §25c KSchG)`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Präklusion & Zustellungsfehler als Exekutionshindernis`
   goal: `Prüfung, ob der Zahlungsbefehl aufgrund fehlender wirksamer Zustellung (§40 EO, §42 EO) oder Präklusion (§35 EO) nicht mehr vollstreckt werden darf`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
3. `Interzession & Verbot der Überbefriedigung`
   goal: `Beurteilung, ob die Erste Bank durch die Exekution gegen die Mandantin nach Tilgung der Insolvenzforderung eine unzulässige Überbefriedigung erhält (§25d KSchG, EO-Richtlinie der Interzession)`
   tools: `['hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `56507.2`
- tool_calls_total: `74`
- tool_calls_ok: `74`
- tool_ok_rate: `1.0`
- synth_latency_ms: `49153.32`
- final_answer_chars: `7668`
- citation_gate_mode: `repair`
- citation_gate_applied: `False`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Interzession & Verbot der Überbefriedigung`: ms=18914.1 | tools_ok=27/27 | answer_chars=3347
- `Präklusion & Zustellungsfehler als Exekutionshindernis`: ms=17541.92 | tools_ok=22/22 | answer_chars=3470
- `Strategische Rechtsfragen & Akzessorietät in Insolvenz`: ms=20051.18 | tools_ok=25/25 | answer_chars=3444

