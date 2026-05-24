# V2 → V6 Scoring Report (Lehrbuch Integration Benchmark)

**Date:** 2026-02-28
**5 Cases, v2=baseline (pre-lehrbuch), v6=lehrbuch-integrated**

## Executive Summary

| Case | v2 | v6 | Δ | Lehrbuch Hits | Key Issue |
|------|-----|-----|-----|-----|------|
| Carmen (EO/Interzession) | 6.0 | 8.0 | **+2.0** | 3 | §14 IO correctly identified |
| Kolar/Pfeffer (Zustellung) | 4.0 | 8.5 | **+4.5** | 0 | 5 excellent RS found |
| Koller/Baumgartner (Werklohn) | 5.0 | 6.0 | +1.0 | 6 | Citation gate blocks enforce |
| Ullrich (Zumutbarkeit/PV) | 3.0 | 5.0 | +2.0 | 11 | Case facts unclear |
| Celsius (HZÜ/Zustellung) | 7.0 | 5.0 | **-2.0** | 1 | REGRESSION: lost HZÜ RS |
| **Average** | **5.0** | **6.5** | **+1.5** | — | — |

**Target: 9.0/10 (90%). Current: 6.5/10. Gap: -2.5**

## Per-Case Analysis

### 1. Carmen (EO/Interzession) — v2: 6 → v6: 8 (+2)

**v2 Weaknesses:**
- Wrong legal focus (Zustellungsmängel statt Akzessorietät)
- Missing §14 IO analysis (core issue for Bürgschaft in Insolvenz)
- No §1353 ABGB (Haftungseinschränkung)
- 8 RS but partly misdirected (RS0001544, RS0001557 re Zustellung)

**v6 Improvements:**
- Correctly identifies §14 IO as Kernfrage
- §35 EO Oppositionsklage + §40 EO Einstellung + §1353 ABGB properly analyzed
- Stufenbau: EO-Anträge > Präklusion > Interzession (correct priority)
- 4 RS (RS0001298, RS0001126, RS0001387, RS0000901) — fewer but better targeted

**Missing for 9+:**
- RS0001582 (Akzessorietät Bürgschaft) was in v2 but lost in v6
- §25c/d KSchG analysis remains thin
- Missing concrete oracle RS from Interzession-Recherche

### 2. Kolar/Pfeffer (Zustellwirksamkeit) — v2: 4 → v6: 8.5 (+4.5) ⭐

**v2 Weaknesses:**
- Only 1 RS (RS0000351 — barely relevant, about Revisionsrekurs/Unterhalt)
- "Insufficient evidence" throughout despite clear case facts
- No §292 ZPO (Beweiskraft öffentlicher Urkunden)
- Superficial §17 ZustG analysis

**v6 Improvements:**
- 5 excellent RS: RS0036420, RS0036591, RS0083714, RS0083946, RS0096061
- All RS directly relevant to Zustellwirksamkeit + öffentliche Urkunden
- §292 ZPO (Rückschein als öffentliche Urkunde) properly integrated
- Detailed subsumtion with numbered Tatbestandsmerkmale
- Strong Beweislastverteilung analysis

**Missing for 9+:**
- Could add §7 ZustG Heilung detail
- Fristen/Kosten section still generic

### 3. Koller/Baumgartner (Werklohn/Honorar) — v2: 5 → v6: 6 (+1)

**v2 Weaknesses:**
- Wrong §: §1306 ABGB (doesn't exist for Werkvertrag)
- 3 RS with weak relevance
- Good Widerruf analysis (§204 ZPO)

**v6 (repair) Improvements:**
- Better §§: §1001, §1151, §1167 ABGB (correct Werkvertragsrecht area)
- DAS-Deckung with VersVG references
- Still struggles with RS — no strong Werkvertrags-RS found

**Blocking Issue:** Citation gate `enforce` mode blocks output completely. Repair mode needed.

**Missing for 9+:**
- Need §1152 ABGB (angemessenes Entgelt), §1165 ABGB (Fälligkeit Werklohn)
- RS for Werklohn/Honorar (e.g., RS0021738 Werklohn bei Werkvertrag)
- RS for bedingter Vergleich (§204 ZPO specific RS)

### 4. Ullrich (Zumutbarkeit/PV Pension) — v2: 3 → v6: 5 (+2)

**v2 Weaknesses:**
- WRONG §§: §1331 ABGB, §1330 ABGB (Ehrbeleidigung, completely wrong context)
- "Evidence insufficient" throughout
- 3 RS, barely relevant

**v6 Improvements:**
- Better §§: §1295 ABGB, §1304 ABGB (Schadenminderung), §1299 ABGB
- 5 RS (RS0049175, RS0055230, RS0039382, RS0002551, RS0032776)
- Better structure despite "evidence insufficient"

**Root Cause:** The case is about PV/Invaliditätspension + Zumutbarkeit in sozialrechtlichem Kontext, but the harness keeps routing to allgemeines Schadenersatzrecht. The case facts don't clearly map to OGH-Zivilrecht.

**Missing for 9+:**
- Needs ASVG/SVG references if social law aspect
- If purely SE: §1304 ABGB needs better RS (e.g., RS0027043 Schadenminderungspflicht)
- Case prompt needs clearer facts

### 5. Celsius (HZÜ/Zustellung international) — v2: 7 → v6: 5 (-2) ⚠️ REGRESSION

**v2 Strengths (lost in v6):**
- Art 5 HZÜ as strongest line (correctly identified)
- 5 RS: RS0110261, RS0110260, RS0115027, RS0117046, RS0134713
- §8 ZustG Heilung properly analyzed
- Good stufenbau strategy

**v6 Regression:**
- Lost Art 5 HZÜ focus — replaced with generic "Nichtigkeit via Zustellmängel"
- Only 3 RS: RS0123715, RS0117046, RS0043773 (generic, not HZÜ-specific)
- "Evidence insufficient" appears more often
- Lost RS0110261, RS0110260, RS0134713 (core HZÜ RS)

**Root Cause:** Stochastic routing — workers in v6 didn't query HZÜ-specific tools. Lehrbuch adds nothing here (no HZÜ content).

## Top 3 Fixes for V7

### Fix 1: Citation Gate → Default `repair` mode (Impact: Koller +2)
Currently `enforce` blocks Koller completely. Switch to `repair` as default.

### Fix 2: Pre-search: add `search_ogh_rechtssaetze` with domain-specific queries (Impact: Celsius +2, Ullrich +1)
Currently pre-search only does `build_grounding_context`, `detect_clusters`, `search_lehrbuch`. Add `search_ogh_rechtssaetze` with extracted legal keywords from the query to find domain-specific RS early.

### Fix 3: Organizer prompt — force Art/HZÜ extraction for international cases (Impact: Celsius +2)
Ensure the organizer detects international law markers (HZÜ, HBÜ, EuGVVO, CISG) in case context and routes to appropriate RS searches.

## Projected V7 Scores

| Case | v6 | Fix | Projected v7 |
|------|-----|-----|------|
| Carmen | 8.0 | — | 8.0 |
| Kolar/Pfeffer | 8.5 | — | 8.5 |
| Koller/Baumgartner | 6.0 | Fix 1 | 7.5 |
| Ullrich | 5.0 | Fix 2 | 6.5 |
| Celsius | 5.0 | Fix 2+3 | 7.5 |
| **Average** | **6.5** | — | **7.6** |

Still below 9.0 target. Additional fixes needed in subsequent iterations.
