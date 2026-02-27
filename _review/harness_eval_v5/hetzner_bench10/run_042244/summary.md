# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T04:22:44.831207+00:00`
- Dry run: `False`
- Query: `Wurstfabrikant W verkauft zwei Tiefkühlaggregate (je EUR 10.000) an Händler Z. Vereinbarung: Z wird sofort Eigentümer, Geräte bleiben bis Weiterverkauf bei W. Z verkauft ein Aggregat an Fleischer F um EUR 24.000 auf 24 Monatsraten. Zur Sicherung tritt F seine laufenden Forderungen gegen Gastwirt G an Z ab (Sicherungszession). Bei der Abholung beschädigen Zs Mitarbeiter das Aggregat mit dem Gabelstapler grob fahrlässig (EUR 10.000 Schaden). F will den Reparaturschaden gegen den Kaufpreis aufrechnen. Z verlangt volle Ratenzahlung plus die abgetretenen Forderungen. Welche Ansprüche bestehen?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3986.75`
- used_fallback: `False`

## Workstreams
1. `Eigentumsvorbehalt & Übergang des Eigentums`
   goal: `Klären, ob und wann Eigentum an den Aggregaten auf Z übergegangen ist (§§ 380, 433 BGB iVm Vereinbarung)`
   tools: `['search_by_paragraph', 'get_rechtssatz', 'hot_rs_lookup', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Sicherungszession & Abtretungsrecht`
   goal: `Prüfen Wirksamkeit der Sicherungszession der Forderungen G→F→Z und Rechte Z an den abgetretenen Forderungen (§§ 986 ff. BGB)`
   tools: `['search_by_paragraph', 'search_kommentar_paragraph', 'hot_cluster_context', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Schadensersatz & Aufrechnung bei Mangel/Beschädigung`
   goal: `Beurteilen, ob F Schadensersatzanspruch gegen Z hat (§ 280 Abs. 1, 241 Abs. 2 BGB iVm grob fahrlässige Beschädigung) und ob Aufrechnung zulässig ist`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'search_kommentar_keyword', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `318190.58`
- tool_calls_total: `65`
- tool_calls_ok: `65`
- tool_ok_rate: `1.0`
- synth_latency_ms: `19077.97`
- final_answer_chars: `5113`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Eigentumsvorbehalt & Übergang des Eigentums`: ms=79278.93 | tools_ok=29/29 | answer_chars=2966
- `Schadensersatz & Aufrechnung bei Mangel/Beschädigung`: ms=53155.35 | tools_ok=21/21 | answer_chars=3136
- `Sicherungszession & Abtretungsrecht`: ms=185756.3 | tools_ok=15/15 | answer_chars=3635

