# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T13:27:45.294009+00:00`
- Dry run: `False`
- Query: `A ist Eigentümer des Grundstücks X, das nur über das Nachbargrundstück Y des B erreichbar ist. Im Grundbuch ist zugunsten von X ein Geh- und Fahrwegerecht auf Y eingetragen. B stellt ein schweres Tor auf den Weg und wechselt das Schloss, sodass A sein Grundstück nicht mehr erreichen kann. Parallel verlegt Nachbar N ohne Zustimmung des A eine Wasserleitung über As Grundstück. A verlangt: (1) Entfernung des Tores durch B, (2) Entfernung der Wasserleitung durch N und Unterlassung. Welche Ansprüche hat A?`
- Model profile: `cheap_grok_fast`
- Organizer backend: `openrouter`
- MCP mode: `docker_exec`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `x-ai/grok-4.1-fast`
- Synth model: `x-ai/grok-4.1-fast`

## Organizer
- latency_ms: `22804.01`
- used_fallback: `False`

## Workstreams
1. `Eigentumsgewährleistung & Wegerecht (§ 367, § 431 ABGB)`
   goal: `Prüfung von A's Anspruch auf B auf Entfernung des Tores und Unterlassung, basierend auf Eigentumsgewährleistung und dinglichen Rechten (Geh- und Fahrwegerecht)`
   tools: `['get_rechtssatz', 'hot_rs_lookup', 'search_kommentar_paragraph', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
2. `Eingriff in Eigentum & Unlawful Usufruct (§ 480, § 1500 ABGB)`
   goal: `Prüfung von A's Anspruch auf N auf Entfernung der Wasserleitung und Unterlassung, unter Berücksichtigung von § 480 ABGB (Eigentumsvorenthaltung) und § 1500 ABGB (Usus)`
   tools: `['hot_rs_search', 'search_kommentar_paragraph', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`
3. `Synthese & OGH-Taxonomie-Kontext`
   goal: `Konsolidierung der Rechtsprechung und Kommentarpositionen zu den relevanten Sachenrechtsfragen, insbesondere zu dinglichen Zugangsgarantien und unerlaubten Eingriffen`
   tools: `['detect_clusters', 'hot_cluster_context', 'hot_index_stats', 'search_by_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze', 'get_rechtssatz', 'hot_rs_lookup']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `174308.87`
- tool_calls_total: `55`
- tool_calls_ok: `55`
- tool_ok_rate: `1.0`
- synth_latency_ms: `22578.21`
- final_answer_chars: `5406`
- citation_gate_mode: `enforce`
- citation_gate_applied: `False`
- citation_gate_pass_before: `True`
- citation_gate_pass_after: `True`

## Stream Details
- `Eigentumsgewährleistung & Wegerecht (§ 367, § 431 ABGB)`: ms=53539.81 | tools_ok=16/16 | answer_chars=3603
- `Eingriff in Eigentum & Unlawful Usufruct (§ 480, § 1500 ABGB)`: ms=73007.47 | tools_ok=20/20 | answer_chars=3641
- `Synthese & OGH-Taxonomie-Kontext`: ms=47761.59 | tools_ok=19/19 | answer_chars=4177

