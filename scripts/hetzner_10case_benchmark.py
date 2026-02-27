#!/usr/bin/env python3
"""10-case benchmark for Hetzner harness validation."""
import json, os, subprocess, sys, time
from pathlib import Path

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "cheap_grok_fast"
TAG = sys.argv[2] if len(sys.argv) > 2 else "bench10"
OUT = Path(f"/root/harness/results_{TAG}_{PROFILE}")
OUT.mkdir(parents=True, exist_ok=True)

COMMON = [
    "--mcp-mode", "docker_exec",
    "--remote-mcp-container", "mcp-zivilrecht",
    "--config-dir", "config",
    "--model-profile", PROFILE,
    "--citation-gate-mode", "enforce",
    "--grounding-policy", "postgres_only",
]

CASES = {
    "case04_produkthaftung": (
        "Unternehmer X betreibt Weinanbau in Wien. Er bestellt bei Großhändler Y ein Harz zur Ertragssteigerung "
        "der Rebstöcke. Das Harz wurde von Chemiefabrik Z in Linz hergestellt. Nach Aufbringung im Mai werden bis "
        "September sämtliche Rebstöcke zerstört. Neubepflanzungskosten: 500.000 Euro. X verlangt von Y vollen "
        "Schadenersatz. Y wendet ein, das Harz sei von Z fehlerhaft produziert worden. Welche Ansprüche hat X "
        "gegen Y und Z? Greift das PHG?"
    ),
    "case05_erbrecht_pflichtteil": (
        "Ein Erblasser hinterlässt Ehefrau, Sohn und Tochter. Im Testament erhält die Tochter das Eigentum an "
        "einer Wiener Innenstadtliegenschaft (Wert ca. 3-7 Mio EUR). Der Sohn erhält nur ein lebenslängliches "
        "Fruchtgenussrecht an der Hälfte dieser Liegenschaft (kein Eigentum), plus Veräußerungsverbot und "
        "Vorkaufsrecht. Die Ehefrau ist Alleinerbin. Der kapitalisierte Barwert des Fruchtgenusses liegt unter "
        "dem gesetzlichen Pflichtteil von 1/6. Der Sohn ist gleichzeitig Erwachsenenvertreter seiner Mutter "
        "(Alleinerbin). Welche Ansprüche hat der Sohn? Braucht er einen Kollisionskurator?"
    ),
    "case06_werkvertrag": (
        "Karl beauftragt die Ofenbau AG mit dem Einbau eines Kachelofens (EUR 9.000). Die Montage wird durch "
        "Mitarbeiter der Subunternehmerin Allerlei GmbH durchgeführt. Mängel: vergessene Ausschnittslöcher "
        "(Sichtfenster verrußt), Luftschieber schließt nicht, Herdeinsatz fällt beim Reparaturversuch aus der "
        "Halterung. Ein Sachverständiger stellt fest, dass ein kompletter Neuaufbau nötig ist (Kosten EUR 10.000 "
        "über Marktwert). Bei der Demontage wird der Ofen mit Gabelstapler statt Kran transportiert – Mitarbeiter "
        "hatten es eilig wegen Feierabend. Dabei entsteht zusätzlicher Gebäudeschaden. Welche Ansprüche hat Karl "
        "gegen die Ofenbau AG?"
    ),
    "case07_bereicherung": (
        "Hannes Grubmair lässt nach einem Unfall seinen PKW günstig vom Freund reparieren und gibt ihn der "
        "Gebrauchtwagen-GmbH (Geschäftsführerin Paula Gabler) zum Weiterverkauf. Vereinbart: Bei Verkauf erhält "
        "Grubmair EUR 17.000. Die GmbH verkauft den PKW an Marius um EUR 22.000 mit Kreditkarte. Marius fährt "
        "auf eine Tankstelle und tankt um EUR 80, fährt ohne zu zahlen davon. Ein Jahr später stellt sich heraus, "
        "dass die Kreditkartenzahlung des Marius nicht gedeckt war. Die GmbH geht insolvent. Grubmair hat nie "
        "Geld erhalten. Welche Ansprüche hat Grubmair? Welche Ansprüche hat der Tankstellenbetreiber?"
    ),
    "case08_wrongful_birth": (
        "Brigitte Buchner gebar am 21.11.2008 gesunde Drillinge nach IVF-Behandlung im Krankenhaus der "
        "Stadtgemeinde A. Sie hatte mit dem behandelnden Arzt Dr. Kindermann vereinbart, nur zwei Embryonen "
        "einzusetzen, um Mehrlingsschwangerschaft zu vermeiden. Tatsächlich wurden drei Embryonen eingesetzt. "
        "Haben Brigitte und ihr Ehemann Hubert Schadenersatzansprüche gegen den Arzt und/oder das Krankenhaus "
        "wegen der unerwünschten Drillingsgeburt? Wie ist die Rechtslage beim sogenannten Wrongful Birth?"
    ),
    "case09_doppelverkauf": (
        "Eigentümer E verkauft seine Liegenschaft an B. B wird NICHT ins Grundbuch eingetragen. Anschließend "
        "verkauft E dieselbe Liegenschaft an A. A wird ordnungsgemäß ins Grundbuch eingetragen und wird damit "
        "bücherlicher Eigentümer. B erfährt davon und klagt auf Löschung der Eintragung des A und eigene "
        "Eintragung. Wer ist Eigentümer? Hat B Ansprüche gegen A auf Herausgabe? Oder nur gegen E?"
    ),
    "case10_weg_oeltank": (
        "In einer Wohnungseigentumsanlage entdeckt ein Eigentümer (Top 16, Anteil 174/2742) einen aktiven "
        "Ölaustritt an der gemeinsamen Öltankanlage im Heizraum. Er ergreift Sofortmaßnahmen (Dokumentation, "
        "Öl auffangen), meldet den Schaden schriftlich an die Hausverwaltung mit Fotodokumentation und setzt "
        "eine Nachfrist. Die Hausverwaltung reagiert nicht substantiell. Die Öltankanlage ist allgemeiner Teil "
        "der Liegenschaft (§ 2 Abs 4 WEG). Welche Ansprüche hat der Eigentümer gegen die Hausverwaltung und "
        "die Eigentümergemeinschaft? Muss die HV sofort handeln (§ 20 Abs 2 WEG)?"
    ),
    "case11_anweisung": (
        "Peter Kolar hat in den Jahren 2015-2018 ca. EUR 80.000 für seine Schwiegermutter Hildegard Pfeffer "
        "aufgewendet (Zahnbehandlungen, Lebenshaltungskosten). 2021 einigen sie sich vergleichsweise auf "
        "EUR 40.000 Rückzahlung. Vereinbarung: Dr. Fohringer zahlt als Angewiesener (§ 1400 ABGB) jährlich "
        "EUR 5.000 an Kolar (8 Jahre). 2022-2024 fließen EUR 15.000. Anfang 2025 widerruft die Schwiegermutter "
        "per WhatsApp die Anweisung an Dr. Fohringer. Offener Rest: EUR 25.000. Zahlungsbefehl wurde erlassen. "
        "Wie sind die Erfolgsaussichten? Kann der Widerruf der Anweisung den Zahlungsanspruch beseitigen?"
    ),
    "case12_sicherungszession": (
        "Wurstfabrikant W verkauft zwei Tiefkühlaggregate (je EUR 10.000) an Händler Z. Vereinbarung: Z wird "
        "sofort Eigentümer, Geräte bleiben bis Weiterverkauf bei W. Z verkauft ein Aggregat an Fleischer F um "
        "EUR 24.000 auf 24 Monatsraten. Zur Sicherung tritt F seine laufenden Forderungen gegen Gastwirt G an "
        "Z ab (Sicherungszession). Bei der Abholung beschädigen Zs Mitarbeiter das Aggregat mit dem Gabelstapler "
        "grob fahrlässig (EUR 10.000 Schaden). F will den Reparaturschaden gegen den Kaufpreis aufrechnen. Z "
        "verlangt volle Ratenzahlung plus die abgetretenen Forderungen. Welche Ansprüche bestehen?"
    ),
    "case13_servitut_nachbar": (
        "A ist Eigentümer des Grundstücks X, das nur über das Nachbargrundstück Y des B erreichbar ist. Im "
        "Grundbuch ist zugunsten von X ein Geh- und Fahrwegerecht auf Y eingetragen. B stellt ein schweres Tor "
        "auf den Weg und wechselt das Schloss, sodass A sein Grundstück nicht mehr erreichen kann. Parallel "
        "verlegt Nachbar N ohne Zustimmung des A eine Wasserleitung über As Grundstück. A verlangt: (1) "
        "Entfernung des Tores durch B, (2) Entfernung der Wasserleitung durch N und Unterlassung. Welche "
        "Ansprüche hat A?"
    ),
}

print(f"=== 10-Case Benchmark | profile={PROFILE} | tag={TAG} | {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} ===")
results = {}
for i, (case_id, query) in enumerate(CASES.items(), 1):
    print(f"[{i}/10] {case_id}...", flush=True)
    log_path = OUT / f"{case_id}.log"
    t0 = time.time()
    try:
        proc = subprocess.run(
            ["python3", "scripts/legalchat_agentic_harness_minimal.py", "--query", query] + COMMON,
            capture_output=True, text=True, timeout=600,
            cwd="/root/harness",
            env={**os.environ, "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", "")},
        )
        elapsed = time.time() - t0
        log_path.write_text(proc.stdout)
        try:
            result = json.loads(proc.stdout.strip())
            ok = result.get("ok", False)
            ms = result.get("elapsed_ms", elapsed * 1000)
            out_dir = result.get("out_dir", "?")
            print(f"  ok={ok} elapsed={ms:.0f}ms dir={out_dir}")
            results[case_id] = {"ok": ok, "elapsed_ms": ms, "out_dir": out_dir}
        except json.JSONDecodeError:
            print(f"  PARSE ERROR after {elapsed:.0f}s")
            print(f"  stdout: {proc.stdout[:200]}")
            print(f"  stderr: {proc.stderr[:200]}")
            results[case_id] = {"ok": False, "elapsed_ms": elapsed * 1000, "error": "parse_error"}
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after 600s")
        results[case_id] = {"ok": False, "elapsed_ms": 600000, "error": "timeout"}
    except Exception as e:
        print(f"  ERROR: {e}")
        results[case_id] = {"ok": False, "elapsed_ms": (time.time() - t0) * 1000, "error": str(e)}

print(f"\n=== SUMMARY ===")
ok_count = sum(1 for r in results.values() if r.get("ok"))
total_ms = sum(r.get("elapsed_ms", 0) for r in results.values())
print(f"OK: {ok_count}/10 | Total: {total_ms/1000:.0f}s | Avg: {total_ms/10000:.0f}s/case")
for case_id, r in results.items():
    status = "OK" if r.get("ok") else f"FAIL({r.get('error', '?')})"
    print(f"  {case_id}: {status} {r.get('elapsed_ms', 0)/1000:.0f}s")

# Save summary
summary_path = OUT / "benchmark_summary.json"
summary_path.write_text(json.dumps({"profile": PROFILE, "tag": TAG, "results": results, "ok_count": ok_count, "total_ms": total_ms}, indent=2, ensure_ascii=False))
print(f"\nSummary saved: {summary_path}")
