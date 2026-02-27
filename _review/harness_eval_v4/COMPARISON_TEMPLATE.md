# Harness V4 vs Claude Code — Vollstaendiger Vergleich

Stand: 27. Februar 2026

## Methodik

| Dimension | Methode |
|-----------|---------|
| **Claude Code (CC)** | Opus 4.6 + MCP-Tools direkt, 29-32 Calls, iterative Vertiefung, gezielte Paragraph- und Schlagwort-Suche |
| **Harness V4** | Grok 4.1 Fast Worker + Qwen Organizer + Gemini Synth, 3 parallele Workstreams, Pre-Search Scatter, Domain Classifier |

**Identische Infrastruktur:** Beide Systeme nutzen dieselbe PostgreSQL-Datenbank (super_ris.rs/te, 105K RS, 109K TE) ueber denselben MCP zivilrecht-server. Der Unterschied liegt ausschliesslich in der Orchestrierung.

## 3 Testfaelle

1. **Arzthaftung** — Peronaeusschaden bei Knieoperation, Tischler, Berufsunfaehigkeit
2. **Gewaehrleistung/Laesio** — Immobilienkauf 320K vs 165K, Schimmel, keine Baubewilligung, gefaelschter Energieausweis
3. **Interzession** — Buergschaft Ehefrau (EUR 150.000), einkommenslos, §25c KSchG-Verletzung, Fahrnisexekution

---

## Dimension 1: Technisch

| Metrik | Harness V4 | Claude Code |
|--------|:---:|:---:|
| Tool-Calls Case 1 | 66 (autom.) | 30 (gezielt) |
| Tool-Calls Case 2 | 67 (autom.) | 32 (gezielt) |
| Tool-Calls Case 3 | 49 (autom.) | 29 (gezielt) |
| Latenz Case 1 | 78s | ~180s |
| Latenz Case 2 | 81s | ~180s |
| Latenz Case 3 | 64s | ~180s |
| Deep-Dive RS (get/hot_rs_lookup) | 15/15/15 | 20/14/15 |
| Tool OK Rate | 100% | 93% (2x 0-Treffer FTS, 1x Auth-Error) |
| Unique Queries | ~27/Case | ~25/Case |

**Analyse:** Der Harness macht doppelt so viele Tool-Calls, da er 3 parallele Worker-Streams betreibt. Viele Calls sind aber redundant (dieselben Suchbegriffe in verschiedenen Streams). CC macht weniger, aber jeder Call ist gezielt und informiert den naechsten. CC braucht ~2x laenger, produziert aber 4-5x mehr Output.

## Dimension 2: Kosten

| Metrik | Harness V4 | Claude Code |
|--------|:---:|:---:|
| Kosten/Query | ~$0.007 | ~$2-5 |
| Faktor | 1x | ~400-700x |
| 1000 Queries/Monat | $7 | $2.000-5.000 |

**Analyse:** Der Kostenvorteil des Harness ist enorm (Faktor 400-700x). Fuer Volumen-Anwendungen (Chat, Q&A) ist der Harness die einzige wirtschaftliche Option. CC ist ein Premium-Tool fuer Einzelfallanalysen.

## Dimension 3: Funktional (RS-Coverage)

| Metrik | Harness V4 | Claude Code | Faktor |
|--------|:---:|:---:|:---:|
| RS in Answer Case 1 | 9 | 15 | 1.7x |
| RS in Answer Case 2 | 7 | 20 | 2.9x |
| RS in Answer Case 3 | 8 | 23 | 2.9x |
| **RS Total** | **24** | **58** | **2.4x** |
| Antwort-Chars Case 1 | 4,677 | 21,748 | 4.6x |
| Antwort-Chars Case 2 | 3,886 | 24,852 | 6.4x |
| Antwort-Chars Case 3 | 4,357 | 23,661 | 5.4x |
| **Chars Total** | **12,920** | **70,261** | **5.4x** |

**Analyse:** CC liefert 2.4x mehr RS-Zitate und 5.4x laengere Antworten. Entscheidend ist aber nicht die Menge, sondern die **Qualitaet** — siehe Dimension 4.

---

## Dimension 4: Juristische Qualitaet (HAUPTDIMENSION)

### Bewertungskriterien

| Kriterium | Gewicht | Beschreibung |
|-----------|:---:|-------------|
| Anspruchsgrundlagen-Vollstaendigkeit | 25% | Alle relevanten §§ geprueft? |
| RS-Relevanz | 20% | Sind die zitierten RS tatsaechlich einschlaegig? |
| Subsumtionsqualitaet | 25% | Korrekte Anwendung auf den Sachverhalt? |
| Prozessstrategie | 15% | Praktisch umsetzbare Empfehlungen? |
| Risikoanalyse | 15% | Gegenargumente erkannt und eingeordnet? |

---

### Case 1: Arzthaftung

| Kriterium | Harness V4 | Claude Code | Gewinner |
|-----------|:---:|:---:|:---:|
| §§-Vollstaendigkeit | 6/10 | 9/10 | **CC** |
| RS-Relevanz | 7/10 | 9/10 | **CC** |
| Subsumtion | 6/10 | 9/10 | **CC** |
| Strategie | 5/10 | 9/10 | **CC** |
| Risiken | 6/10 | 9/10 | **CC** |
| **Gesamt (gewichtet)** | **6.1/10** | **9.0/10** | **CC (+2.9)** |

**Harness-Defizite Case 1:**
- **§1299 ABGB fehlt** — die zentrale Norm fuer den erhoehten Sorgfaltsmassstab bei Aerzten wurde nicht gefunden. CC identifiziert §1299 als Kernnorm und baut die gesamte Analyse darauf auf.
- **Keine Dual-Track-Strategie** — Harness trennt nicht zwischen Kunstfehler und Aufklaerungsfehler. CC erarbeitet zwei separate Anspruchsstrecken mit **unterschiedlicher Beweislast** (entscheidend fuer die Praxis!).
- **Keine Beweislastanalyse** — RS0026478 (keine Beweislastumkehr bei Kunstfehler) fehlt. CC erkennt dies als Schluesselrisiko und empfiehlt deshalb die doppelgleisige Strategie.
- **Nur 2 Risiken** (hypothetische Einwilligung + Kausalitaet) vs. CC mit 5 detaillierten Risiken inkl. Repliken.
- **Kein Streitwert**, keine Beweisantraege, keine Zustaendigkeitsanalyse.

**CC-Staerken Case 1:**
- 15 RS mit je 1-Satz-Zusammenfassung in strukturierter Tabelle
- Doppelgleisige Strategie (Kunstfehler + Aufklaerungsfehler) — genau so wuerde ein erfahrener Anwalt vorgehen
- Detaillierte Beweisantraege-Tabelle (8 Beweismittel mit Beweisthemen)
- Erfolgsaussichten pro Aspekt (60-90%), Gesamteinschaetzung 70-80%
- Empfohlener Streitwert: EUR 80.000-150.000

---

### Case 2: Gewaehrleistung/Laesio

| Kriterium | Harness V4 | Claude Code | Gewinner |
|-----------|:---:|:---:|:---:|
| §§-Vollstaendigkeit | 7/10 | 10/10 | **CC** |
| RS-Relevanz | 7/10 | 10/10 | **CC** |
| Subsumtion | 7/10 | 9/10 | **CC** |
| Strategie | 5/10 | 10/10 | **CC** |
| Risiken | 6/10 | 9/10 | **CC** |
| **Gesamt (gewichtet)** | **6.6/10** | **9.6/10** | **CC (+3.0)** |

**Harness-Staerke Case 2:**
- Korrekte LE-Berechnung: 165K vs. 160K Grenze, knapp nicht erfuellt — richtig erkannt!
- RS0024085 (Konkurrenz GWL/LE) gefunden

**Harness-Defizite Case 2:**
- **§874 ABGB (List) fehlt** — bei einem gefaelschten Energieausweis ist arglistige Taeuschung die staerkste Anspruchsgrundlage. CC baut eine komplette List-Argumentation mit 5 RS (RS0016301, RS0025334, RS0107864, RS0016298, RS0120502).
- **Keine Anspruchskonkurrenz** — Harness erwaehnt GWL, Irrtum und LE nebeneinander, aber ordnet sie nicht in ein Haupt-/Eventualbegehren-System ein. CC strukturiert 5 Eventualbegehren in korrekter Prioritaet.
- **§928 ABGB (verborgene Maengel)** nur oberflaechlich — CC zitiert RS0022021 (Erkennbarkeit) und RS0018555 (arglistiges Verschweigen).
- **Fehlende prozessuale Massnahmen** — CC empfiehlt einstweilige Verfuegung, Streitanmerkung (§61 GBG), Strafanzeige §223 StGB.
- **Keine Verjaehrungsanalyse** — CC unterscheidet §933 (GWL 3J), §1487 (Irrtum 3J), §1489 (SE, RS0120502).

**CC-Staerken Case 2:**
- 20 RS in strukturierter Tabelle mit Kernaussage + Relevanz
- 5-stufiges Klagebegehren (List → Irrtum → Wandlung → Preisminderung → LE)
- Relative Berechnungsmethode (RS0110929): 320K x (165K/320K) = 155K Minderung
- 6 Risiken mit detaillierten Gegenargumenten
- Erfolgsaussichten pro Anspruchsgrundlage (40-90%)

---

### Case 3: Interzession

| Kriterium | Harness V4 | Claude Code | Gewinner |
|-----------|:---:|:---:|:---:|
| §§-Vollstaendigkeit | 5/10 | 10/10 | **CC** |
| RS-Relevanz | 7/10 | 10/10 | **CC** |
| Subsumtion | 6/10 | 9/10 | **CC** |
| Strategie | 5/10 | 9/10 | **CC** |
| Risiken | 6/10 | 9/10 | **CC** |
| **Gesamt (gewichtet)** | **5.8/10** | **9.4/10** | **CC (+3.6)** |

**Harness-Staerke Case 3:**
- RS0121054 (Haftungsentfall ex lege) korrekt gefunden — die wichtigste RS
- RS0120256 (Beweislast bei Bank) richtig eingeordnet

**Harness-Defizite Case 3:**
- **§879 ABGB (Sittenwidrigkeit) fehlt komplett** — die zweite zentrale Verteidigungslinie bei Angehoerigenburgschaften. CC baut ein komplettes bewegliches System auf (RS0048300, RS0048309, RS0048312, RS0113490, RS0115167).
- **§25d KSchG (Maessigung) fehlt** — das Auffangnetz, wenn Sittenwidrigkeit und Haftungsentfall scheitern. CC analysiert dies als drittes Verteidigungslevel.
- **RS0115167 fehlt** — der Leit-RS zur einkommenslosen Hausfrau ("wirtschaftliche Abhaengigkeit hebt Eigeninteresse auf"). Exakt auf diesen Sachverhalt zugeschnitten.
- **Keine prozessuale Strukturierung** — Harness erwaehnt Oppositionsklage und "Antrag auf Aufschiebung", aber ohne Zuordnung. CC strukturiert 4 Optionen in korrekter Reihenfolge: (1) §42 EO Aufschiebung sofort, (2) §146 ZPO Wiedereinsetzung, (3) §35 EO Oppositionsklage, (4) §25d Maessigung.
- **Praeklusionsproblem nicht erkannt** — CC analysiert ausfuehrlich, ob Einwendungen im Oppositionsverfahren praekludiert sind (groesster prozessualer Risikopunkt).

**CC-Staerken Case 3:**
- 23 RS in 4 thematischen Tabellen (Sittenwidrigkeit, §25c, §25d, Buergschaft allgemein)
- Triple-Defense: §879 Nichtigkeit + §25c Haftungsentfall + §25d Maessigung
- RS0048300 (40 TE, Tier 1) als Leit-RS zur Sittenwidrigkeitspruefung
- Praeklusionsanalyse mit differenzierter Replik (streitiger vs. nicht-streitiger Titel)
- 5 Risiken mit konkreten Repliken
- Erfolgsaussicht 65-80% mit Differenzierung pro Rechtsgrundlage

---

## Gesamtergebnis

### Juristische Qualitaet (Durchschnitt aller Cases)

| System | Case 1 | Case 2 | Case 3 | **Durchschnitt** |
|--------|:---:|:---:|:---:|:---:|
| **Harness V4** | 6.1 | 6.6 | 5.8 | **6.2/10** |
| **Claude Code** | 9.0 | 9.6 | 9.4 | **9.3/10** |
| **Delta** | +2.9 | +3.0 | +3.6 | **+3.1** |

### Kosten-Qualitaets-Verhaeltnis

| Metrik | Harness V4 | Claude Code |
|--------|:---:|:---:|
| Kosten/Query | $0.007 | ~$3.50 |
| Qualitaet | 6.2/10 | 9.3/10 |
| Qualitaet/Dollar | 886/$ | 2.66/$ |
| **Break-Even** | — | **3.1 Qualitaetspunkte fuer 500x Mehrkosten** |

---

## Fehlertypen-Analyse

### Systematische Harness-Defizite

| Fehlertyp | Haeufigkeit | Ursache | Behebbar? |
|-----------|:-----------:|---------|:---------:|
| **Fehlende Zentralnorm** | 3/3 Cases | Worker suchen breit statt tief | Teilweise |
| **Keine Anspruchskonkurrenz** | 3/3 Cases | Synth kann nicht priorisieren | Schwer |
| **Keine Eventualbegehren** | 3/3 Cases | Kein Prozessrecht-Wissen im Prompt | Mittel |
| **Oberflaechliche Risiken** | 3/3 Cases | max_tokens/Synth-Budget zu klein | Einfach |
| **Fehlende Beweislastanalyse** | 2/3 Cases | Kein Konzept von "Track A vs Track B" | Schwer |
| **Kein Streitwert/Zustaendigkeit** | 3/3 Cases | Nicht im Synth-Template | Einfach |

### CC-Muster (konsistent ueber alle Cases)

- Paragraph-getriebene Suche (§→RS→Subsumtion)
- Deep-Dive auf jeden gefundenen RS (hot_rs_lookup)
- Iterative Vertiefung: Fund A fuehrt zu Suche B
- Strukturierte Risiko-Replik-Paare
- Prozessuale Empfehlungen mit konkreter Reihenfolge

---

## Fazit

### Kann man mit dem Harness V4 gewinnende Schriftsaetze schreiben?

**Nein — nicht in der aktuellen Form.**

Ein gewinnender Schriftsatz erfordert:
1. **Vollstaendige Anspruchsgrundlagen** — der Harness verpasst in jedem Fall mindestens eine zentrale Norm (§1299, §874, §879)
2. **Strukturierte Eventualbegehren** — der Harness liefert keine klare Haupt-/Eventualstruktur
3. **Beweislastanalyse** — ohne Verstaendnis der Beweislastverteilung kann kein Anwalt strategisch planen
4. **Risikoeinschaetzung mit Repliken** — der Harness nennt Risiken, aber keine Gegenstrategien

Ein Anwalt, der den Harness-Output als alleinige Grundlage nimmt, wuerde in Case 1 die doppelgleisige Strategie versaeumen, in Case 2 die List-Argumentation uebersehen, und in Case 3 die Sittenwidrigkeit nicht vorbringen — alles potenzielle Verfahrensfehler.

### Kann man mit Claude Code gewinnende Schriftsaetze schreiben?

**Ja — als qualifizierter Ausgangspunkt.**

Die CC-Gutachten erreichen in allen 3 Cases Qualitaet 9+/10. Sie enthalten:
- Vollstaendige Anspruchsgrundlagen mit korrekter Priorisierung
- Alle zentralen OGH-Rechtssaetze mit Kernaussagen
- Detaillierte Subsumtion auf den konkreten Sachverhalt
- Prozessstrategie mit Haupt-/Eventualbegehren
- Risiken mit konkreten Gegenargumenten
- Erfolgsaussichten pro Aspekt

Ein erfahrener Anwalt koennte diese Gutachten als **Briefing-Dokument** verwenden und daraus einen Schriftsatz entwickeln. Die RS-Recherche ist solide, die Struktur entspricht der FANA-Methodik.

### Kann man damit Berufungen gewinnen?

**CC: Ja, als Recherche-Grundlage.** Die RS-Tiefe und die systematische Abdeckung aller Anspruchsgrundlagen bieten eine starke Basis. Die Identifikation von RS0115167 (einkommenslose Hausfrau) oder RS0110820 (Rechtsmangel Baubewilligung) zeigt, dass CC fallrelevante Judikatur findet, die ein Anwalt manuell Stunden suchen wuerde.

**Harness V4: Nicht als alleinige Quelle.** Die Luecken (fehlende §§, keine Beweislastanalyse, oberflaechliche Risiken) waeren in einer Berufungsschrift fatal. Als **erste Orientierung** ("gibt es OGH-Judikatur zu diesem Thema?") ist der Harness aber nuetzlich.

### Empfehlung

**Zwei-Stufen-Modell:**

| Stufe | System | Use Case | Kosten |
|-------|--------|----------|--------|
| **Stufe 1: Triage** | Harness V4 | Ersteinschaetzung, RS-Screening, Q&A-Chat | $0.007/Query |
| **Stufe 2: Gutachten** | Claude Code | Vollstaendige Fallanalyse, Schriftsatz-Vorbereitung | $3-5/Query |

Der Harness V4 ist ein **Screening-Tool** — er findet die richtige Richtung, aber nicht die volle Tiefe. Claude Code ist ein **Analyse-Tool** — es liefert die Qualitaet, die ein Anwalt fuer einen Schriftsatz braucht.

**Fuer die Praxis:** Harness fuer 95% der Anfragen (schnelle Einschaetzung), CC fuer die 5% die einen Schriftsatz oder eine Berufung begruenden muessen.

### Verbesserungspotenzial Harness V5

Die drei wirkungsvollsten Massnahmen:
1. **Structured Legal Reasoning im Synth-Prompt** — erzwinge Anspruchsgrundlagen-Hierarchie (Haupt/Eventual)
2. **Mandatory §-Paragraph-Search pro erkanntem Rechtsgebiet** — der Domain Classifier erkennt "Arzthaftung", aber die Worker suchen nicht nach §1299 ABGB
3. **Beweislast-Analyse als eigener Synth-Block** — "Wer muss was beweisen?" als Pflichtsektion
