# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T13:47:47.696722+00:00`
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
- latency_ms: `11938.1`
- used_fallback: `False`

## Workstreams
1. `Strategische Rechtsfragen & Akzessorietät in Insolvenz`
   goal: `Klärung, ob die Bürgschaft mit Erlöschen der Hauptschuld (§ 14 IO) erloschen ist und ob die spätere Exekution gegen die Bürgschaftswährin widersrechtlich ist (§ 7 Abs 3 EO, § 40 EO, § 42 EO)`
   tools: `['search_ogh_rechtssaetze', 'search_ogh_entscheidungen', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'hot_rs_lookup']`
2. `Präklusion & Zustellungsfehler als Exekutionshindernis`
   goal: `Prüfung, ob der Zahlungsbefehl aufgrund fehlender ordnungsgemäßer Zustellung (§ 17 ZPO iVm § 18c ZPO) nicht rechtskräftig geworden ist und ob eine Präklusion vorliegt (§ 25c KSchG, § 25d KSchG)`
   tools: `['hot_rs_search', 'hot_cluster_context', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
3. `Interzession & Überbefriedigung im Insolvenzkontext`
   goal: `Beurteilung, ob die Erste Bank durch die Zahlung des Hauptschuldners bereits vollständig befriedigt wurde (§ 35 EO) und ob eine interzessionelle Forderungserhaltung gegen die Bürgschaftswährin unzulässig ist`
   tools: `['build_grounding_context', 'detect_clusters', 'ask_gemini_zivilrecht', 'search_kommentar_paragraph', 'search_kommentar_keyword', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `64459.38`
- tool_calls_total: `100`
- tool_calls_ok: `100`
- tool_ok_rate: `1.0`
- synth_latency_ms: `33550.09`
- final_answer_chars: `7635`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Interzession & Überbefriedigung im Insolvenzkontext`: ms=20709.45 | tools_ok=35/35 | answer_chars=3255
- `Präklusion & Zustellungsfehler als Exekutionshindernis`: ms=21232.01 | tools_ok=33/33 | answer_chars=3130
- `Strategische Rechtsfragen & Akzessorietät in Insolvenz`: ms=22517.92 | tools_ok=32/32 | answer_chars=3428

