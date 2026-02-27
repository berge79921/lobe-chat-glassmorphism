# Hetzner V5b 10-Case Quality Comparison

**Date:** 2026-02-27 | **Profile:** cheap_grok_fast | **MCP:** docker_exec | **Grounding:** postgres_only

## 1. Technical Pass/Fail Summary

| # | Case | Tools | CG | 8-Sect | RS | Time |
|---|------|-------|-----|--------|-----|------|
| 04 | Produkthaftung | 57/57 | PASS | 8/8 | 5 | 100s |
| 05 | Erbrecht/Pflichtteil | 62/62 | PASS | 8/8 | 2 | 113s |
| 06 | Werkvertrag/Mangel | 67/67 | PASS | 8/8 | 6 | 114s |
| 07 | Bereicherung/GmbH | 81/81 | PASS | 8/8 | 10 | 166s |
| 08 | Wrongful Birth | 75/75 | PASS | 8/8 | 11 | 239s |
| 09 | Doppelverkauf | 60/62 | PASS | 8/8 | 5 | 137s |
| 10 | WEG Öltank | 69/69 | PASS | 8/8 | 1 | 249s |
| 11 | Anweisung §1400 | 68/68 | PASS | 8/8 | 8 | 76s |
| 12 | Sicherungszession | 65/65 | PASS | 8/8 | 7 | 230s |
| 13 | Servitut/Nachbar | 72/72 | PASS | 8/8 | 6 | 105s |
| **Σ** | | **676/678** | **10/10** | **80/80** | **61** | **1530s** |

**All 10 cases: technical PASS.** 99.7% tool success. All citation gates passed. All 8 sections present.

---

## 2. Fallübersicht Reference Comparison (3 overlapping cases)

### Case 11 — Anweisung §1400 (KOLAR v. PFEFFER)

| Kriterium | Fallübersicht Referenz | Harness Output | Δ |
|-----------|----------------------|----------------|---|
| **Kern-§§** | §1400, §252/3 ZPO, §7 EO, §290a-301 EO | §1400, §1401 ABGB | Fallübersicht breiter (Exekutionsrecht-Schicht) |
| **RS-Zitate** | 0 | 5 (RS0033170, RS0109097, RS0033084, RS0032998, RS0032933) | **Harness +5 RS** |
| **Subsumtion** | Anweisung + Exekutionsvollstreckung | Anweisung + Annahme-Analyse via Zahlungen | Harness tiefer auf §1400-Dogmatik |
| **Strategie** | 4-Säulen-Exekution (Bank/Pension/Drittschuldner/Fahrnisse) | Zahlungsklage auf EUR 25.000 | Fallübersicht praxisnäher (Vollstreckung) |
| **Risiken** | SWOT (Alter 85, Ausland) | 5 dogmatische Gegenargumente mit Repliken | Komplementär |
| **Bewertung** | ⭐⭐⭐⭐⭐ praxisorientiert | ⭐⭐⭐⭐⭐ juristisch-dogmatisch | **Gleichwertig, unterschiedlicher Fokus** |

**Fazit:** Harness liefert überlegene RS-Grounding (5 präzise RS zu §1400). Fallübersicht hat bessere Exekutions-Praxis. Beide ergänzen sich.

---

### Case 10 — WEG Öltank (Ölaustritt Klein Pöchlarn)

| Kriterium | Fallübersicht Referenz | Harness Output | Δ |
|-----------|----------------------|----------------|---|
| **Kern-§§** | §2/4, §20/2, §24, §28/1/1, §30, §32 WEG 2002 + §1318 ABGB | §833 ABGB (allgemein) | **Fallübersicht massiv besser** |
| **RS-Zitate** | 7 (5 Ob 230/13d, RS0013821, RS0069976, RS0013747, etc.) | 1 (RS0013431) | **Fallübersicht +6 RS** |
| **Subsumtion** | WEG-spezifisch (allgemeiner Teil, Notmaßnahme, Erhaltungspflicht EG) | Generisch (§833 Erhaltungspflicht) | Fallübersicht präziser |
| **Strategie** | 4-Säulen (außerstreitig §30 WEG, einstw. Verfügung, SE Verwalter, Versicherung) | Außerstreit + SE Verwalter + Selbstvornahme | Fallübersicht vollständiger |
| **Umweltrecht** | WRG Grundwassergefährdung erkannt | Nicht erwähnt | Fallübersicht breiter |
| **Bewertung** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | **Fallübersicht klar überlegen** |

**Fazit:** Schwächster Harness-Case. Classifier erkennt WEG-Spezifik nicht — greift auf generisches §833 ABGB statt WEG 2002 zurück. Pre-search findet nur 1 RS statt der 7 relevanten. **Root Cause: Kein WEG-Domain im Classifier + keine WEG-Mandatory-§§.**

---

### Case 05 — Erbrecht/Pflichtteil (Testament Stummer)

| Kriterium | Fallübersicht Referenz | Harness Output | Δ |
|-----------|----------------------|----------------|---|
| **Kern-§§** | §758, §763, §277, §1502 ABGB + Art.22 EuErbVO + §15 BewG | §773, §774, §775, §457, §612 ABGB | Beide valide, unterschiedliche Ansätze |
| **RS-Zitate** | 2 (RS0011827, RS0034302) | 2 (RS0015379, RS0012566) | Gleichwertig (verschiedene RS) |
| **Barwert-Berechnung** | Versicherungsmathematisch, 3 Szenarien, €-Beträge | Erwähnt aber nicht berechnet | Fallübersicht quantitativ besser |
| **Kollisionskurator** | §277 ABGB als kritischer Blocker erkannt | §271 ABGB analog, 50% Erfolg | Beide erkennen das Issue |
| **Verjährung** | §1502 ABGB, 3J ab Kundmachung als offenes Risiko | Nicht erwähnt | Fallübersicht besser |
| **Strategie** | 3 Handlungsoptionen + 7 offene Punkte | Haupt- + Eventualbegehren | Fallübersicht praxisnäher |
| **Bewertung** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Fallübersicht besser** (Quantifizierung + Verjährung) |

**Fazit:** Harness liefert dogmatisch korrektes Gutachten mit guter Struktur. Fallübersicht ist praxisnäher: konkrete Barwert-Szenarien, Verjährungsfrist, offene Punkte-Liste. Der Harness verpasst die Verjährungs-Thematik.

---

## 3. Nicht-Fallübersicht-Cases — Standalone-Qualität

| # | Case | §§-Vollständigkeit | RS-Relevanz | Subsumtion | Strategie | Risiken | Gesamt |
|---|------|-------------------|-------------|------------|-----------|---------|--------|
| 04 | Produkthaftung | 7/10 | 8/10 | 7/10 | 8/10 | 7/10 | **7.4** |
| 06 | Werkvertrag | 9/10 | 9/10 | 9/10 | 8/10 | 8/10 | **8.6** |
| 07 | Bereicherung | 8/10 | 9/10 | 8/10 | 7/10 | 8/10 | **8.0** |
| 08 | Wrongful Birth | 9/10 | 10/10 | 9/10 | 7/10 | 9/10 | **8.8** |
| 09 | Doppelverkauf | 9/10 | 8/10 | 9/10 | 8/10 | 7/10 | **8.2** |
| 12 | Sicherungszession | 8/10 | 8/10 | 8/10 | 8/10 | 8/10 | **8.0** |
| 13 | Servitut/Nachbar | 9/10 | 9/10 | 9/10 | 9/10 | 8/10 | **8.8** |

**Avg (7 standalone):** 8.3/10

## 4. Alle 10 Cases — Gesamtbewertung

| # | Case | Score | Bemerkung |
|---|------|-------|-----------|
| 04 | Produkthaftung | 7.4 | Solide, PHG-Defekt-Analyse könnte tiefer sein |
| 05 | Erbrecht/Pflichtteil | 7.5 | Korrekt aber Verjährung + Barwert fehlen |
| 06 | Werkvertrag/Mangel | 8.6 | Stark: Beweislastumkehr, 6 RS |
| 07 | Bereicherung/GmbH | 8.0 | Gut strukturiert, 10 RS, Evidence-Gaps ehrlich |
| 08 | Wrongful Birth | 8.8 | Beste RS-Dichte (11), realistisch pessimistisch |
| 09 | Doppelverkauf | 8.2 | Textbook §431, sauber |
| 10 | WEG Öltank | 5.5 | Schwach: WEG-§§ verpasst, nur 1 RS |
| 11 | Anweisung §1400 | 8.5 | Stark: 5 präzise RS, 90% Prognose |
| 12 | Sicherungszession | 8.0 | Gut: Besitzkonstitut + Zession korrekt |
| 13 | Servitut/Nachbar | 8.8 | Stark: Dienstbarkeit + actio negatoria |
| **Avg** | | **7.9** | |

---

## 5. Root-Cause-Analyse der Schwächen

### WEG-Lücke (Case 10: 5.5/10)
- **Problem:** `DOMAIN_MANDATORY_PARAGRAPHS` hat keinen WEG-Eintrag
- **Folge:** Classifier fällt auf generisches "vertragsrecht" oder unclassified zurück → §833 ABGB statt WEG 2002
- **Fix:** WEG-Domain mit §§ 2, 20, 28, 30, 32 WEG 2002 + Subdomains (Heizung, Erhaltung)

### Erbrecht-Verjährung (Case 05: 7.5/10)
- **Problem:** Verjährungs-§§ (§1502 ABGB, 3J-Frist) nicht in mandatory_paragraphs für Erbrecht
- **Folge:** Worker sucht nicht nach Verjährungs-RS → kritische Frist unerwähnt
- **Fix:** §1502 ABGB in Erbrecht-mandatory + Subdomain "pflichtteil" mit Barwert-Hinweis

### Quantifizierung generell
- **Problem:** Synth-Template fordert keine konkreten EUR-Beträge/Berechnungen
- **Folge:** Harness bleibt bei qualitativer Analyse statt quantitativer Prognose
- **Fix:** Section 8 um "monetäre Dimension" ergänzen (Streitwert, Kostenrisiko)

---

## 6. Vergleich V4 → V5b Hetzner

| Metrik | V4 (3-Case Avg) | V5b Hetzner (10-Case Avg) | Δ |
|--------|-----------------|--------------------------|---|
| Avg Score | 6.2/10 | 7.9/10 | **+1.7** |
| RS per Case | 2.3 | 6.1 | **+3.8** |
| 8-Section Compliance | 0% (6 Sektionen) | 100% | **+100%** |
| Citation Gate Pass | N/A | 100% | - |
| Tool Success Rate | ~95% | 99.7% | **+4.7%** |
| Beweislast-Section | Missing | Present in 10/10 | **New** |
| Erfolgsaussichten | Missing | Present in 10/10 | **New** |

**V5b hebt die Baseline um +1.7 Punkte vs V4.** Die größte Verbesserung kommt durch das 8-Sektionen-Template (Fix 5) und die mandatory paragraphs (Fix 1).

---

## 7. Empfehlungen

1. **WEG-Domain hinzufügen** (höchste Priorität) → würde Case 10 von 5.5 auf ~8.0 heben
2. **Verjährungs-§§ als Pflicht** bei Erbrecht/Pflichtteil → Case 05 von 7.5 auf ~8.5
3. **Quantifizierung im Synth-Template** → EUR-Beträge/Kostenrisiko als Pflichtangabe
4. **default-Profil Vergleich** → 10-Case Benchmark mit default-Profil auf Hetzner wiederholen
