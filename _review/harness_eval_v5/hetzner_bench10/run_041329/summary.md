# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T04:13:29.017304+00:00`
- Dry run: `False`
- Query: `Eigentümer E verkauft seine Liegenschaft an B. B wird NICHT ins Grundbuch eingetragen. Anschließend verkauft E dieselbe Liegenschaft an A. A wird ordnungsgemäß ins Grundbuch eingetragen und wird damit bücherlicher Eigentümer. B erfährt davon und klagt auf Löschung der Eintragung des A und eigene Eintragung. Wer ist Eigentümer? Hat B Ansprüche gegen A auf Herausgabe? Oder nur gegen E?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `3208.67`
- used_fallback: `False`

## Workstreams
1. `Eigentumsvorbehalt & Übergang des Eigentums bei Liegenschaften`
   goal: `Klären, wann Eigentum an Liegenschaften beim Käufer eintritt (§ 367, § 480 ABGB) und welche Rolle die Grundbucheintragung spielt`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Schutz des nicht eingetragenen Käufers (B) vs. bücherlichem Eigentümer (A)`
   goal: `Prüfen, ob B Ansprüche gegen A (z.B. auf Herausgabe) oder nur gegen E hat – insbesondere im Lichte des § 1500 ABGB (Gutgläubigenschutz)`
   tools: `['hot_cluster_context', 'search_kommentar_paragraph', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Rechtsprechungsübersicht & Hot RS-Suche`
   goal: `Identifizieren relevanter OGH-Entscheidungen zur Konstellation 'Doppelverkauf ohne Grundbucheintragung'`
   tools: `['search_ogh_entscheidungen', 'hot_rs_search', 'detect_clusters', 'hot_index_stats', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `208964.84`
- tool_calls_total: `62`
- tool_calls_ok: `60`
- tool_ok_rate: `0.968`
- synth_latency_ms: `23555.42`
- final_answer_chars: `4569`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Eigentumsvorbehalt & Übergang des Eigentums bei Liegenschaften`: ms=73493.05 | tools_ok=13/14 | answer_chars=3118
- `Rechtsprechungsübersicht & Hot RS-Suche`: ms=88789.89 | tools_ok=30/31 | answer_chars=2927
- `Schutz des nicht eingetragenen Käufers (B) vs. bücherlichem Eigentümer (A)`: ms=46681.9 | tools_ok=17/17 | answer_chars=2932

