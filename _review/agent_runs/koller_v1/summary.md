# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-28T14:28:00.254019+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Erstelle eine kompakte anwaltliche Ersteinschaetzung zum Fall Koller gegen Baumgartner: Baumgartner (Beklagter) wird von RA Dr. Koller auf Werklohn/Honorar EUR 18.114,83 s.A. geklagt. Bedingter Vergleich (§204 ZPO) wurde widerrufen (DAS-Deckungsverweigerung). Pruefe: Werkvertrag vs Dienstvertrag (§1165 ABGB vs §1151 ABGB), Bevoellmaechtigung (§1002 ABGB, Ermaechtigung), Widerruf bedingter Vergleich (§204 ZPO), DAS-Deckung (§158k VersVG, ARB). Nenne die wichtigsten RS/TE.`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `10533` chars, `2` files, `0` OCR

## Organizer
- latency_ms: `4505.81`
- used_fallback: `False`

## Workstreams
1. `Werkvertrag vs. Dienstvertrag (§§ 1165, 1151 ABGB)`
   goal: `Klärung der rechtlichen Einordnung der Tätigkeit von RA Koller – entscheidend für Anspruchsgrundlage (Werklohn vs. Dienstlohn)`
   tools: `['get_rechtssatz', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'hot_rs_lookup']`
2. `Bevollmächtigung & Ermächtigung (§ 1002 ABGB)`
   goal: `Prüfung, ob RA Berger rechtskräftig bevollmächtigt war, den bedingten Vergleich widerrufen zu können – Voraussetzung für wirksamen Widerruf`
   tools: `['hot_rs_search', 'hot_cluster_context', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz']`
3. `Widerruf bedingter Vergleich (§ 204 ZPO) & DAS-Deckung (§ 158k VersVG)`
   goal: `Rechtliche Bewertung der Widerrufsfrist, -wirkung und der Rolle der DAS-Deckungsverweigerung; Prüfung, ob Deckung für Fortführung des Verfahrens noch möglich`
   tools: `['build_grounding_context', 'detect_clusters', 'ask_gemini_zivilrecht', 'search_kommentar_paragraph', 'search_kommentar_keyword', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `53527.51`
- tool_calls_total: `61`
- tool_calls_ok: `61`
- tool_ok_rate: `1.0`
- synth_latency_ms: `41466.74`
- final_answer_chars: `7621`
- citation_gate_mode: `repair`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Bevollmächtigung & Ermächtigung (§ 1002 ABGB)`: ms=17235.89 | tools_ok=20/20 | answer_chars=3159
- `Werkvertrag vs. Dienstvertrag (§§ 1165, 1151 ABGB)`: ms=14103.43 | tools_ok=16/16 | answer_chars=3335
- `Widerruf bedingter Vergleich (§ 204 ZPO) & DAS-Deckung (§ 158k VersVG)`: ms=22188.19 | tools_ok=25/25 | answer_chars=2754

