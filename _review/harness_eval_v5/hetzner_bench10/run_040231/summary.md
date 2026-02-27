# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T04:02:31.348429+00:00`
- Dry run: `False`
- Query: `Ein Erblasser hinterlässt Ehefrau, Sohn und Tochter. Im Testament erhält die Tochter das Eigentum an einer Wiener Innenstadtliegenschaft (Wert ca. 3-7 Mio EUR). Der Sohn erhält nur ein lebenslängliches Fruchtgenussrecht an der Hälfte dieser Liegenschaft (kein Eigentum), plus Veräußerungsverbot und Vorkaufsrecht. Die Ehefrau ist Alleinerbin. Der kapitalisierte Barwert des Fruchtgenusses liegt unter dem gesetzlichen Pflichtteil von 1/6. Der Sohn ist gleichzeitig Erwachsenenvertreter seiner Mutter (Alleinerbin). Welche Ansprüche hat der Sohn? Braucht er einen Kollisionskurator?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3602.72`
- used_fallback: `False`

## Workstreams
1. `Pflichtteilsrechtliche Prüfung des Sohnes`
   goal: `Ermitteln, ob der Sohn einen Pflichtteilsanspruch gegen die Erblasserin (Ehefrau) geltend machen kann, insbesondere wegen unzureichender Erbfolge und Kapitalisierung des Fruchtgenusses unter 1/6 des gesetzlichen Erbteils`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Vertretungskonflikt & Kollisionskuratorbedarf`
   goal: `Prüfen, ob ein Interessenkonflikt zwischen der Ehefrau (Erbin) und dem Sohn (als Erwachsenenvertreter derselben) im Hinblick auf die Ausübung des Fruchtgenusses und des Vorkaufsrechts besteht und ob ein Kollisionskurator erforderlich ist`
   tools: `['search_kommentar_paragraph', 'hot_cluster_context', 'detect_clusters', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Sachenrechtliche und Erbfolgekonstellation`
   goal: `Klären, ob das Fruchtgenussrecht (§ 457 ABGB iVm § 477 ABGB) und das Veräußerungsverbot im Testament wirksam sind, und wie sich dies auf die Erbmasse und Pflichtteilsberechtigung auswirkt`
   tools: `['search_ogh_entscheidungen', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `172476.46`
- tool_calls_total: `62`
- tool_calls_ok: `62`
- tool_ok_rate: `1.0`
- synth_latency_ms: `25001.53`
- final_answer_chars: `5631`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Pflichtteilsrechtliche Prüfung des Sohnes`: ms=63707.7 | tools_ok=18/18 | answer_chars=3194
- `Sachenrechtliche und Erbfolgekonstellation`: ms=49041.03 | tools_ok=17/17 | answer_chars=4727
- `Vertretungskonflikt & Kollisionskuratorbedarf`: ms=59727.73 | tools_ok=27/27 | answer_chars=4101

