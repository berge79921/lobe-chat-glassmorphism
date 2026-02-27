# Grok 4.1 Fast Worker — Full 3-Case Regression (2026-02-27)

## Scorecard

| Case | Metrik | Flash Lite (cheap_default) | Grok 4.1 Fast (grok_worker) | Delta |
|------|--------|---------------------------|----------------------------|-------|
| **CARMEN** | Tool Calls | 24 | **54** | +125% |
| | RS Cited | 5 | **8** | +60% |
| | Answer Chars | 3648 | **4156** | +14% |
| | §40 EO | YES | YES | = |
| | §25d KSchG | YES | YES | = |
| | **§25c KSchG** | NO | **YES** | **NEW** |
| | Time | 132s | **103s** | -22% |
| | **Status** | **PASS** | **PASS** | |
| **KOLAR** | Tool Calls | 32 | **73** | +128% |
| | RS Cited | 6 | 6 | = |
| | Answer Chars | 3618 | **4322** | +19% |
| | §16 ZustG | YES | YES | = |
| | §158 ZPO | YES | YES | = |
| | §22 ZustG | NO | **YES** | **NEW** |
| | §292 ZPO | NO | **YES** | **NEW** |
| | Time | 133s | 140s | +5% |
| | **Status** | **PASS** | **PASS** | |
| **ULLRICH** | Tool Calls | 19 | **47** | +147% |
| | RS Cited | 2 | **7** | +250% |
| | Answer Chars | 3219 | **4027** | +25% |
| | § 254 ASVG | YES | YES | = |
| | § 255 ASVG | partial | **YES** | improved |
| | § 273 ASVG | NO | **YES** | **NEW** |
| | Bad Cite (§1295/§129) | NO | NO | = |
| | Time | — | 127s | — |
| | **Status** | **PASS** | **PASS** | |

## Aggregiert

| Metrik | Flash Lite avg | Grok 4.1 avg | Delta |
|--------|---------------|-------------|-------|
| **Tool Calls** | 25 | **58** | **+132%** |
| **RS Cited** | 4.3 | **7.0** | **+63%** |
| **Answer Chars** | 3495 | **4168** | **+19%** |
| **Pass Rate** | 3/3 | 3/3 | = |
| **Est. Cost/Query** | ~$0.004 | ~$0.008 | +100% |

## Key Findings

1. **Grok 4.1 Fast ist als Worker klar überlegen**: +132% mehr Tool-Calls, +63% mehr RS, +19% längere Antworten
2. **Qualitative Verbesserungen**:
   - Carmen: §25c KSchG (Informationspflicht) — bisher größte Lücke zu Claude Code
   - Kolar: §22 ZustG (Zustellnachweis), §292 ZPO (Beweiskraft)
   - Ullrich: 7 statt 2 RS, §273 ASVG (Berufsunfähigkeit Angestellte)
3. **Alle Streams balanced**: Grok nutzt alle 3 Streams gleichmäßig (Flash Lite hatte oft 1 schwachen Stream)
4. **Kosten verdoppeln sich** ($0.004 → $0.008) — immer noch extrem günstig
5. **Kein Overfitting-Risiko**: Verbesserungen kommen aus besserem Tool-Calling, nicht aus Prompt-Tuning

## Empfehlung

**`grok_worker` als neuer Default für Produktivbetrieb** — die Qualitätssteigerung rechtfertigt die Kostenverdopplung bei weitem.

## Timestamps

- Carmen Grok: `20260226_234103`
- Kolar Grok: `20260226_234549`
- Ullrich Grok: `20260226_234540`
- Carmen Flash: `20260226_233756`
- Kolar Flash: `20260226_230833`
- Ullrich Flash: `20260226_225353`
