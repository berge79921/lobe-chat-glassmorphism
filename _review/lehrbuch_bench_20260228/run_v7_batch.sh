#!/usr/bin/env bash
# V7 Lehrbuch Benchmark - 5 cases in parallel
# Fixes: citation-gate=repair, fallback search_ogh_rechtssaetze, expanded legal terms
set -eu
HARNESS="/Users/reinhardberger/HCS/lobe-chat-custom/scripts/legalchat_agentic_harness_minimal.py"
OUTDIR="/Users/reinhardberger/HCS/lobe-chat-custom/_review/lehrbuch_bench_20260228"
CASES="/Users/reinhardberger/HCS/_TEST CASES Super Ris"

run_case() {
    local name="$1" query="$2" context_file="$3" outfile="$4"
    echo "[$(date +%H:%M:%S)] START $name"
    python3 "$HARNESS" \
        --query "$query" \
        --context-file "$context_file" \
        --output "$outfile" \
        --mcp-mode remote_ssh \
        --remote-ssh root@46.225.110.68 \
        --remote-mcp-container mcp-zivilrecht \
        --citation-gate-mode repair \
        --verbose 2>&1 | tail -3
    echo "[$(date +%H:%M:%S)] DONE $name → $(wc -c < "$outfile") bytes"
}

# Carmen
run_case "carmen" \
  'Fasse den Fall "CARMEN" One-Shot als strategische anwaltliche Ersteinschaetzung zusammen: welche 2-3 Rechtsfragen sind entscheidend? Wie sind EO-/Praeklusion-/Interzessions-Aspekte zu priorisieren? Welche Schritte bringen kurzfristig den groessten Nutzen? Nenne die wichtigsten RS/TE zur Absicherung.' \
  "$CASES/CARMEN/CASE_DATA.json" \
  "$OUTDIR/carmen_v7.md" &

# Celsius
run_case "celsius" \
  'Gib eine One-Shot-Rekursanalyse zum Fall "MITTER:CELSIUS" mit Schwerpunkt Zustellmaengel: Tragfaehigkeit der Zustellung ohne deutsche Uebersetzung (Art 5 HZUe), Abgabestelle § 17 ZustG, Heilung § 8 ZustG. Welche RS sind einschlaegig? Welche Risiken bestehen?' \
  "$CASES/MITTER:CELSIUS/CASE_DATA.json" \
  "$OUTDIR/celsius_v7.md" &

# Kolar/Pfeffer
run_case "kolar_pfeffer" \
  'Erstelle eine One-Shot-Analyse fuer "KOLAR .:. PFEFFER" zur Abwehr einer Wiedereinsetzung bzw. zur Zustellwirksamkeit. Pruefe § 17 ZustG Hinterlegungszustellung, Beweiskraft des Rueckscheins (§ 292 ZPO), Ortsabwesenheit. Nenne einschlaegige RS.' \
  "$CASES/KOLAR .:. PFEFFER/CASE_DATA.json" \
  "$OUTDIR/kolar_pfeffer_v7.md" &

# Ullrich
run_case "ullrich" \
  'Erstelle eine kompakte anwaltliche Ersteinschaetzung (One-Shot) zum Fall "ULLRICH Zumutbarkeit" mit Fokus auf: 1) tragende Rechtsfragen, 2) relevante Normen/Judikatur, 3) prozessual sinnvolle naechste Schritte, 4) zentrale Risiken/Gegenargumente. Bitte arbeite explizit mit OGH-/RIS-Quellen.' \
  "$CASES/ULLRICH Zumutbarkeit/PV Pension Klage/Klagsentwurf_Ullrich_Invaliditaetspension.md" \
  "$OUTDIR/ullrich_v7.md" &

# Koller/Baumgartner
run_case "koller_baumgartner" \
  'Erstelle eine strategische Ersteinschaetzung zum Fall "Koller : Baumgartner": Wirksamkeit des Widerrufs des bedingten Vergleichs (§ 204 ZPO), Bestand des Werklohnanspruchs (§§ 1151, 1152, 1165 ABGB), DAS-Deckungsfrage. Nenne einschlaegige RS.' \
  "$CASES/Koller : Baumgartner/CASE_DATA.json" \
  "$OUTDIR/koller_baumgartner_v7.md" &

echo "All 5 cases launched. Waiting..."
wait
echo "=== ALL DONE ==="
for f in "$OUTDIR"/*_v7.md; do echo "$(basename "$f"): $(wc -c < "$f") bytes"; done
