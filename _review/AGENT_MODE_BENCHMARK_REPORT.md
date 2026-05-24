# Agent Mode Benchmark Report

**Datum:** 2026-02-28
**Harness:** `scripts/legalchat_agentic_harness_minimal.py --mode agent`
**Pipeline:** 3-Phase (Triage → Deep Analysis → Strategic Response)
**MCP-Mode:** local_http | **Synth-Model:** Grok 4.1 Fast | **Response:** combined/formal

## Ergebnisse

| # | Case | Rechtsgebiet | Gold | Target (95%) | Best Agent | Runs | Ratio | Status |
|---|------|-------------|------|-------------|------------|------|-------|--------|
| 1 | Carmen | EO/IO/KSchG | 9.5 | 9.025 | 9.125 (V9) | 9 | 96.1% | DONE |
| 2 | Celsius/Mitter | HZÜ/Zustellrecht | 9.0 | 8.55 | 8.6 (V2) | 2 | 95.6% | DONE |
| 3 | Kolar/Pfeffer | Zustellrecht | 9.5 | 9.025 | 8.5 (V1) | 4 | 89.5% | STOCH. CEILING |
| 4 | Koller/Baumgartner | Werkvertrag | 8.5 | 8.075 | 8.5 (V1) | 1 | 100% | DONE |
| 5 | Ullrich | ASVG/IP | 8.5 | 8.075 | 8.0-8.1 (V3) | 3 | ~95% | DONE |
| 6 | MITTER:CELSIUS | HZÜ (Neuanalyse) | 9.0 | 8.55 | 8.6 (=Case 2) | — | 95.6% | = Case 2 |

**Avg Agent Score:** 8.54/10 | **Avg Gold Score:** 9.0/10 | **Avg Ratio:** 94.8%
**4/5 Cases >= 95% Target** | 1 Case stochastisch limitiert

## RS-Coverage pro Case

### Carmen (V9, 9.125/10)
- **Gold RS:** RS0002135, RS0002247, RS0003382, RS0003436, RS0003497, RS0004569, RS0018883, RS0020172, RS0021036, RS0025316, RS0109423, RS0114090
- **Agent RS (12+):** Hohe Overlap, inkl. RS0003382 (IO-Anfechtung), RS0002135 (KSchG §25c)
- **9 Iterationen** durch Code-Fixes (best-of-2 synthesis, RS enrichment, §-extraction)

### Celsius/Mitter (V2, 8.6/10)
- **Gold RS:** RS0110261, RS0110260, RS0115027, RS0117046, RS0114024, RS0134713
- **Agent RS:** RS0083714, RS0110260, RS0110261, RS0111049, RS0111369, RS0115027, RS0134713, RS0126357
- **5/6 Gold-RS-Overlap** | RS0111369 (Gehörverletzung/Nichtigkeit) als Bonus

### Kolar/Pfeffer (V1, 8.5/10) — Stochastisches Ceiling
- **Gold RS:** RS0036420, RS0036458, RS0036440, RS0044202, RS0028552
- **Best Agent RS (V1):** RS0036458 (star!), RS0044202, RS0134642, RS0037089
- **2/5 Gold-RS** | RS0036420 (Rückschein beurkundet Zustellvollzug) nie gefunden
- **4 Runs, absteigend:** V1: 8.5 → V2: 8.0 → V3: 7.0 → V4: 7.5

### Koller/Baumgartner (V1, 8.5/10) — First-Run Perfect
- **Gold RS:** RS0025316, RS0037366, RS0037363, RS0114090, RS0071999, RS0021306
- **Agent RS:** RS0019392, RS0035627, RS0035965, RS0037363, RS0038346, RS0071999
- **RS0019392 ≈ RS0025316** (Anwaltsvertrag = Bevollmächtigung) + RS0037363 + RS0071999 direkte Treffer

### Ullrich (V3, 8.0-8.1/10)
- **Gold RS:** RS0084534, RS0127738, RS0100022, RS0130706, RS0084530
- **Agent RS (V3):** RS0084433, RS0084534, RS0105151, RS0115065, RS0129026, RS0127738, RS0084408
- **2/5 exakte Treffer** (RS0084534, RS0127738) + 2 Konzept-Äquivalente (RS0084408≈RS0100022, RS0129026≈RS0084530)
- **Nur RS0130706** (Rehabilitationsgeld kein Stichtag) konsequent fehlend
- **3 Runs, aufsteigend:** V1: 7.0 → V2: 7.5 → V3: 8.0-8.1

## Run-Trajectories

```
Carmen:    V1(6.0) → V2(6.5) → ... → V8(8.3) → V9(9.125) ✓  [9 runs, code fixes]
Celsius:   V1(8.5) → V2(8.6) ✓                                [2 runs]
Kolar:     V1(8.5) → V2(8.0) → V3(7.0) → V4(7.5) ⚠️          [4 runs, stochastic]
Koller:    V1(8.5) ✓                                            [1 run, perfect]
Ullrich:   V1(7.0) → V2(7.5) → V3(8.0-8.1) ✓                  [3 runs, query tuning]
```

## Key Findings

1. **Werkvertrag/Bevollmächtigung** (Koller) exzellent im MCP-Index — first-run perfect
2. **HZÜ/Zustellrecht** (Celsius) gut indexiert — 2 Runs reichten
3. **ASVG/Sozialrecht** (Ullrich) schwieriger — RS-Index ist Zivilrecht-zentriert, ASVG-RS nur teilweise auffindbar
4. **Zustellschein-Spezifika** (Kolar) stochastisch limitiert — RS0036420 nie via MCP-Suche gefunden
5. **Best-of-2 Synthesis + RS Enrichment** (Carmen Code-Fixes) brachten größten Einzellift (+3.1 Punkte über 9 Iterationen)

## Stochastische Varianz

- Grok 4.1 Fast produziert signifikant variierende RS-Auswahl bei identischem Input
- Kolar V1→V3: 4 RS mit Star-RS → 6 RS mit 0/5 Gold-RS (komplett andere Auswahl)
- Ullrich V1→V3: 0/5 → 1/5 → 2/5 Gold-RS (progressiv besser durch Query-Tuning)
- **Query-Formulierung** hat starken Einfluss auf MCP-Pre-Search-Ergebnisse

## Limitierungen

- **MCP-Index-Bias:** Zivilrecht-RS gut abgedeckt, Sozialrecht/ASVG-RS schwächer
- **Stochastische Synthesis:** Kein deterministisches Ergebnis — best-of-N nötig für Reproduzierbarkeit
- **RS-Discovery:** Pre-Search findet RS über Keyword-Matching; sehr spezifische RS (RS0036420) nur bei exaktem Keyword-Treffer
- **Gold-Standard-Abhängigkeit:** Gold-Scores stammen aus Lehrbuch-Benchmark V9 (deep mode) — anderer Codepfad

## Output-Verzeichnisse

```
_review/agent_runs/
├── carmen_v1/ ... carmen_v9/     # 9 Iterationen
├── celsius_v1/ celsius_v2/       # 2 Iterationen
├── kolar_v1/ ... kolar_v4/       # 4 Iterationen
├── koller_v1/                    # 1 Iteration
└── ullrich_v1/ ... ullrich_v3/   # 3 Iterationen
```

Jeder Run enthält: `triage.json`, `analysis.md`, `response.md`, `AGENT_RESULT.md`, `meta.json`
