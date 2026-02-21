# Data Sync Strategy — Local to Hetzner

**Last verified:** 2026-02-21
**Script:** `sync_data_to_hetzner.sh`

## Architecture

```
Local (Mac)                    Hetzner
┌──────────────┐    rsync     ┌─────────────────────────────┐
│ HCS/         │ ──────────>  │ /mnt/data/super-ris-artifacts│
│  TE_ENRICHED/│   ~7 GB      │   ogh_zivil_te/             │
│  RIS_ZIVIL_* │   compressed │   vwgh_rs/                  │
│  RIS_EU/     │              │   curia_enriched/           │
│  ...         │              │   ...                       │
└──────────────┘              └──────────┬──────────────────┘
                                         │ Docker importers
                                         ▼
                              ┌─────────────────────────────┐
                              │ PostgreSQL (pgvector:pg16)   │
                              │  super_ris.rs  (RS)         │
                              │  super_ris.te  (TE)         │
                              │  curia.cases   (EU)         │
                              │  curia.paragraphs           │
                              └─────────────────────────────┘
```

## Complete Data Inventory (29 Sources)

### Tier 1 — Core Austrian Courts (~9.4 GB)

| # | Corpus | Local Path | Files | Size | Remote Dir |
|---|--------|-----------|-------|------|------------|
| 1 | OGH Zivil TE | `TE_ENRICHED/grok_v21/ZIVIL_CANONICAL/` | 109,559 | 428M | `ogh_zivil_te/` |
| 2 | OGH Straf TE | `TE_ENRICHED/grok_v21/STRAF/` | 37,583 | 147M | `ogh_straf_te/` |
| 3 | VwGH RS | `TE_ENRICHED/grok_v21/VWGH_RS/` | 350,499 | 2.6G | `vwgh_rs/` |
| 4 | VwGH TE | `TE_ENRICHED/grok_v21_pilot/VWGH_v3/` | 137,803 | 1.0G | `vwgh_te/` |
| 5 | OGH RS (all) | `RIS_ZIVIL_extractions/` | 478,060 | 4.6G | `ogh_rs/` |
| 6 | Straf TE (alt) | `SUPER_RIS_CRIMINAL/` | 61,022 | 592M | `straf_te/` |

### Tier 2 — Secondary Austrian Courts (~1.3 GB)

| # | Corpus | Local Path | Files | Size | Remote Dir |
|---|--------|-----------|-------|------|------------|
| 7 | VfGH TE | `TE_ENRICHED/grok_v21/VFGH/` | 20,445 | 475M | `vfgh_te/` |
| 8 | VfGH RS | `TE_ENRICHED/grok_v21/VFGH_RS/` | 23,852 | 131M | `vfgh_rs/` |
| 9 | BFG TE | `TE_ENRICHED/grok_v21/BFG/` | 36,345 | 143M | `bfg_te/` |
| 10 | UFS TE | `TE_ENRICHED/grok_v21/UFS/` | 46,254 | 181M | `ufs_te/` |
| 11 | LVwG TE | `TE_ENRICHED/grok_v21/LVWG/` | 41,912 | 168M | `lvwg_te/` |
| 12 | OLG TE | `TE_ENRICHED/grok_v21/OLG/` | 8,991 | 35M | `olg_te/` |
| 13 | LG TE | `TE_ENRICHED/grok_v21/LG/` | 1,208 | 5M | `lg_te/` |
| 14 | AUSL TE | `TE_ENRICHED/grok_v21/AUSL/` | 2,065 | 8M | `ausl_te/` |
| 15 | BVwG TE | `TE_ENRICHED/grok_v21/BVWG/` | 1,503 | 63M | `bvwg_te/` |
| 16 | DSB enriched | `RIS_DSB/enriched/` | 1,559 | 49M | `dsb_enriched/` |
| 17 | DSB TE source | `RIS_DSB/TE/` | 1,561 | 30M | `dsb_te/` |
| 18 | DSB RS source | `RIS_DSB/RS/` | 234 | 5M | `dsb_rs/` |

### Tier 3 — EU / International (~10.0 GB)

| # | Corpus | Local Path | Files | Size | Remote Dir |
|---|--------|-----------|-------|------|------------|
| 19 | CURIA enriched (V4) | `RIS_EU/CURIA/enriched_mimo_v4_production/` | 78,094 | 545M | `curia_enriched/` |
| 20 | CURIA p3 refs | `RIS_EU/CURIA/p3_production/` | 74,011 | 357M | `curia_p3/` |
| 21 | CURIA p25 prelim | `RIS_EU/CURIA/p25_production/` | 74,011 | 321M | `curia_p25/` |
| 22 | CURIA consolidated | `RIS_EU/CURIA/consolidated/` | 3 | 6.5G | `curia_consolidated/` |
| 23 | CURIA DB schema | `RIS_EU/CURIA/db/` | 5 | <1M | `curia_db/` |
| 24 | EGMR enriched | `RIS_EU/EGMR_ENRICHED/` | 65 | 266M | `egmr_enriched/` |
| 25 | EGMR extracted | `RIS_EU/EGMR_EXTRACTED/` | 65 | 2.0G | `egmr_extracted/` |

### Tier 4 — Supplementary (~0.9 GB)

| # | Corpus | Local Path | Files | Size | Remote Dir |
|---|--------|-----------|-------|------|------------|
| 26 | Normen DuckDB | `RIS_NORMEN/db/legal_norms.duckdb` | 1 | 63M | `normen/` |
| 27 | Normen caches | `RIS_NORMEN/db/*.json` | 5 | ~10M | `normen/` |
| 28 | Zivil Story | `TE_ENRICHED/grok_v21/ZIVIL_STORY/` | 110,738 | 835M | `ogh_zivil_story/` |
| 29 | EGMR Master | `RIS_EU/EGMR_MASTER_EXPORT.jsonl` | 1 | 176M | `egmr/` |

### Totals

| Tier | Sources | Files | Size |
|------|---------|-------|------|
| Tier 1 Core | 6 | ~1.17M | ~9.4G |
| Tier 2 Secondary | 12 | ~186K | ~1.3G |
| Tier 3 International | 7 | ~226K | ~10.0G |
| Tier 4 Supplementary | 4 | ~111K | ~0.9G |
| **TOTAL** | **29** | **~1.69M** | **~21.6G** |

Transfer compressed: **~7 GB**. Duration: 10-45 min.

## DB Schemas on Hetzner

### `super_ris` schema (deployed)

```sql
super_ris.rs  (rs_number PK)  — OGH RS, VwGH RS, VfGH RS, DSB RS
super_ris.te  (stable_key PK) — all TE from all courts
```

Init scripts: `docker/mcp-super-ris-init/001-003*.sql`
Importers: `import_super_ris_rs.py`, `import_super_ris_te.py`

### `curia` schema (5 SQL files)

```sql
curia.cases              (celex PK)  — EuGH + EuG decisions
curia.preliminary_questions          — preliminary ruling Q&A
curia.case_references                — cross-case citations
curia.eu_law_citations               — EU legal act refs
curia.eu_legal_acts                  — directive/regulation catalog
curia.eu_legal_act_articles          — article-level citations
curia.joined_cases                   — consolidated cases
curia.sync_log                       — import audit trail
curia.paragraphs         (id PK)     — paragraph-level IUROPA text
curia.registry           (case_id PK)— master case registry
```

Schema files: `RIS_EU/CURIA/db/001-005*.sql`
Mounted into Docker init: `docker-compose.mcp.internal.yml`

## Import Sequence (on Hetzner)

```bash
tmux new -s import
cd /opt/legalchat/docker

# 0. Backup
docker exec mcp-super-ris-postgres pg_dump -U postgres -d super_ris -Fc -f /tmp/pre_import.dump

# 1. RS first (FK targets)
for dir in ogh_rs vwgh_rs vfgh_rs dsb_rs; do
  docker compose -f docker-compose.yml -f docker-compose.mcp.internal.yml \
    --profile mcp-import run --rm mcp-super-ris-rs-importer \
    --json-root /srv/super-ris-artifacts/$dir
done

# 2. TE (all courts)
for dir in ogh_zivil_te ogh_straf_te vwgh_te vfgh_te bfg_te ufs_te lvwg_te olg_te lg_te ausl_te bvwg_te dsb_te dsb_enriched; do
  docker compose -f docker-compose.yml -f docker-compose.mcp.internal.yml \
    --profile mcp-import run --rm mcp-super-ris-importer \
    --json-root /srv/super-ris-artifacts/$dir
done

# 3. CURIA schema (host stdin redirect — paths are HOST paths on Hetzner)
for sql in 001_create_curia_schema.sql 002_add_fts_tsvector_column.sql 003_add_french_search_vector.sql 004_create_paragraphs_table.sql 005_create_registry_table.sql; do
  docker exec -i mcp-super-ris-postgres psql -U postgres -d super_ris \
    < /mnt/data/super-ris-artifacts/curia_db/$sql
done

# 4. FTS rebuild (uses container-internal path via -f, not host redirect)
docker exec mcp-super-ris-postgres psql -U postgres -d super_ris \
  -f /docker-entrypoint-initdb.d/003_rebuild_fts_indexes.sql

# 5. Post-import backup
docker exec mcp-super-ris-postgres pg_dump -U postgres -d super_ris -Fc -f /tmp/post_import.dump
```

## Verification Queries

```sql
-- Row counts
SELECT 'rs' AS tbl, count(*) FROM super_ris.rs
UNION ALL SELECT 'te', count(*) FROM super_ris.te;

-- FTS smoke test
SELECT rs_number FROM super_ris.rs
WHERE to_tsvector('german', rechtssatz_volltext) @@ to_tsquery('german', 'Schadenersatz')
LIMIT 5;

-- CURIA (after import)
SELECT count(*) FROM curia.cases;
SELECT count(*) FROM curia.paragraphs;
```

## Not Transferred (by design)

- Raw HTML sources (`RIS_ZIVIL_sources/`, `RIS_DOWNLOADS/`, `RIS_VERWALTUNGSRECHT/RS/`) — ~90 GB, not needed for DB import
- BVwG raw extractions (`RIS_BVWG/`) — 71 GB, only 1,503 enriched files transferred
- VfGH raw (`RIS_VERFASSUNG/`) — 22 GB, enriched versions in Tier 2
- Build artifacts, OCR outputs, training data
