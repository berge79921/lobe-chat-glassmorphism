# Harness Review Package

Stand: 27. Februar 2026 (V3 Update)

Scope: Nur der agentische Harness (nicht die komplette Plattform-Architektur).

## Dokumente

1. Architektur: `docs/HARNESS_ARCHITECTURE_EXTERNAL_REVIEW.md`
2. PRD: `docs/HARNESS_PRD.md`
3. Inventory: `docs/HARNESS_INVENTORY.md`
4. Revision Trail: `docs/HARNESS_REVISION_TRAIL.md` (V3: neu)

## Was mit den 10 Testfaellen bereits abgesichert ist

- Reproduzierbarer 10-Faelle-Agentic-Benchmark (Local vs Remote) auf gleichem Manifest.
- Aktueller eingefrorener Referenzlauf:
  - `_review/test_reports/baselines/qwen_all_2026-02-26_final/summary.json`
- Harte Zitier- und Grounding-Kriterien fuer diesen Lauf:
  - `citation_gate_mode=repair`
  - `grounding_policy=postgres_only`
  - invalid/ungrounded citations: `0`

## V3 Erweiterungen (27.02.2026)

- 3 Power-MCP-Tools: `build_grounding_context`, `detect_clusters`, `ask_gemini_zivilrecht`
- Domain-Klassifikation + Query-Expansion + Pre-Search Scatter
- 5 Worker-Optimierungen (Pre-Search 5000ch, Power-Tool-Prompt, Payload 2400, Organizer-Guidance, Cross-Stream)
- 13 Modellprofile, Default: `grok_worker` (Grok 4.1 Fast)
- 4-Case Regression (Carmen, Kolar, Ullrich, Arzthaftung): 4/4 PASS
- V3 Full Comparison Report: `_review/test_reports/HARNESS_V3_FULL_COMPARISON_20260227.md`

## Minimaler Reviewer-Start

1. Architektur lesen (V3 Sections 4, 10, 11 fuer Neuerungen).
2. PRD gegen Architektur mappen.
3. Revision Trail fuer chronologische Aenderungshistorie lesen.
4. Inventory zur Verifikation (Code/Config/Reports) nutzen.
5. Einen 1-Case-Smoketest und optional den 10-Faelle-Benchmark rerunnen.
