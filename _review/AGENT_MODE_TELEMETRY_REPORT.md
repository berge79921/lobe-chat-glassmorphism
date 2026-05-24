# Agent Mode Telemetry Report

**Datum:** 2026-02-28
**19 Runs** | 5 Cases | 3-Phase Pipeline (Triage → Deep Analysis → Strategic Response)

## 1. Runtime pro Run

| Run | Elapsed (s) | Triage (s) | Analysis (s) | Response (s) | Cost ($) |
|-----|------------|-----------|-------------|-------------|---------|
| carmen_v1 | 124.3 | 18.2 | 79.8 | 26.3 | 0.072 |
| carmen_v2 | 143.8 | 18.5 | 103.5 | 21.8 | 0.071 |
| carmen_v3 | 144.8 | 23.9 | 93.6 | 27.3 | 0.075 |
| carmen_v4 | 148.3 | 24.4 | 95.1 | 28.8 | 0.060 |
| carmen_v5 | 155.6 | 27.2 | 101.7 | 26.7 | 0.109 |
| carmen_v6 | 145.4 | 25.0 | 102.7 | 17.6 | 0.086 |
| carmen_v7 | 181.4 | 26.0 | 132.7 | 22.7 | 0.104 |
| carmen_v8 | 183.6 | 24.2 | 136.2 | 23.2 | 0.072 |
| carmen_v9 | 182.7 | 26.4 | 134.5 | 21.7 | 0.091 |
| celsius_v1 | 186.0 | 27.3 | 144.9 | 13.9 | 0.075 |
| celsius_v2 | 178.5 | 20.2 | 130.4 | 27.8 | 0.082 |
| kolar_v1 | 175.0 | 21.4 | 127.9 | 25.7 | 0.064 |
| kolar_v2 | 177.3 | 23.5 | 132.9 | 20.9 | 0.070 |
| kolar_v3 | 182.1 | 20.1 | 128.6 | 33.3 | 0.067 |
| kolar_v4 | 185.7 | 22.8 | 135.9 | 26.9 | 0.076 |
| koller_v1 | 175.8 | 17.6 | 136.7 | 21.5 | 0.067 |
| ullrich_v1 | 167.2 | 20.0 | 130.2 | 16.9 | 0.060 |
| ullrich_v2 | 194.0 | 37.3 | 138.8 | 17.9 | 0.061 |
| ullrich_v3 | 170.2 | 27.7 | 121.5 | 21.1 | 0.079 |
| **AVG** | **168.5** | **24.3** | **121.0** | **23.0** | **$0.076** |
| **TOTAL** | **3,201.7** | — | — | — | **$1.44** |

**Phase-Verteilung:** Triage 14% | Analysis 72% | Response 14%

## 2. Kosten-Breakdown

| Komponente | Total ($) | Anteil |
|-----------|----------|--------|
| Subagents (3x Gemini 3 Flash) | 1.253 | **87.0%** |
| Synthesis (Grok 4.1-fast) | 0.099 | 6.9% |
| Response (Grok 4.1-fast) | 0.038 | 2.6% |
| Triage (Grok 4.1-fast) | 0.028 | 1.9% |
| Organizer (Grok 4.1-fast) | 0.023 | 1.6% |

**Cheapest run:** carmen_v4 ($0.060) | **Teuerster:** carmen_v5 ($0.109)

## 3. Output-Grössen

| Metrik | Min | Max | Avg |
|--------|-----|-----|-----|
| `analysis.md` | 3,487 B | 7,847 B | 4,925 B |
| `response.md` | 3,087 B | 4,977 B | 4,255 B |
| `AGENT_RESULT.md` | 9,141 B | 14,154 B | 10,591 B |
| `triage.json` | 1,716 B | 2,845 B | 2,242 B |
| `result.json` | 89,833 B | 198,571 B | ~139K B |
| RS cited in final answer | 4 | 15 | 9 |
| RS im Evidence Pool | 6 | 53 | 28 |

## 4. Tool Calls

| Tool | Calls | Anteil |
|------|-------|--------|
| `get_rechtssatz` | 311 | 25.1% |
| `hot_rs_lookup` | 286 | 23.1% |
| `search_ogh_rechtssaetze` | 200 | 16.1% |
| `search_by_paragraph` | 145 | 11.7% |
| `hot_rs_search` | 133 | 10.7% |
| `search_kommentar_*` | 128 | 10.3% |
| Rest (schlagwort, clusters, gemini) | 36 | 2.9% |
| **Total** | **1,239** | **100% OK** |

**100% Erfolgsrate** — 0 Fehler bei 1,239 MCP Tool Calls.

## 5. Modell-Konfiguration

| Rolle | Modell |
|-------|--------|
| Triage | `x-ai/grok-4.1-fast` |
| Organizer | `x-ai/grok-4.1-fast` |
| Subagents (3x parallel) | `google/gemini-3-flash-preview` |
| Synthesis (best-of-2) | `x-ai/grok-4.1-fast` |
| Response | `x-ai/grok-4.1-fast` |

## 6. Verbose Trace — Highlights

### Carmen v9 (9.125/10, Best Run)

**Triage** identifiziert "laufende Gehaltsexekution gegen AMS-Leistungen" als HIGH urgency. 3 Szenarien: ZMR-Nachweis → Exekution eingestellt; Tilgung anerkannt; Anträge abgewiesen.

**Pre-Search** feuert 10+ MCP-Calls parallel: §6/9/25c/25d KSchG, §14 IO. §14 IO liefert 0 Ergebnisse.

**Best-of-2 Synthesis:**
```
A=104.9 (11 RS) vs B=89.5 (9 RS) → A gewählt
```
Kein RS-Enrichment nötig. Citation Gate: alle 11 RS verifiziert (`found=true`).

### Celsius v2 (8.6/10)

**Triage** extrahiert Rekursfrist 09.03.2026 (9 Tage). Urgency HIGH wegen drohender Rechtskraft.

**Best-of-2:**
```
A=80.5 (9 RS) vs B=86.6 (10 RS) → B gewählt
RS Enrichment: +1 RS (RS0126357) injected
```

### Kolar v1 (8.5/10) — Dünnste RS-Abdeckung

**Best-of-2:**
```
A=23.2 (3 RS) vs B=24.2 (3 RS) → B gewählt
```
Sehr niedrige Scores — ZustG/§292 ZPO-Domäne hat wenig RS im Index. RS-Enrichment injiziert RS0037089 (§879 ABGB) — **falsches Thema**, ein Routing-Fehler.

### Koller v1 (8.5/10) — First-Run Perfect

**Best-of-2:**
```
A=69.3 (7 RS) vs B=63.0 (7 RS) → A gewählt
RS Enrichment: +3 RS injected (RS0035965, RS0038346, RS0126928)
```
Höchste Injection-Rate aller 5 Cases — Synthesizer liess Lücken, Enrichment füllt sie.

### Ullrich v3 (8.0-8.1/10) — ASVG-Domäne

**Triage** (27.7s, längster aller Runs) identifiziert 4 Entscheidungspunkte: Berufsschutz, Verweisbarkeit, Krankengeld, Rehabilitationsgeld.

**Organizer** splittet exakt nach §255 ASVG Absätzen: WS1=Abs2, WS2=Abs3, WS3=Abs4.

**RS-Treffer:** RS0084534 (Gold!), RS0127738 (Gold!), RS0084408 (≈RS0100022), RS0129026 (≈RS0084530). 2/5 exakte + 2 Konzept-Äquivalente.

## 7. Beobachtungen

1. **Phase 1 dominiert** (72% Runtime, 87% Kosten) — Subagent-MCP-Calls sind der Flaschenhals
2. **Best-of-2 Synthesis** wirkt: carmen_v9 (104.9 vs 89.5) und celsius_v2 (80.5 vs 86.6) zeigen signifikante Score-Spreizung
3. **RS-Enrichment** füllt Lücken (koller +3 RS, celsius +1), kann aber fehlgehen (kolar: falsches Thema)
4. **Stochastische Varianz:** Carmen v1→v9 zeigt Runtime-Anstieg von 124→183s nach Code-Fixes (best-of-2, RS enrichment)
5. **MCP-Reliability:** 100% Erfolgsrate bei 1,239 Calls — kein einziger Fehler
6. **Kosteneffizienz:** $0.076/Run avg, $1.44 total für alle 19 Runs
7. **Ullrich Pre-Search schwächer:** Nur 3.3-4.1K evidence chars vs 5K bei allen anderen Cases (ASVG schwächer indexiert)
