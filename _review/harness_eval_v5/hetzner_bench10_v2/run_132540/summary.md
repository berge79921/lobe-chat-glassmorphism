# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:25:40.473140+00:00`
- Dry run: `False`
- Query: `Wurstfabrikant W verkauft zwei Tiefkühlaggregate (je EUR 10.000) an Händler Z. Vereinbarung: Z wird sofort Eigentümer, Geräte bleiben bis Weiterverkauf bei W. Z verkauft ein Aggregat an Fleischer F um EUR 24.000 auf 24 Monatsraten. Zur Sicherung tritt F seine laufenden Forderungen gegen Gastwirt G an Z ab (Sicherungszession). Bei der Abholung beschädigen Zs Mitarbeiter das Aggregat mit dem Gabelstapler grob fahrlässig (EUR 10.000 Schaden). F will den Reparaturschaden gegen den Kaufpreis aufrechnen. Z verlangt volle Ratenzahlung plus die abgetretenen Forderungen. Welche Ansprüche bestehen?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `6523.86`
- used_fallback: `False`

## Workstreams
1. `Eigentumsvorbehalt & Übergang des Eigentums`
   goal: `Klären, ob und wann Eigentum an den Aggregaten auf Z übergegangen ist (§§ 380, 433 BGB iVm Vereinbarung)`
   tools: `['search_by_paragraph', 'get_rechtssatz', 'hot_rs_lookup', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Sicherungszession & Abtretungsrecht`
   goal: `Prüfen Wirksamkeit der Sicherungszession der Forderungen G→F→Z und Rechte Z an den abgetretenen Forderungen (§§ 986 ff. BGB)`
   tools: `['search_by_paragraph', 'search_kommentar_paragraph', 'hot_cluster_context', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Schadensersatz & Aufrechnung bei Mangel/Nichteignung`
   goal: `Beurteilen, ob F Schadensersatzanspruch gegen Z hat (§ 280, 311a BGB iVm grob fahrlässige Beschädigung) und ob Aufrechnung zulässig ist`
   tools: `['search_by_paragraph', 'search_ogh_entscheidungen', 'search_kommentar_keyword', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `186246.1`
- tool_calls_total: `72`
- tool_calls_ok: `70`
- tool_ok_rate: `0.972`
- synth_latency_ms: `26460.44`
- final_answer_chars: `6160`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Eigentumsvorbehalt & Übergang des Eigentums`: ms=72406.87 | tools_ok=26/28 | answer_chars=3086
- `Schadensersatz & Aufrechnung bei Mangel/Nichteignung`: ms=58422.21 | tools_ok=22/22 | answer_chars=2349
- `Sicherungszession & Abtretungsrecht`: ms=55417.02 | tools_ok=22/22 | answer_chars=3674

