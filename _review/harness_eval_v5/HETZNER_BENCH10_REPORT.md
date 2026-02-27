# Hetzner V5b 10-Case Benchmark Report
Profile: cheap_grok_fast | MCP: docker_exec | Citation Gate: enforce | Grounding: postgres_only

| # | Case | Domain | RS | Tools | CG | Secs | 8-Sect |
|---|------|--------|-----|-------|-----|------|--------|
| 04 | Produkthaftung | SE/PHG | 5 | 57/57 | PASS | 100 | 8/8 |
| 05 | Erbrecht/Pflichtteil | Erbrecht | 2 | 62/62 | PASS | 113 | 8/8 |
| 06 | Werkvertrag/Mangel | SE/VR | 6 | 67/67 | PASS | 114 | 8/8 |
| 07 | Bereicherung/GmbH | BE/SR | 10 | 81/81 | PASS | 166 | 8/8 |
| 08 | Wrongful Birth | SE/Arzt | 11 | 75/75 | PASS | 239 | 8/8 |
| 09 | Doppelverkauf | Sachenrecht | 5 | 60/62 | PASS | 137 | 8/8 |
| 10 | WEG Öltank | WEG/VR | 1 | 69/69 | PASS | 249 | 8/8 |
| 11 | Anweisung §1400 | VR/EX | 8 | 68/68 | PASS | 76 | 8/8 |
| 12 | Sicherungszession | VR/SR | 7 | 65/65 | PASS | 230 | 8/8 |
| 13 | Servitut/Nachbar | Sachenrecht | 6 | 72/72 | PASS | 105 | 8/8 |
| **Σ** | | | **61** | **676/678** | ALL PASS | **1530** | |

**Avg per case:** 6.1 RS, 68 tools, 153s
**Tool success rate:** 99.7%
**All 10 cases: OK** | All 8 sections present | All citation gates passed

## Domain Coverage
Schadenersatz (3), Sachenrecht (2), Vertragsrecht (3), Erbrecht (1), Bereicherungsrecht (1), WEG (1), Exekution (1)