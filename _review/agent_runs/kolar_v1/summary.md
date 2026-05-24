# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:12:41.811302+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Analysiere den Fall KOLAR gegen PFEFFER aus Sicht der betreibenden Partei (Kolar): Wirksamkeit der Hinterlegungszustellung (§17 ZustG, RSb-Hinterlegung 12.12.2025, retourniert 30.12.2025), Beweiskraft des Zustellscheins als oeffentliche Urkunde (§292 ZPO, Rueckschein), Abwehr eines erwarteten Wiedereinsetzungsantrags der Beklagten (§146 ZPO, Verschulden, auffallende Sorglosigkeit), Ortsabwesenheit pensionierte Beklagte (geb. 07.01.1940). Nenne die wichtigsten RS/TE insb. zur Beweiskraft des Zustellscheins als oeffentliche Urkunde und zur Hinterlegungszustellung.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12043` chars, `2` files, `0` OCR

## Organizer
- latency_ms: `6087.57`
- used_fallback: `False`

## Workstreams
1. `Hinterlegungszustellung gem. §17 ZustG – Wirksamkeit prüfen`
   goal: `Klärung, ob die RSb-Hinterlegung am 12.12.2025 (retourniert 30.12.2025) wirksam war, insb. unter Berücksichtigung der Altersstruktur der Beklagten (geb. 1940) und Ortsabwesenheit`
   tools: `['hot_cluster_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
2. `Beweiskraft des Zustellscheins als öffentliche Urkunde (§292 ZPO)`
   goal: `Ermittlung der Rechtsprechung zur Beweiskraft des Rücksendescheins (RSb) im Rahmen der Hinterlegungszustellung, insb. als öffentliche Urkunde iSv §292 ZPO`
   tools: `['hot_rs_search', 'hot_cluster_context', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
3. `Abwehr von Wiedereinsetzungsantrag gem. §146 ZPO – Verschulden & auffallende Sorglosigkeit`
   goal: `Identifikation von RS/TE zur Auslegung von „auffallender Sorglosigkeit“ bei pensionierten Beklagten, insb. bei Hinterlegungszustellung und Rücksendung`
   tools: `['build_grounding_context', 'detect_clusters', 'ask_gemini_zivilrecht', 'search_kommentar_paragraph', 'search_kommentar_keyword', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `50694.89`
- tool_calls_total: `38`
- tool_calls_ok: `38`
- tool_ok_rate: `1.0`
- synth_latency_ms: `30094.71`
- final_answer_chars: `6661`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Abwehr von Wiedereinsetzungsantrag gem. §146 ZPO – Verschulden & auffallende Sorglosigkeit`: ms=16386.24 | tools_ok=14/14 | answer_chars=3193
- `Beweiskraft des Zustellscheins als öffentliche Urkunde (§292 ZPO)`: ms=17100.19 | tools_ok=13/13 | answer_chars=3246
- `Hinterlegungszustellung gem. §17 ZustG – Wirksamkeit prüfen`: ms=17208.46 | tools_ok=11/11 | answer_chars=3907

