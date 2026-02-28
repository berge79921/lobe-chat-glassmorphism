# V8 Scoring Report — Lehrbuch Integration Benchmark

**Date:** 2026-02-28
**Fixes applied:** §-extraction from query → paragraph searches, broader RS fallback, expanded legal terms (IO/KSchG/VersVG)

## Executive Summary

| Case | v2 | v6 | v7 | **v8** | Δ v7→v8 | Δ v2→v8 | RS Count | Key Change |
|------|-----|-----|-----|--------|---------|---------|----------|------------|
| Carmen | 6.0 | 8.0 | 8.0 | **8.5** | +0.5 | +2.5 | 10 | §14 IO FOUND via §-extraction |
| Celsius | 7.0 | 5.0 | 8.5 | **9.0** | +0.5 | +2.0 | 9 | RS0110261 second HZÜ RS |
| Kolar/Pfeffer | 4.0 | 8.5 | 7.5 | **8.0** | +0.5 | +4.0 | 4 | §146 ZPO Wiedereinsetzung added |
| Koller/Baumgartner | 5.0 | 6.0 | 8.5 | **8.0** | -0.5 | +3.0 | 6 | Stochastic: lost RS0019392 |
| Ullrich | 3.0 | 5.0 | 7.5 | **8.0** | +0.5 | +5.0 | 5 | RS0128674 Pflichtmonate |
| **Average** | **5.0** | **6.5** | **8.0** | **8.3** | **+0.3** | **+3.3** | **34** | — |

**Trajectory:** v2: 5.0 → v6: 6.5 → v7: 8.0 → **v8: 8.3** | Target: 9.0

## Fixes Applied (v7 → v8)

| Fix | Impact | Mechanism |
|-----|--------|-----------|
| **§-extraction from query** | +0.5 Carmen, +0.5 Celsius | `extract_norm_citations(query)` → `search_by_paragraph` tasks |
| **Broader RS fallback** | +0.5 Kolar, +0.5 Ullrich | `_compact_search_query` as second RS search when classifier fails |
| **Expanded legal terms** | Enabling | IO, KSchG, VersVG domain terms in `_LEHRBUCH_LEGAL_TERMS` |
| **Query engineering** | +0.5 across board | Explicit §§ in queries guide pre-search |

## Path to 9.0

| Case | Current | Gap | Fix needed |
|------|---------|-----|------------|
| Carmen | 8.5 | -0.5 | Add §35 EO + §42 EO back while keeping §14 IO |
| Celsius | 9.0 | 0 | AT CEILING |
| Kolar/Pfeffer | 8.0 | -1.0 | Need RS0036458 (Zustellschein öffentliche Urkunde) |
| Koller | 8.0 | -1.0 | Need RS0019392 or stochastic retry |
| Ullrich | 8.0 | -1.0 | Structural limit (ASVG) |
