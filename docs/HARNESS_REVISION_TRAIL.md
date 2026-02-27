# Harness Revision Trail

Chronologische Aenderungshistorie des LegalChat Agentic Harness.

---

## V3 — 27. Februar 2026

**Commit:** `889f714` auf `codex/mcp-zivilrecht-hot-tools`

### Zusammenfassung

Erweiterung des Harness um Power-MCP-Tools, Domain-Klassifikation, 5 Worker-Optimierungen und Multi-Model-Profiling. Validiert auf 4 Cases mit 4 Worker-Modellen.

### Geaenderte Dateien

| Datei | Aenderung |
|-------|-----------|
| `scripts/legalchat_agentic_harness_minimal.py` | 3 Power-Tool-Specs, Topic-Patterns, Sanitize/Build-Args, Workstreams, Pre-Search, 5 Worker-Fixes |
| `config/agent_profiles.yaml` | 8 neue Profile, Default auf `grok_worker` |
| `config/mcp_registry.yaml` | 7 neue Tools in Rollen + Policies |

### Neue MCP-Tools (7)

| Tool | Kategorie | Zweck |
|------|-----------|-------|
| `search_by_paragraph` | Retrieval | RS nach §-Nummer |
| `search_by_schlagwort` | Retrieval | RS nach OGH-Schlagwort |
| `hot_rs_lookup` | Retrieval | RS + TE-Mini-Stories direkt |
| `hot_index_stats` | Retrieval | Index-Metadaten |
| `build_grounding_context` | Power | Cluster-Level Minimal-Ruleset (TopicPreprocessor) |
| `detect_clusters` | Power | Automatische Cluster-Erkennung |
| `ask_gemini_zivilrecht` | Power | Fine-tuned Gemini Expert |

### Neue Features

1. **Domain-Klassifikation:** Deterministischer Pattern-Matcher (`_TOPIC_PATTERNS`) erkennt 12 Rechtsgebiete. LLM-Fallback bei confidence < 0.5.
2. **Query-Expansion:** Cheap LLM generiert paragraph_queries, schlagwort_queries, keyword_queries vor Worker-Loop.
3. **Pre-Search Scatter:** 8-10 parallele MCP-Calls inkl. `build_grounding_context` und `detect_clusters` bei Topic-Match.
4. **Phasengesteuerter Worker-Prompt:** Phase 1 (Suche), Phase 2 (Vertiefen + Power-Tools), Phase 3 (Zusammenfassung).
5. **Cross-Stream Awareness:** Worker sehen Namen paralleler Streams.

### Worker-Optimierungen (5 Fixes)

| # | Fix | Vorher | Nachher |
|---|-----|--------|---------|
| 1 | Pre-search evidence truncation | 3000 chars | 5000 chars |
| 2 | Power-Tools im Worker-Prompt | nicht erwaehnt | Phase 2B Guidance |
| 3 | Payload preview fuer High-Value-Tools | 1600 chars | 2400 chars |
| 4 | Organizer Domain Guidance | keine | Power-Tool-Workstream bei confidence>=0.5 |
| 5 | Cross-stream awareness | keine | Parallele Stream-Namen sichtbar |

### Modellprofile (13 total, 5 neu)

| Profil | Worker | Rolle |
|--------|--------|-------|
| `grok_worker` (Default) | x-ai/grok-4.1-fast | Beste Qualitaet |
| `minimax_worker` | minimax/minimax-m2.5 | Budget-Alternative |
| `deepseek_worker` | deepseek/deepseek-v3.2 | Nicht empfohlen |
| `gemini3_worker` | google/gemini-3-flash-preview | Test |
| `kimi_swarm` | moonshotai/kimi-k2.5 | Swarm-Experiment |

### Validierung (4-Case Regression)

| Case | Domain | Tools | RS | Key Checks | Ergebnis |
|------|--------|------:|---:|------------|:--------:|
| Carmen | exekution | 53 | 5 | §25c YES, §25d YES, §40 EO YES | PASS |
| Kolar | zustellrecht | 60 | 5 | ZustG YES, §158 ZPO YES | PASS |
| Ullrich | sozialversicherung | 47 | 9 | ASVG YES, 0x ABGB/StGB | PASS |
| Arzthaftung | schadenersatz | 63 | 11 | §1299 YES, §1296 YES, Kausalitaet YES | PASS |

Power-Tool-Aktivierung: `build_grounding_context` bei Carmen + Arzthaftung. Korrekt inaktiv bei Kolar (Zustellrecht) und Ullrich (ASVG).

### Worker-Modell Vergleich (Carmen-Case)

| Worker | Tools | RS | §25c | Latenz | Empfehlung |
|--------|------:|---:|:----:|-------:|:----------:|
| Grok 4.1 Fast | 54 | 8 | YES | 103s | Default |
| MiniMax M2.5 | 33 | 6 | YES | 99s | Budget |
| Flash Lite | 24 | 5 | NO | 132s | Nicht empfohlen |
| DeepSeek V3.2 | 26 | 5 | NO | 172s | Nicht empfohlen |

### Report-Artefakte

- `_review/test_reports/HARNESS_V3_FULL_COMPARISON_20260227.md` — Vollstaendiger Vergleich
- `_review/test_reports/WORKER_MODEL_COMPARISON_V3.md` — Worker-Modell Ranking
- `_review/test_reports/HARNESS_V3_TEST_CHECKLIST.json` — 4-Case Pass/Fail Kriterien
- `_review/test_reports/CARMEN_AB_TEST_RESULTS.md` — Carmen A/B Flash vs Grok
- `_review/test_reports/GROK_WORKER_FULL_REGRESSION.md` — Grok 3-Case Regression

---

## V2 — 26. Februar 2026

**Baseline-Commit:** `qwen_all_2026-02-26_final`

### Zusammenfassung

Initiales Review-Paket mit 10-Case-Benchmark, Citation Gates, Grounding Policy. 7 MCP-Tools, 5 Modellprofile.

### Kern-Features

- Rollenorchestrierung: Organizer, Worker, Synthese, Citation-Repair
- 7 MCP-Tools (search_ogh_rechtssaetze, search_ogh_entscheidungen, get_rechtssatz, hot_rs_search, hot_cluster_context, search_kommentar_paragraph, search_kommentar_keyword)
- Citation Gate Modi: off, warn, repair, enforce
- Grounding Policy: postgres_only
- 5 Modellprofile: cheap_default (Standard), cheap_grok_fast, default, premium_champion, qwen_all

### Validierung

- 10-Faelle-Benchmark: Local + Remote, 10/10 ok
- Citation Gate Pass Rate: 1.0
- Invalid RS: 0, Ungrounded RS/TE: 0

### Report-Artefakte

- `_review/test_reports/baselines/qwen_all_2026-02-26_final/summary.json`
- `_review/test_reports/AGENTIC_PROFILE_COMPARE_CHEAP_DEFAULT_VS_GROK_FAST_2026-02-26.md`

### Architektur-Dokumente (erstellt)

- `docs/HARNESS_REVIEW_PACKAGE.md`
- `docs/HARNESS_ARCHITECTURE_EXTERNAL_REVIEW.md`
- `docs/HARNESS_PRD.md`
- `docs/HARNESS_INVENTORY.md`
