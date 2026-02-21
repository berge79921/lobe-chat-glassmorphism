#!/bin/bash
# sync_data_to_hetzner.sh — Full corpus transfer: Local -> Hetzner
# 29 verified sources across 4 tiers, ~21.6 GB uncompressed (~7 GB compressed)
# Verified paths: 2026-02-21

set -euo pipefail

# ==========================================
# CONFIGURATION
# ==========================================
HETZNER_HOST="${HETZNER_HOST:-1.2.3.4}"
HETZNER_USER="${HETZNER_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
REMOTE_STAGING_DIR="${REMOTE_STAGING_DIR:-/mnt/data/super-ris-artifacts}"
DRY_RUN=""
TIER_FILTER=""  # empty = all tiers

RSYNC_OPTS="-avzPh --stats --delete"
SSH_CMD="ssh -p ${SSH_PORT}"

# Local base directory (auto-detect from script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HCS_BASE="${HCS_BASE:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --dry-run       Show what would be transferred (rsync -n)
  --tier N        Only sync tier N (1-4), default: all
  --host HOST     Hetzner host (default: \$HETZNER_HOST or 1.2.3.4)
  --user USER     SSH user (default: \$HETZNER_USER or root)
  --base DIR      Local HCS base directory (default: auto-detect)
  -h, --help      Show this help

Examples:
  $(basename "$0") --dry-run                    # Preview all transfers
  $(basename "$0") --tier 1                     # Only core courts
  $(basename "$0") --tier 3 --dry-run           # Preview EU/international
  $(basename "$0") --host 5.6.7.8 --user deploy # Custom target
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)  DRY_RUN="-n"; shift ;;
    --tier)     [[ $# -lt 2 ]] && { echo "ERROR: --tier requires an argument (1-4)"; exit 1; }
                TIER_FILTER="$2"; shift 2 ;;
    --host)     [[ $# -lt 2 ]] && { echo "ERROR: --host requires an argument"; exit 1; }
                HETZNER_HOST="$2"; shift 2 ;;
    --user)     [[ $# -lt 2 ]] && { echo "ERROR: --user requires an argument"; exit 1; }
                HETZNER_USER="$2"; shift 2 ;;
    --base)     [[ $# -lt 2 ]] && { echo "ERROR: --base requires an argument"; exit 1; }
                HCS_BASE="$2"; shift 2 ;;
    -h|--help)  usage ;;
    *)          echo "Unknown option: $1"; usage ;;
  esac
done

# Validate --tier value
if [[ -n "$TIER_FILTER" && ! "$TIER_FILTER" =~ ^[1-4]$ ]]; then
  echo "ERROR: --tier must be 1, 2, 3, or 4 (got: '${TIER_FILTER}')"
  exit 1
fi

if [[ -n "$DRY_RUN" ]]; then
  RSYNC_OPTS="${RSYNC_OPTS} -n"
  echo "[DRY-RUN MODE] No data will be transferred."
fi

REMOTE="${HETZNER_USER}@${HETZNER_HOST}"
TIER_TOTAL_FILES=0
TIER_SYNCED=0

# ==========================================
# HELPER
# ==========================================
sync_corpus() {
  local label="$1"
  local src="$2"
  local dst="$3"
  local desc="$4"

  if [[ ! -e "$src" ]]; then
    echo "  SKIP  ${label} — source not found: ${src}"
    return
  fi

  echo "--------------------------------------------------------"
  echo "  ${label}: ${desc}"
  echo "  src: ${src}"
  echo "  dst: ${REMOTE_STAGING_DIR}/${dst}"
  rsync $RSYNC_OPTS -e "$SSH_CMD" "${src}" "${REMOTE}:${REMOTE_STAGING_DIR}/${dst}"
  TIER_SYNCED=$((TIER_SYNCED + 1))
}

# ==========================================
# PRE-FLIGHT
# ==========================================
echo "==========================================================="
echo "DATA SYNC TO HETZNER — Full Corpus Transfer"
echo "Target: ${REMOTE}:${REMOTE_STAGING_DIR}"
echo "Base:   ${HCS_BASE}"
echo "Tiers:  ${TIER_FILTER:-all}"
[[ -n "$DRY_RUN" ]] && echo "Mode:   DRY-RUN"
echo "==========================================================="

# Verify HCS_BASE
if [[ ! -d "${HCS_BASE}/TE_ENRICHED" ]]; then
  echo "ERROR: HCS_BASE (${HCS_BASE}) does not contain TE_ENRICHED/. Check --base."
  exit 1
fi

echo "Phase 1: Pre-flight checks..."
echo "[1/3] Checking remote disk space (need >50 GB free)..."
$SSH_CMD "${REMOTE}" "mkdir -p ${REMOTE_STAGING_DIR} && df -h ${REMOTE_STAGING_DIR}"

echo "[2/3] Creating remote directory structure..."
ALL_DIRS="ogh_zivil_te ogh_straf_te vwgh_rs vwgh_te ogh_rs straf_te"
ALL_DIRS+=" vfgh_te vfgh_rs bfg_te ufs_te lvwg_te olg_te lg_te ausl_te bvwg_te dsb_enriched dsb_te dsb_rs"
ALL_DIRS+=" curia_enriched curia_p3 curia_p25 curia_consolidated curia_db egmr_enriched egmr_extracted"
ALL_DIRS+=" normen ogh_zivil_story egmr"
$SSH_CMD "${REMOTE}" "mkdir -p ${REMOTE_STAGING_DIR}/{${ALL_DIRS// /,}}"

echo "[3/3] Pre-flight complete."
if [[ -z "$DRY_RUN" ]]; then
  echo ""
  echo "Transfer ~7 GB compressed. Press ENTER to continue or Ctrl+C to abort."
  read -r
fi

# ==========================================
# TIER 1 — Core Austrian Courts (~9.4 GB)
# ==========================================
if [[ -z "$TIER_FILTER" || "$TIER_FILTER" == "1" ]]; then
  echo ""
  echo "========== TIER 1: Core Austrian Courts =========="

  sync_corpus "T1.1 OGH Zivil TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/ZIVIL_CANONICAL/" \
    "ogh_zivil_te/" \
    "109,559 files, ~428 MB"

  sync_corpus "T1.2 OGH Straf TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/STRAF/" \
    "ogh_straf_te/" \
    "37,583 files, ~147 MB"

  sync_corpus "T1.3 VwGH RS" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/VWGH_RS/" \
    "vwgh_rs/" \
    "350,499 files, ~2.6 GB"

  sync_corpus "T1.4 VwGH TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21_pilot/VWGH_v3/" \
    "vwgh_te/" \
    "137,803 files, ~1.0 GB"

  sync_corpus "T1.5 OGH RS (all, recursive)" \
    "${HCS_BASE}/RIS_ZIVIL_extractions/" \
    "ogh_rs/" \
    "478K JSON across year-dirs, ~4.6 GB"

  sync_corpus "T1.6 Straf TE (alt, recursive)" \
    "${HCS_BASE}/SUPER_RIS_CRIMINAL/" \
    "straf_te/" \
    "61K JSON across year-dirs, ~592 MB"

  echo "========== TIER 1 complete =========="
fi

# ==========================================
# TIER 2 — Secondary Austrian Courts (~1.3 GB)
# ==========================================
if [[ -z "$TIER_FILTER" || "$TIER_FILTER" == "2" ]]; then
  echo ""
  echo "========== TIER 2: Secondary Austrian Courts =========="

  sync_corpus "T2.1 VfGH TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/VFGH/" \
    "vfgh_te/" \
    "20,445 files, ~475 MB"

  sync_corpus "T2.2 VfGH RS" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/VFGH_RS/" \
    "vfgh_rs/" \
    "23,852 files, ~131 MB"

  sync_corpus "T2.3 BFG TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/BFG/" \
    "bfg_te/" \
    "36,345 files, ~143 MB"

  sync_corpus "T2.4 UFS TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/UFS/" \
    "ufs_te/" \
    "46,254 files, ~181 MB"

  sync_corpus "T2.5 LVwG TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/LVWG/" \
    "lvwg_te/" \
    "41,912 files, ~168 MB"

  sync_corpus "T2.6 OLG TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/OLG/" \
    "olg_te/" \
    "8,991 files, ~35 MB"

  sync_corpus "T2.7 LG TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/LG/" \
    "lg_te/" \
    "1,208 files, ~5 MB"

  sync_corpus "T2.8 AUSL TE" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/AUSL/" \
    "ausl_te/" \
    "2,065 files, ~8 MB"

  sync_corpus "T2.9 BVwG TE (enriched)" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/BVWG/" \
    "bvwg_te/" \
    "1,503 files, ~63 MB"

  sync_corpus "T2.10 DSB enriched" \
    "${HCS_BASE}/RIS_DSB/enriched/" \
    "dsb_enriched/" \
    "1,559 files, ~49 MB"

  sync_corpus "T2.11 DSB TE source" \
    "${HCS_BASE}/RIS_DSB/TE/" \
    "dsb_te/" \
    "1,561 files, ~30 MB"

  sync_corpus "T2.12 DSB RS source" \
    "${HCS_BASE}/RIS_DSB/RS/" \
    "dsb_rs/" \
    "234 files, ~5 MB"

  echo "========== TIER 2 complete =========="
fi

# ==========================================
# TIER 3 — EU / International (~10.0 GB)
# ==========================================
if [[ -z "$TIER_FILTER" || "$TIER_FILTER" == "3" ]]; then
  echo ""
  echo "========== TIER 3: EU / International =========="

  sync_corpus "T3.1 CURIA enriched (V4)" \
    "${HCS_BASE}/RIS_EU/CURIA/enriched_mimo_v4_production/" \
    "curia_enriched/" \
    "78,094 files, ~545 MB"

  sync_corpus "T3.2 CURIA p3 refs" \
    "${HCS_BASE}/RIS_EU/CURIA/p3_production/" \
    "curia_p3/" \
    "74,011 files, ~357 MB"

  sync_corpus "T3.3 CURIA p25 prelim" \
    "${HCS_BASE}/RIS_EU/CURIA/p25_production/" \
    "curia_p25/" \
    "74,011 files, ~321 MB"

  sync_corpus "T3.4 CURIA consolidated" \
    "${HCS_BASE}/RIS_EU/CURIA/consolidated/" \
    "curia_consolidated/" \
    "3 files, ~6.5 GB"

  sync_corpus "T3.5 CURIA DB schema" \
    "${HCS_BASE}/RIS_EU/CURIA/db/" \
    "curia_db/" \
    "5 SQL files"

  sync_corpus "T3.6 EGMR enriched" \
    "${HCS_BASE}/RIS_EU/EGMR_ENRICHED/" \
    "egmr_enriched/" \
    "65 files, ~266 MB"

  sync_corpus "T3.7 EGMR extracted" \
    "${HCS_BASE}/RIS_EU/EGMR_EXTRACTED/" \
    "egmr_extracted/" \
    "65 files, ~2.0 GB"

  echo "========== TIER 3 complete =========="
fi

# ==========================================
# TIER 4 — Supplementary (~0.9 GB)
# ==========================================
if [[ -z "$TIER_FILTER" || "$TIER_FILTER" == "4" ]]; then
  echo ""
  echo "========== TIER 4: Supplementary =========="

  sync_corpus "T4.1 Normen DuckDB" \
    "${HCS_BASE}/RIS_NORMEN/db/legal_norms.duckdb" \
    "normen/legal_norms.duckdb" \
    "1 file, ~63 MB"

  # Sync JSON caches individually
  for f in para_cache.json rs_cache.json rs_te_cache.json te_cache_v3.json te_cache.json; do
    if [[ -f "${HCS_BASE}/RIS_NORMEN/db/${f}" ]]; then
      rsync $RSYNC_OPTS -e "$SSH_CMD" \
        "${HCS_BASE}/RIS_NORMEN/db/${f}" \
        "${REMOTE}:${REMOTE_STAGING_DIR}/normen/${f}"
    fi
  done

  sync_corpus "T4.2 Zivil Story" \
    "${HCS_BASE}/TE_ENRICHED/grok_v21/ZIVIL_STORY/" \
    "ogh_zivil_story/" \
    "110,738 files, ~835 MB"

  sync_corpus "T4.3 EGMR Master Export" \
    "${HCS_BASE}/RIS_EU/EGMR_MASTER_EXPORT.jsonl" \
    "egmr/EGMR_MASTER_EXPORT.jsonl" \
    "1 file, ~176 MB"

  echo "========== TIER 4 complete =========="
fi

# ==========================================
# VERIFICATION
# ==========================================
echo ""
echo "==========================================================="
echo "TRANSFER COMPLETE. Running remote verification..."
echo "==========================================================="
$SSH_CMD "${REMOTE}" "
echo '=== Remote file counts ==='
for d in ${REMOTE_STAGING_DIR}/*/; do
  name=\$(basename \"\$d\")
  count=\$(find \"\$d\" -type f 2>/dev/null | wc -l)
  printf '  %-25s %s files\n' \"\$name\" \"\$count\"
done
echo ''
echo '=== Total disk usage ==='
du -sh ${REMOTE_STAGING_DIR}
"

echo ""
echo "==========================================================="
echo "NEXT STEPS on Hetzner:"
echo "==========================================================="
echo "1. ssh ${REMOTE}"
echo "2. tmux new -s mcp-import"
echo "3. cd /opt/legalchat/docker"
echo ""
echo "4. Backup DB:"
echo "   docker exec mcp-super-ris-postgres pg_dump -U postgres -d super_ris -Fc -f /tmp/pre_import.dump"
echo ""
echo "5. Import RS first (FK targets):"
echo "   for dir in ogh_rs vwgh_rs vfgh_rs dsb_rs; do"
echo "     docker compose -f docker-compose.yml -f docker-compose.mcp.internal.yml \\"
echo "       --profile mcp-import run --rm mcp-super-ris-rs-importer \\"
echo "       --json-root /srv/super-ris-artifacts/\$dir"
echo "   done"
echo ""
echo "6. Import TE (all courts):"
echo "   for dir in ogh_zivil_te ogh_straf_te vwgh_te vfgh_te bfg_te ufs_te lvwg_te olg_te lg_te ausl_te bvwg_te dsb_te dsb_enriched; do"
echo "     docker compose -f docker-compose.yml -f docker-compose.mcp.internal.yml \\"
echo "       --profile mcp-import run --rm mcp-super-ris-importer \\"
echo "       --json-root /srv/super-ris-artifacts/\$dir"
echo "   done"
echo ""
echo "7. CURIA schema + import (host stdin redirect — paths are HOST paths):"
echo "   for sql in 001_create_curia_schema.sql 002_add_fts_tsvector_column.sql 003_add_french_search_vector.sql 004_create_paragraphs_table.sql 005_create_registry_table.sql; do"
echo "     docker exec -i mcp-super-ris-postgres psql -U postgres -d super_ris < ${REMOTE_STAGING_DIR}/curia_db/\$sql"
echo "   done"
echo ""
echo "8. Rebuild FTS indexes (via container-internal path):"
echo "   docker exec mcp-super-ris-postgres psql -U postgres -d super_ris -f /docker-entrypoint-initdb.d/003_rebuild_fts_indexes.sql"
echo ""
echo "9. Post-import backup:"
echo "   docker exec mcp-super-ris-postgres pg_dump -U postgres -d super_ris -Fc -f /tmp/post_import.dump"
echo "==========================================================="
