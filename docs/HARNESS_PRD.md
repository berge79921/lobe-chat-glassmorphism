# Harness PRD (Product Requirements)

Stand: 27. Februar 2026 (V3 Update)

## 1. Produktproblem

Fuer legales One-shot und agentisches Arbeiten wird ein operativer Harness benoetigt, der:

- juristische Evidenz aus internen Tools konsolidiert,
- LLM-Rollen kontrolliert orchestriert,
- und fachlich riskante Halluzinationen ueber harte Zitationspruefung verhindert.

## 2. Produktziel

Ein kosteneffizienter, reproduzierbarer Agentic-Runner, der im Zusammenspiel aus LLM + MCP + PostgreSQL stabile, zitierfaehige Antworten liefert und zwischen lokalem und Hetzner-Betrieb vergleichbar arbeitet.

## 3. Nutzer und Hauptnutzen

1. Juristischer Analyst:
   - Erwartet belastbare RS/TE/Normen-Zitate.
2. Ops/Engineering:
   - Erwartet reproduzierbare Laeufe, klare Reports, Profile fuer Kosten/Qualitaet.
3. Externer Reviewer:
   - Erwartet nachvollziehbare Architektur, klare Artefakte, reproduzierbare Benchmark-Pfade.

## 4. Functional Requirements

1. Rollenorchestrierung:
   - Organizer, Worker, Synthese, optional Citation-Repair.
2. MCP-Integration:
   - Local und Remote Tooling mit konfigurierbarer Policy.
   - V3: 14 aktive Tools inkl. 3 Power-Tools (build_grounding_context, detect_clusters, ask_gemini_zivilrecht).
3. Domain-Klassifikation (V3):
   - Deterministischer Pattern-Matcher + LLM-Fallback fuer Rechtsgebiet-Erkennung.
   - Injiziert Domain-Hint und §§-Prioritaeten in Organizer und Worker.
4. Pre-Search Scatter (V3):
   - Query-Expansion via cheap LLM, dann 8-10 parallele MCP-Calls vor Worker-Loop.
   - Bis zu 5000 Zeichen Startkontext fuer Worker.
5. Grounding:
   - `postgres_only` als erzwingbare Betriebsart.
6. Citation-Gates:
   - Modi `off|warn|repair|enforce`.
7. Profilsteuerung:
   - 13 konfigurierbare Modellprofile (V3: grok_worker als Default).
8. Traceability:
   - Vollstaendige Run-Artefakte pro Query.
9. Benchmarking:
   - 10-Faelle Runner mit Local-vs-Remote Vergleich und Judge-Auswertung.
   - V3: 4-Case Regression (Carmen, Kolar, Ullrich, Arzthaftung) mit Pass/Fail-Kriterien.

## 5. Non-Functional Requirements

1. Sicherheit:
   - Keine ungrounded Judikatur im finalen Output bei aktiviertem Gate.
2. Performance:
   - Operativ unter Last kontrollierbar (Guardrails fuer Query/Rows/Timeout).
3. Reproduzierbarkeit:
   - Gleiches Manifest + gleiche Policy = vergleichbare Bewertungsbasis.
4. Betriebsfaehigkeit:
   - Remote-Mode ueber SSH/Container ohne neue Infrastruktur zwingend.

## 6. Out of Scope

1. Vollstaendige UI-Agent-Experience.
2. Vollstaendige autonome Langlauf-Agentenplattform.
3. Vollstaendige Datenpipeline- und ETL-PRD fuer alle Gerichte.

## 7. Success Metrics

Pflichtmetriken fuer operative Freigabe eines Profils:

1. `citation_gate_pass_rate_local >= 0.95`
2. `citation_gate_pass_rate_remote >= 0.95`
3. `invalid_rs_total == 0`
4. `ungrounded_rs_total == 0`
5. `ungrounded_te_total == 0`
6. `missing_postgres_judicature_total == 0`

Aktueller Nachweis (qwen_all Snapshot):

- Alle obigen Safety-Metriken sind im 10-Faelle-Lauf erfuellt.

## 8. Betriebsprofile (V3 Stand)

Quelle:

- `/Users/reinhardberger/HCS/lobe-chat-custom/config/agent_profiles.yaml`

Wesentliche Profile:

1. `grok_worker` (V3 Produktionsdefault — Grok 4.1 Fast Worker)
2. `minimax_worker` (V3 Budget-Alternative — MiniMax M2.5 Worker)
3. `cheap_default` (Legacy Baseline — Flash Lite Worker)
4. `default` (Gemini 3 Flash Worker)
5. `premium_champion` (GPT-5.3 Codex + Grok 4.1 Fast)
6. `qwen_all` (gefrorene Qualitaetsbaseline)

V3 Benchmark-Ergebnisse (4-Case Regression):

| Profil | Avg Tools | Avg RS | Pass Rate | Avg Latenz |
|--------|----------:|-------:|----------:|---------:|
| `grok_worker` (post-opt) | 56 | 7.5 | 4/4 | 113s |
| `minimax_worker` | 33 | 12.7 | 3/3 | 99s |
| `cheap_default` | 25 | 4.3 | 2/3 | 125s |

## 9. Acceptance Criteria (Release-Ready)

Ein Harness-Release gilt als review-ready, wenn:

1. Architektur-, PRD- und Inventory-Dokumente aktuell sind.
2. 10-Faelle-Benchmark erfolgreich durchgelaufen ist (local/remote ok).
3. Safety-Metriken gruen sind (siehe Section 7).
4. Ergebnisartefakte und Pfade fuer externes Review verlinkt sind.

## 10. Risiken und Gegenmassnahmen

1. Risiko: Modell driftet in freies Vorwissen.
   - Massnahme: `postgres_only` + Citation-Gate `repair/enforce`.
2. Risiko: Toolqueries sind zu schwach, resultieren in leerer Evidenz.
   - Massnahme: Organizer-Routing verbessern, Query-Normalisierung erweitern.
3. Risiko: Kosten/Latenz steigen durch Premium-Modelle.
   - Massnahme: `cheap_default` als operativer Standard, Premium nur fuer Spezialfaelle.
