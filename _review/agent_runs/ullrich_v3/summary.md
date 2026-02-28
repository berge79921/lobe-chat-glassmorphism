# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:43:44.978935+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Analysiere den Fall ULLRICH (Invaliditaetspension gegen PVA, LG St. Poelten): Der Klaeger Mario Ullrich (geb. 1967) hat einen erlernten Beruf ausgeubt und begehrt Invaliditaetspension (§255 ASVG) bzw. in eventu Rehabilitationsgeld (§143a ASVG). Zentrale Rechtsfragen: (1) BERUFSSCHUTZ: Ueberwiegen qualifizierter Pflichtversicherungsmonate bei mehreren Berufen im 15-Jahres-Rahmen (§255 Abs 2 ASVG); ob Post-Lehrzeit Ausbildungsmonate zaehlen (nur tatsaechlich ausgebildete Berufsjahre); (2) VERWEISBARKEIT: Lohnhaelfte-Massstab, ob Verweisung auf Taetigkeiten mit Teilfaehigkeiten und aehnlichem Arbeitsumfeld beschraenkt ist (§255 Abs 3 ASVG); (3) KRANKENGELD: Anrechnung max 24 Monate bei beruflicher Kausalitaet (§255 Abs 4 ASVG); (4) REHABILITATIONSGELD: voruebergehende Invaliditaet, kein Stichtag erforderlich (§143a ASVG). Recherchiere RS zum Berufsschutz bei Ueberwiegen qualifizierter Monate, zur Post-Lehrzeit, zum Verweisungsberuf bei Invaliditaet und zum Rehabilitationsgeld bei voruebergehender Invaliditaet.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12108` chars, `3` files, `0` OCR

## Organizer
- latency_ms: `6830.05`
- used_fallback: `False`

## Workstreams
1. `Berufsschutz & qualifizierte Monate (§255 Abs 2 ASVG)`
   goal: `Ermittlung der Rechtsprechung zum Überwiegen qualifizierter Pflichtversicherungsmonate bei mehreren Berufen im 15-Jahres-Rahmen, einschließlich Post-Lehrzeit und Ausbildungsmonaten`
   tools: `['search_ogh_rechtssaetze', 'search_ogh_entscheidungen', 'get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'hot_rs_lookup']`
2. `Verweisbarkeit & Lohnhelfe-Massstab (§255 Abs 3 ASVG)`
   goal: `Klärung der Verweisbarkeitsgrenzen bei Invalidität, insbesondere Tätigkeiten mit Teilfähigkeiten und ähnlichem Arbeitsumfeld`
   tools: `['hot_rs_search', 'hot_cluster_context', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
3. `Krankengeld & Anrechnungsfrist (§255 Abs 4 ASVG)`
   goal: `Recherche zur max. 24-monatigen Anrechnung bei beruflicher Kausalität und Berufsunfähigkeit`
   tools: `['build_grounding_context', 'detect_clusters', 'ask_gemini_zivilrecht', 'search_kommentar_paragraph', 'search_kommentar_keyword', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `53746.47`
- tool_calls_total: `73`
- tool_calls_ok: `73`
- tool_ok_rate: `1.0`
- synth_latency_ms: `34092.58`
- final_answer_chars: `7557`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Berufsschutz & qualifizierte Monate (§255 Abs 2 ASVG)`: ms=18071.2 | tools_ok=27/27 | answer_chars=3677
- `Krankengeld & Anrechnungsfrist (§255 Abs 4 ASVG)`: ms=19042.28 | tools_ok=25/25 | answer_chars=3066
- `Verweisbarkeit & Lohnhelfe-Massstab (§255 Abs 3 ASVG)`: ms=16632.99 | tools_ok=21/21 | answer_chars=3483

