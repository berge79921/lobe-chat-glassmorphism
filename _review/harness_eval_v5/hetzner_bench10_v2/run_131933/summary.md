# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:19:33.125928+00:00`
- Dry run: `False`
- Query: `Eigentümer E verkauft seine Liegenschaft an B. B wird NICHT ins Grundbuch eingetragen. Anschließend verkauft E dieselbe Liegenschaft an A. A wird ordnungsgemäß ins Grundbuch eingetragen und wird damit bücherlicher Eigentümer. B erfährt davon und klagt auf Löschung der Eintragung des A und eigene Eintragung. Wer ist Eigentümer? Hat B Ansprüche gegen A auf Herausgabe? Oder nur gegen E?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `9721.74`
- used_fallback: `False`

## Workstreams
1. `Eigentumsvorbehalt & Übergang des Eigentums bei Liegenschaften`
   goal: `Klären, wann Eigentum an Liegenschaften beim Käufer eintritt und welche Voraussetzungen für wirksame Übergabe erfüllt sein müssen – insbesondere bei fehlender Grundbucheintragung`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Rechtsfolgen bei doppeltem Verkauf & öffentliches Gutachtenprinzip`
   goal: `Prüfen, ob der spätere Käufer A durch Grundbucheintragung Eigentum erlangt hat und ob B Ansprüche gegen A oder nur gegen E hat`
   tools: `['hot_cluster_context', 'search_kommentar_paragraph', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Rechtsprechung & Leitsätze zu doppelten Liegenschaftsverkäufen`
   goal: `Identifizieren von OGH-Leitsätzen und Hot-Index-Entscheidungen zur Konstellation 'fehlende Grundbucheintragung → spätere Eintragung eines anderen → Klage auf Löschung'`
   tools: `['search_ogh_rechtssaetze', 'hot_index_stats', 'detect_clusters', 'build_grounding_context', 'search_by_paragraph', 'search_by_schlagwort', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `146075.5`
- tool_calls_total: `56`
- tool_calls_ok: `56`
- tool_ok_rate: `1.0`
- synth_latency_ms: `27453.35`
- final_answer_chars: `6085`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Eigentumsvorbehalt & Übergang des Eigentums bei Liegenschaften`: ms=54093.51 | tools_ok=16/16 | answer_chars=3719
- `Rechtsfolgen bei doppeltem Verkauf & öffentliches Gutachtenprinzip`: ms=48803.71 | tools_ok=18/18 | answer_chars=3181
- `Rechtsprechung & Leitsätze zu doppelten Liegenschaftsverkäufen`: ms=43178.28 | tools_ok=22/22 | answer_chars=2937

