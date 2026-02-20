# MCP Deployment Blueprint (Internal First)

## Zielbild

LegalChat nutzt MCPs intern ueber George (z. B. `deep research`, `pruefungsmodus`) ohne oeffentliche Exponierung.  
Spaeter kann optional ein autorisierter Zugriff fuer andere Apps (z. B. Codex) aktiviert werden.

## Betriebsmodi

### Modus A: Intern only (jetzt)

- MCP-Container laufen im privaten Docker-Netzwerk `legalchat_mcp_internal` (`internal: true`).
- Keine `ports:` fuer MCP-Services.
- Nur `login-proxy` ist mit dem MCP-Netz verbunden.
- Zugriffspfad: Browser -> LegalChat -> George -> interne MCP-Endpunkte.
- MCP-Server laufen als stdio-Prozesse hinter einer internen Bridge (`mcp_stdio_bridge.py`).
- Interne HTTP-Endpunkte:
  - `http://mcp-zivilrecht:8070`
  - `http://mcp-zivil-pruefung:8071`
- Interne DB fuer `zivilrecht`:
  - `mcp-super-ris-postgres:5432` (nur im `mcp_internal` Netz)
- Artefaktablage fuer Rohdaten:
  - `JSON` + `original HTML` unter `MCP_SUPER_RIS_ARTIFACTS_HOST_PATH`

### Modus B: Extern mit Autorisierung (spaeter)

- Zusaetzlicher MCP-Gateway-Service vor den MCPs.
- OIDC/JWT-Validierung gegen Logto.
- Scope-/Rollenpruefung pro Tool.
- Rate limiting, Audit logs, optional IP allowlist oder mTLS.
- Erst dann gezielte Freigabe fuer Third-Party-Clients.

## Compose-Blueprint

Datei: `docker/docker-compose.mcp.internal.yml`

Bridge-Implementierung: `docker/mcp-bridge/mcp_stdio_bridge.py`

Aktivierung:

```bash
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.mcp.internal.yml \
  --profile mcp-internal up -d
```

Deaktivierung:

```bash
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.mcp.internal.yml \
  --profile mcp-internal down
```

## Geplanter MCP: `zivil-pruefung` (vorgemerkt)

Status: in Build/Test.

Konzept:

- `zivilrecht-server` = Daten-Layer (Suche, Rechtssaetze, Entscheidungen)
- `zivil-pruefung` = Orchestrierungs-Layer (Exam Harness, Scoring, Fusion)

Geplante Tools:

- Tier 1: `list_topics`, `list_clusters`, `get_cluster_detail`, `detect_clusters`, `build_grounding_context`, `list_exams`, `load_exam`
- Tier 2: `run_exam`, `run_cct`, `get_validation_dashboard`

Wichtiger Implementierungspunkt:

- `fp_runner._p()` schreibt auf stdout und kollidiert mit MCP-stdio JSON-RPC.
- Fix: Monkey-Patch auf stderr (`fp_runner._p = _safe_p`).

Referenzpfad (lokal in eurer Entwicklungsumgebung):

- `.claude/skills/zivil-pruefung/mcp_server_zivil_pruefung.py`

## Empfohlene Env-Variablen

In `docker/.env`:

- `LEGALCHAT_MCP_INTERNAL_ENABLED=1`
- `LEGALCHAT_MCP_DEEP_RESEARCH_ENDPOINT=http://mcp-zivilrecht:8070`
- `LEGALCHAT_MCP_PRUEFUNGSMODUS_ENDPOINT=http://mcp-zivil-pruefung:8071`
- `MCP_ZIVILRECHT_CODE_PATH=/opt/legalchat/mcp/zivilrecht`
- `MCP_ZIVIL_PRUEFUNG_CODE_PATH=/opt/legalchat/mcp/zivil-pruefung`
- `MCP_RULESETS_PATH=/opt/legalchat/mcp/rulesets`
- `LEGALCHAT_MCP_BEARER_TOKEN=<service-token-standard>`
- `LEGALCHAT_MCP_ADMIN_BEARER_TOKEN=<service-token-admin>`
- `SUPER_RIS_POSTGRES_DB=super_ris`
- `SUPER_RIS_POSTGRES_USER=postgres`
- `SUPER_RIS_POSTGRES_PASSWORD=<starkes-passwort>`
- `MCP_ZIVILRECHT_DB_HOST=mcp-super-ris-postgres`
- `MCP_ZIVILRECHT_DB_PORT=5432`
- `MCP_ZIVILRECHT_DB_NAME=super_ris`
- `MCP_ZIVILRECHT_DB_USER=postgres`
- `MCP_ZIVILRECHT_DB_PASSWORD=<starkes-passwort>`
- `MCP_ZIVILRECHT_DB_SSLMODE=disable` (im internen Docker-Netz)
- `MCP_SUPER_RIS_ARTIFACTS_HOST_PATH=./mcp-super-ris-artifacts`
- `MCP_SUPER_RIS_IMPORT_JSON_ROOT=/srv/super-ris-artifacts`
- `MCP_SUPER_RIS_IMPORT_JSON_GLOB=*_TE.json`
- `MCP_SUPER_RIS_IMPORT_HTML_ROOTS=/srv/super-ris-artifacts`
- `MCP_SUPER_RIS_IMPORT_COMMIT_EVERY=1000`
- `MCP_SUPER_RIS_IMPORT_RS_JSON_ROOT=/srv/super-ris-artifacts`
- `MCP_SUPER_RIS_IMPORT_RS_JSON_GLOB=*_RS.json`
- `MCP_SUPER_RIS_IMPORT_RS_COMMIT_EVERY=1000`
- `MCP_STDOUT_SAFE_PATCH=1`
- `MCP_ZIVILRECHT_COMMAND=python3 /srv/mcp/mcp_server_zivilrecht.py`
- `MCP_ZIVIL_PRUEFUNG_COMMAND=python3 /srv/mcp/mcp_server_zivil_pruefung.py`
- `MCP_PROTOCOL_VERSION=2024-11-05`
- `MCP_BRIDGE_INIT_TIMEOUT_SEC=45`
- `MCP_BRIDGE_REQUEST_TIMEOUT_SEC=1200`
- `LEGALCHAT_MCP_ADMIN_EMAILS=<comma-separated>`
- `LEGALCHAT_MCP_ADMIN_ROLES=admin,owner,superadmin`
- `LEGALCHAT_MCP_PRIVILEGED_TOOLS_DEEP_RESEARCH=ask_gemini_zivilrecht`
- `LEGALCHAT_MCP_PRIVILEGED_TOOLS_PRUEFUNGSMODUS=run_exam,run_cct,get_validation_dashboard`

## Bridge API (intern)

Die Bridge kapselt MCP-JSON-RPC fuer interne HTTP-Aufrufe:

- `GET /health` -> Liveness
- `GET /tools` -> MCP `tools/list`
- `POST /tools/call` -> MCP `tools/call` mit Body:
  - `{ "name": "run_exam", "arguments": { ... } }`
- `POST /tool/<name>` -> Kurzform, Body = Arguments
- `POST /rpc` -> Low-level passthrough:
  - `{ "method": "tools/list", "params": {} }`

Beispiel:

```bash
curl -s http://mcp-zivil-pruefung:8071/tools | jq .
curl -s -X POST http://mcp-zivil-pruefung:8071/tools/call \
  -H 'content-type: application/json' \
  -d '{"name":"list_exams","arguments":{}}' | jq .
```

## LegalChat Gateway API (George Lane)

Der `login-proxy` bietet eine geschuetzte MCP-Lane unter:

- `GET /api/legalchat/mcp/status`
- `GET /api/legalchat/mcp/tools?mode=deep-research|pruefungsmodus`
- `POST /api/legalchat/mcp/call`
- `POST /api/legalchat/mcp/deep-research`
- `POST /api/legalchat/mcp/pruefungsmodus`
- `POST /api/legalchat/mcp/deep-research/<toolName>`
- `POST /api/legalchat/mcp/pruefungsmodus/<toolName>`

Request-Format (Tool-Call):

```json
{
  "mode": "deep-research",
  "name": "search_ogh_rechtssaetze",
  "arguments": {
    "query": "Verjaehrung Schadenersatz ABGB"
  }
}
```

AuthZ-Verhalten:

- Standard: eingeloggte LegalChat-Session (Auth.js-Cookie) ist ausreichend.
- Optional fuer Service-zu-Service:
  - `Authorization: Bearer <LEGALCHAT_MCP_BEARER_TOKEN>` (nicht privilegierte Tools)
  - `Authorization: Bearer <LEGALCHAT_MCP_ADMIN_BEARER_TOKEN>` (auch privilegierte Tools)
- Privilegierte Tools (z. B. `ask_gemini_zivilrecht`, `run_exam`) liefern `403`, wenn keine Admin-Rolle/-E-Mail oder kein Admin-Bearer vorliegt.
- Wenn `LEGALCHAT_MCP_INTERNAL_ENABLED=0`, antwortet die Lane mit `503`.

## Sicherheitsleitplanken

- MCPs bleiben ohne oeffentliche `ports`.
- MCP-Netzwerk bleibt `internal: true`.
- Nur explizit noetige Services an `mcp_internal` anbinden.
- Fuer externe Freigabe immer Gateway + AuthZ davor.

## Super-RIS Datenimport (Hetzner)

Der Container `mcp-super-ris-postgres` startet mit leerem Basisschema.  
Die echten OGH-Daten muessen danach importiert werden (Dump/Restore).

Schema fuer Rohdaten ist vorbereitet:
- `super_ris.te.source_json` (`jsonb`)
- `super_ris.te.original_html` (`text`)

### Option A: JSON + Original-HTML direkt importieren (empfohlen fuer MCP-Rohdaten)

One-shot Importer-Service:

```bash
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.mcp.internal.yml \
  --profile mcp-internal run --rm mcp-super-ris-importer \
  --json-root /srv/super-ris-artifacts \
  --html-root /srv/super-ris-artifacts \
  --glob '*_TE.json'
```

RS-Importer (Rechtssaetze) separat:

```bash
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.mcp.internal.yml \
  --profile mcp-internal --profile mcp-import run --rm mcp-super-ris-rs-importer \
  --json-root /srv/super-ris-artifacts \
  --glob '*_RS.json'
```

Dry-Run (ohne DB-Schreiben):

```bash
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.mcp.internal.yml \
  --profile mcp-internal run --rm mcp-super-ris-importer \
  --dry-run --limit 50 --verbose
```

Beispiel (auf dem Hetzner-Host):

```bash
# 1) Dump in den Container kopieren
docker cp /opt/legalchat/backups/super_ris.dump mcp-super-ris-postgres:/tmp/super_ris.dump

# 2) Restore laufen lassen
docker exec -it mcp-super-ris-postgres \
  pg_restore -U ${SUPER_RIS_POSTGRES_USER:-postgres} \
  -d ${SUPER_RIS_POSTGRES_DB:-super_ris} \
  --clean --if-exists --no-owner --no-privileges /tmp/super_ris.dump
```

Smoke-Test:

```bash
curl -s -X POST https://legalchat.net/api/legalchat/mcp/deep-research/search_by_paragraph \
  -H "Authorization: Bearer <LEGALCHAT_MCP_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"paragraph":"§ 934 ABGB","limit":3}'
```

Optionaler Check auf Rohdaten:

```bash
docker exec -it mcp-super-ris-postgres psql -U ${SUPER_RIS_POSTGRES_USER:-postgres} -d ${SUPER_RIS_POSTGRES_DB:-super_ris} \
  -c "select stable_key, (source_json is not null) as has_json, (original_html is not null) as has_html from super_ris.te limit 10;"
```

### FTS-Index-Migration fuer bestehende Volumes

Bei bereits laufenden Datenbanken kann ein alter RS-FTS-Index aktiv sein.  
Die produktive Query nutzt `COALESCE(rechtssatz_volltext, kurzinformation, '')`.

Migration anwenden:

```bash
docker exec -i mcp-super-ris-postgres psql -U ${SUPER_RIS_POSTGRES_USER:-postgres} -d ${SUPER_RIS_POSTGRES_DB:-super_ris} \
  < /opt/legalchat/docker/mcp-super-ris-init/003_rebuild_fts_indexes.sql
```

Verifikation:

```bash
docker exec -it mcp-super-ris-postgres psql -U ${SUPER_RIS_POSTGRES_USER:-postgres} -d ${SUPER_RIS_POSTGRES_DB:-super_ris} \
  -c "EXPLAIN ANALYZE SELECT rs_number FROM super_ris.rs WHERE to_tsvector('german', COALESCE(rechtssatz_volltext, kurzinformation, '')) @@ plainto_tsquery('german','laesio') LIMIT 5;"
```
