# Carmen A/B Test — Worker Model Comparison (2026-02-27)

## Test Query
Carmen: Interzession, Exekutionsrecht, §40 EO, §25d KSchG

## Results

| Metrik | Flash Lite (v4) | Grok 4.1 Fast | Claude Code Baseline |
|--------|----------------|---------------|---------------------|
| **Worker Model** | gemini-2.5-flash-lite | x-ai/grok-4.1-fast | — |
| **Tool Calls** | 24 | **54** | ~20 (interactive) |
| **RS Cited** | 5 | **7** | 15+ |
| **Answer Chars** | 4092 | **5128** | — |
| **§40 EO** | YES | YES | YES |
| **§25d KSchG** | YES | YES | YES |
| **§25c KSchG** | NO | **YES** | YES |
| **§879 ABGB** | YES | YES | YES |
| **§35 EO** | YES | YES | YES |
| **Laufzeit** | 132s | **103s** | — |
| **Stream Balance** | 11/2/11 (unbalanced) | 17/15/22 (balanced) | — |
| **Est. Cost** | ~$0.004 | ~$0.008 | — |

## Key Finding: Grok 4.1 Fast findet §25c KSchG

Grok hat eigenständig die **Informationspflicht (§25c KSchG)** und die zugehörige Judikatur (RS0115983) gefunden — das war die größte Lücke zum Claude Code Baseline.

### RS Comparison

| RS | Flash Lite | Grok 4.1 | Baseline |
|----|-----------|----------|----------|
| RS0115165 (§25d Mäßigung) | ✅ | ✅ | ✅ |
| RS0113935 (§25d ≠ §879) | ✅ | ✅ | ✅ |
| RS0115167 (Vermögensloses Eigeninteresse) | ✅ | — | ✅ |
| RS0112840 (Einzelfallabhängig) | ✅ | — | — |
| RS0001126 (§35/§40 EO) | ✅ | — | — |
| RS0113490 (Sittenwidrigkeit Angehörige) | — | ✅ | ✅ |
| RS0115983 (**§25c Informationspflicht**) | — | **✅** | ✅ |
| RS0124086 (Interzessionsbegriff) | — | ✅ | — |
| RS0048300 (Missverhältnis) | — | ✅ | ✅ |
| RS0065238 (Verbrauchereigenschaft) | — | ✅ | — |
| RS0001355 (§40 EO Taxativität) | v3 only | ✅ | ✅ |

## Empfehlung

**Grok 4.1 Fast als Worker ist klar überlegen** bei ~2x Kosten ($0.008 vs $0.004).
Für produktive Nutzung: `grok_worker` Profil empfohlen.
Für Budget-Betrieb: `cheap_default` bleibt viable (alle PASS-Kriterien erfüllt).

## Nächste Tests
- [ ] Kolar mit grok_worker
- [ ] Ullrich mit grok_worker
- [ ] DeepSeek V3.2 als Worker testen
- [ ] MiniMax M2.5 als Worker testen
- [ ] Kimi K2.5 als Worker testen
