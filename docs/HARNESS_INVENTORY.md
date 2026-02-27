# Harness Inventory (External Review)

Stand: 27. Februar 2026 (V3 Update)

## 1. Ziel dieses Inventory

Dieses Dokument listet die relevanten Artefakte fuer die externe Review des agentischen Harness:

- Laufzeitcode
- Konfiguration
- Benchmark-/Validierungsartefakte
- Operative Baselines

## 2. Laufzeitcode

1. Haupt-Runner:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/scripts/legalchat_agentic_harness_minimal.py`
2. 10-Faelle-Benchmark:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/scripts/zivilrecht_agentic_10cases_benchmark.py`
3. One-shot Vergleichsrunner:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/scripts/zivilrecht_oneshot_functional_compare.py`
4. Concurrency-Benchmark:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/scripts/agentic_concurrency_benchmark.py`

## 3. Konfiguration

1. Modellprofile:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/config/agent_profiles.yaml`
2. MCP Registry, Rollen-Tool-Policy, Guardrails:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/config/mcp_registry.yaml`
3. Skill-Bindings pro Rolle:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/config/skills_bindings.yaml`
4. Operative Baselines:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/config/operational_baselines.yaml`

## 4. Testfall-Manifest

10-Faelle Manifest:

- `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_specs/zivilrecht_oneshot_cases_v1.yaml`

## 5. Baseline- und Report-Artefakte

1. Eingefrorene qwen_all Baseline:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/baselines/qwen_all_2026-02-26_final/summary.json`
   - `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/baselines/qwen_all_2026-02-26_final/summary.md`
2. V3 Full Comparison Report (4 Worker-Modelle, 4 Cases, 15+ Runs):
   - `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/HARNESS_V3_FULL_COMPARISON_20260227.md`
3. V3 Worker Model Comparison:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/WORKER_MODEL_COMPARISON_V3.md`
4. V3 Test Checklist (4 Cases mit Pass/Fail-Kriterien):
   - `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/HARNESS_V3_TEST_CHECKLIST.json`
5. Profilvergleich cheap_default vs cheap_grok_fast:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/AGENTIC_PROFILE_COMPARE_CHEAP_DEFAULT_VS_GROK_FAST_2026-02-26.md`
6. Historische Agentic 10-Faelle Runs:
   - `/Users/reinhardberger/HCS/lobe-chat-custom/_review/test_reports/zivilrecht_agentic_10cases_*`

## 6. Tooling Contract (aus Inventory-Sicht, V3)

Retrieval-Tools (Worker + Organizer):

- `search_ogh_rechtssaetze`
- `search_ogh_entscheidungen`
- `get_rechtssatz`
- `search_by_paragraph` (V3: neu)
- `search_by_schlagwort` (V3: neu)
- `hot_rs_search`
- `hot_rs_lookup` (V3: neu)
- `hot_cluster_context`
- `hot_index_stats` (V3: neu)
- `search_kommentar_paragraph`
- `search_kommentar_keyword`

Power-Tools (V3: Cluster-Grounding + Expert):

- `build_grounding_context` — Minimal-Ruleset aus TopicPreprocessor (12 Rechtsgebiete)
- `detect_clusters` — Cluster-Erkennung via Keyword-Matching
- `ask_gemini_zivilrecht` — Fine-tuned Gemini Pro fuer Laesio/Bereicherung/Pflichtteil

Nicht direkt tool-enabled:

- `synth` Rolle
- `citation_repair` Rolle

## 7. Reproduktion: Minimalbefehle

1. Single-Case, volle Pipeline:

```bash
python3 /Users/reinhardberger/HCS/lobe-chat-custom/scripts/legalchat_agentic_harness_minimal.py \
  --query "Pruefe laesio enormis mit OGH-Linie und Kommentar." \
  --model-profile cheap_default \
  --mcp-mode local_http \
  --citation-gate-mode enforce \
  --grounding-policy postgres_only \
  --config-dir /Users/reinhardberger/HCS/lobe-chat-custom/config
```

2. 10-Faelle, Local-vs-Remote:

```bash
python3 /Users/reinhardberger/HCS/lobe-chat-custom/scripts/zivilrecht_agentic_10cases_benchmark.py \
  --limit-cases 10 \
  --model-profile qwen_all \
  --citation-gate-mode repair \
  --grounding-policy postgres_only \
  --judge-model x-ai/grok-4.1-fast \
  --judge-fallback-model google/gemini-3-flash-preview \
  --config-dir /Users/reinhardberger/HCS/lobe-chat-custom/config
```

## 8. Bekannte Grenzen im aktuellen Inventory

1. Einige historische Judge-Ergebnisse enthalten modelbedingte Schwankungen in der Tiefe, trotz gruener Citation-Gates.
2. Latenzprofil ist stark modellabhaengig; `cheap_default` bleibt Betriebsstandard fuer Kosten/Speed.
3. Organizer-Backend `opencode_sidecar` ist als optionaler Pfad vorgesehen, aber nicht produktiver Default.
