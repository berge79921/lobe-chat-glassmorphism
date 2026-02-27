# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:10:12.849228+00:00`
- Dry run: `False`
- Query: `Ein Erblasser hinterlässt Ehefrau, Sohn und Tochter. Im Testament erhält die Tochter das Eigentum an einer Wiener Innenstadtliegenschaft (Wert ca. 3-7 Mio EUR). Der Sohn erhält nur ein lebenslängliches Fruchtgenussrecht an der Hälfte dieser Liegenschaft (kein Eigentum), plus Veräußerungsverbot und Vorkaufsrecht. Die Ehefrau ist Alleinerbin. Der kapitalisierte Barwert des Fruchtgenusses liegt unter dem gesetzlichen Pflichtteil von 1/6. Der Sohn ist gleichzeitig Erwachsenenvertreter seiner Mutter (Alleinerbin). Welche Ansprüche hat der Sohn? Braucht er einen Kollisionskurator?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `35796.72`
- used_fallback: `False`

## Workstreams
1. `Pflichtteilsrechtliche Prüfung für den Sohn`
   goal: `Ermitteln, ob der Sohn aufgrund der geringen Wertzuweisung (Fruchtgenuss < 1/6 Pflichtteil) einen Pflichtteilsanspruch geltend machen kann, insbesondere unter Berücksichtigung der Alleinerbenschaft der Mutter und seiner Funktion als Erwachsenenvertreter`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Vertretungskonflikt & Kollisionskuratorbedarf`
   goal: `Prüfen, ob ein Vertretungskonflikt im Sinne von § 774 ABGB vorliegt (Sohn vertreibt sich selbst als Erbe vs. Vertretung der Mutter als Alleinerbin), und ob ein Kollisionskurator erforderlich ist`
   tools: `['hot_cluster_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Fruchtgenussrecht vs. Pflichtteilswertung`
   goal: `Klären, ob ein lebenslängliches Fruchtgenussrecht mit Veräußerungsverbot und Vorkaufsrecht als ausreichende Abfindung für den Pflichtteil gilt (§ 780, § 781 ABGB) und ob der kapitalisierte Barwert maßgeblich ist`
   tools: `['search_ogh_entscheidungen', 'hot_rs_search', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `161737.77`
- tool_calls_total: `55`
- tool_calls_ok: `54`
- tool_ok_rate: `0.982`
- synth_latency_ms: `15536.41`
- final_answer_chars: `5027`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Fruchtgenussrecht vs. Pflichtteilswertung`: ms=50079.03 | tools_ok=13/13 | answer_chars=2953
- `Pflichtteilsrechtliche Prüfung für den Sohn`: ms=56772.67 | tools_ok=18/18 | answer_chars=2038
- `Vertretungskonflikt & Kollisionskuratorbedarf`: ms=54886.07 | tools_ok=23/24 | answer_chars=3131

