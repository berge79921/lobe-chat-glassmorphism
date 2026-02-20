# Offene Probleme & Lösungsansätze

> Stand: 10. Februar 2026

## ✅ Status-Update (10. Februar 2026)

Ein **Auth-Gateway-Fix** wurde implementiert:

- `GET /api/auth/signin/logto` wird am Gateway abgefangen
- Gateway holt serverseitig CSRF-Token + Cookie
- Gateway fuehrt den erforderlichen POST-Request aus
- Browser erhaelt den korrekten 302 Redirect zu Logto

Damit funktioniert der normale Login-Klick in der LegalChat UI auf `http://localhost:3210` wieder ohne `Configuration` Fehler.

---

## ✅ Status-Update (10. Februar 2026) - Bildverarbeitung

Fuer den OpenRouter/MinIO-Bildpfad wurde eine strukturelle Loesung als Default eingefuehrt:

- `S3_SET_ACL=0` (private Objekte + presigned Preview)
- `LLM_VISION_IMAGE_USE_BASE64=1` (kein externer Fetch auf private URLs)
- `SSRF_ALLOW_PRIVATE_IP_ADDRESS=0` und gezielte `SSRF_ALLOW_IP_ADDRESS_LIST`
- `S3_PUBLIC_DOMAIN` ohne `localhost`

Details und Verlauf: `ISSUES.md` (Issue #1).

---

## ✅ Status-Update (10. Februar 2026) - Branding/CI Konsistenz

Ursache fuer inkonsistentes Branding (teilweise weiter `LegalChat`/alte Icons sichtbar) war ein aktiver PWA-Service-Worker (`/sw.js`), der alte Assets im Browser-Cache hielt.

Strukturelle Loesung im Gateway:

- `login-proxy` liefert fuer `/sw.js` jetzt bewusst ein No-Op-Service-Worker-Skript aus, das sich selbst `unregister()`t
- zusaetzlich werden bekannte PWA/Serwist-Cache-Namen im Browser einmalig aktiv geloescht
- no-store/no-cache Header fuer:
  - HTML Einstiegsseiten (`/`, `/chat*`, `/welcome*`)
  - Branding Assets (`/custom.css`, `/legalchat-branding.js`)
- Branding Asset Version angehoben auf `LEGALCHAT_BRANDING_VERSION=2026-02-10-04`

Verifikation:

- `GET /sw.js` liefert no-cache Header + No-Op Worker
- UI-Wordmark ist konsistent `LegalChat`
- George-Avatar + Icon-Tuning greifen in Sidebar/Session stabil
- Browser-E2E (Playwright) zeigt keine sichtbaren `LegalChat/LegalChat` Texte mehr im gerenderten Body

Hinweis:
- `LegalChat` kann weiterhin in Next.js Inline-Skripten/Meta-Payloads auftauchen (technische SSR-Daten), ist aber nicht mehr als sichtbarer UI-Brandname vorhanden.

---

## 🔴 Kritisch: Authentifizierungs-Fehler

### Problem
Der Login-Button in der LegalChat UI funktioniert nicht. Beim Klicken auf "Sign in with Logto" wird eine Fehlerseite angezeigt:

```
http://localhost:3210/next-auth/error?error=Configuration
```

oder nach einem Redirect-Versuch:

```
http://localhost:3210/next-auth/signin?error=MissingCSRF
```

---

## 🔍 Root Cause Analysis

### Technische Ursache

**Next-Auth v5.0.0-beta.30** erwartet für Provider-Logins einen **POST-Request** an `/api/auth/signin/logto`, aber die LegalChat-UI (oder der Browser-Redirect) macht einen **GET-Request**.

**Auth.js Fehler im Log:**
```
[auth][error] UnknownAction: Unsupported action. Read more at https://errors.authjs.dev#unknownaction
    at Object.signin (/app/.next/server/chunks/15359.js:3215:23)
```

### Warum passiert das?

1. Next-Auth v5 hat die API geändert - `signin()` erwartet POST
2. LegalChat wurde für eine ältere Version entwickelt
3. Der Fehler tritt nur bei der "Sign in with [Provider]" UI-Komponente auf

---

## ✅ Erfolgreich getestete Lösungen

### Workaround: Login Proxy (IMPLEMENTIERT)

**Status:** ✅ Funktioniert

Ein Node.js Proxy-Service auf Port 3211, der:
1. Eine Login-Seite mit Glassmorphism-Design anbietet
2. Direkte Weiterleitung zu Logto ermöglicht
3. Den OAuth-Flow korrekt handhabt

**Zugriff:** http://localhost:3211

**Implementierung:**
- Datei: `docker/login-fix/server.js`
- Service: `login-proxy` in `docker-compose.yml`

### Direkter Logto-Zugriff (MANUELL)

**Status:** ✅ Funktioniert

Manueller Login direkt über Logto:

```
http://192.168.1.240:3001/oidc/auth?
  client_id=berge79921&
  redirect_uri=http%3A%2F%2Flocalhost%3A3210%2Fapi%2Fauth%2Fcallback%2Flogto&
  response_type=code&
  scope=openid+profile+email&
  state=xyz
```

---

## ❌ Nicht funktionierende Ansätze (Dokumentation)

### 1. Umgebungsvariablen-Anpassung

**Versucht:**
- `AUTH_LOGTO_ISSUER` auf verschiedene URLs setzen
  - `http://localhost:3001/oidc` ❌
  - `http://192.168.1.240:3001/oidc` ❌
  - `http://lobe-logto:3001/oidc` ❌

**Ergebnis:** Kein Einfluss auf den GET/POST-Fehler

### 2. Alternative Env-Vars

**Versucht:**
- `LOGTO_CLIENT_ID` statt `AUTH_LOGTO_ID`
- `LOGTO_CLIENT_SECRET` statt `AUTH_LOGTO_SECRET`
- `LOGTO_ISSUER` statt `AUTH_LOGTO_ISSUER`

**Ergebnis:** LegalChat erkennt die Variablen (zeigt Deprecation-Warnungen), aber der Fehler bleibt

### 3. AUTH_URL / AUTH_SECRET

**Versucht:**
```yaml
AUTH_URL: http://localhost:3210/api/auth
AUTH_SECRET: <same_as_NEXT_AUTH_SECRET>
```

**Ergebnis:** Führte zu zusätzlichen Fehlern, keine Besserung

### 4. AUTH_TRUST_HOST

**Versucht:**
```yaml
AUTH_TRUST_HOST: "true"
```

**Ergebnis:** Keine Änderung des Verhaltens

### 5. Cookie-Konfiguration

**Versucht:**
- Domain-Einstellungen anpassen
- SameSite-Cookies testen
- Secure-Flag (für HTTPS)

**Ergebnis:** Problem ist nicht cookie-bezogen

### 6. GET-zu-POST Proxy (automatisch)

**Versucht:**
Ein Proxy der GET-Requests automatisch in POST-Requests umwandelt:

```javascript
// GET /api/auth/signin/logto → POST /api/auth/signin/logto
```

**Ergebnis:** 
- CSRF-Token wird korrekt geholt
- POST-Request wird gemacht
- Aber: `MissingCSRF` Fehler bleibt bestehen
- Ursache: CSRF-Cookies werden nicht korrekt zwischen Requests weitergegeben

### 7. Logto Client Konfiguration

**Versucht:**
- Redirect URIs in Logto anpassen
- CORS Origins konfigurieren
- Verschiedene Application Types (SPA, Traditional, etc.)

**Ergebnis:** Logto funktioniert korrekt (direkte Aufrufe funktionieren)

---

## 🎯 Aktueller Betriebsstatus

### Für Endbenutzer

1. LegalChat normal unter http://localhost:3210 oeffnen
2. Login-Button in der UI wie gewohnt verwenden
3. Der Gateway fuehrt den noetigen CSRF+POST Login-Flow automatisch aus
4. Optional steht weiterhin die Helper-Seite unter http://localhost:3211/login zur Verfuegung

### Für Entwickler

Nach dem Login funktioniert LegalChat vollständig:
- ✅ Chat-Funktionalität
- ✅ OpenRouter AI Integration
- ✅ File Uploads (MinIO)
- ✅ Session Management

---

## 🧭 MCP Taskliste (Zwischenreview 20. Februar 2026)

Quelle: technischer Zwischenreview (Code + Live-Checks gegen Hetzner).  
Status: Abschluss-Update mit Verifikation vom 20. Februar 2026.

### P1 - Produktionskritisch

- [x] `MCP-P1-01` Runtime-Abhaengigkeiten fuer `ask_gemini_zivilrecht` im MCP-Image sicherstellen  
  Umsetzung: Runtime-Image aktualisiert (`docker/mcp-bridge/Dockerfile.mcp-runtime.local`) mit `curl`, `google-auth`, `requests`, `aiohttp`.  
  Verifikation:
    - Container-Check: Imports fuer `google.auth`, `google.auth.transport.requests`, `requests`, `aiohttp` erfolgreich.
    - E2E `/api/legalchat/mcp/deep-research`:
      - Standard-Token auf privilegiertem Tool: 403 (Policy greift),
      - Admin-Token auf privilegiertem Tool: 200 (kein `ENOENT`/`No such file or directory`).

- [x] `MCP-P1-02` Fresh-Deploy DB-Schema zu produktiven Queries kompatibel machen  
  Umsetzung: `001_schema.sql` + `002_compat_columns.sql` aktiv, zusaetzlich FTS-Migration `003_rebuild_fts_indexes.sql`.  
  Verifikation:
    - Frische Test-DB aus Init-Skripten gestartet.
    - Representative Imports erfolgreich (`RS=5`, `TE=3`).
    - Produktive Query-Pfade laufen auf frischer DB ohne `column does not exist`.

- [x] `MCP-P1-03` Datenversorgung fuer RS/TE auf Hetzner sicherstellen  
  Umsetzung: RS- und TE-Importpfade aktiv genutzt, Runbook in `docs/MCP_DEPLOYMENT.md` ergaenzt.  
  Verifikation:
    - Datenstand lokal nach Import: `super_ris.rs=5000`, `super_ris.te=2749`.
    - Smoke-Calls mit echten Ergebnissen:
      - `search_ogh_rechtssaetze`: 200,
      - `search_by_paragraph`: 200,
      - `search_ogh_entscheidungen`: 200.

- [x] `MCP-P1-04` Deploy-Drift Hetzner beheben: `login-proxy` ohne MCP-Lane  
  Umsetzung: Hetzner-Proxy auf aktuellen MCP-Routenstand synchronisiert.  
  Verifikation:
    - `GET https://legalchat.net/api/legalchat/mcp/status` ohne Auth: 401,
    - mit Bearer: 200 (beide Modi healthy),
    - kein 404 mehr auf der MCP-Lane.

### P2 - Stabilitaet / Performance

- [x] `MCP-P2-01` Harte Request-Timeouts in `mcp_stdio_bridge.py` bei blockierendem `readline()`  
  Umsetzung: Timeout-Verhalten gegen haengenden Fake-MCP verifiziert.  
  Verifikation:
    - Mit `MCP_BRIDGE_REQUEST_TIMEOUT_SEC=2` liefert `/tools` nach ~2.01s einen Timeout-Fehler.
    - Keine dauerhaft blockierten Request-Worker beobachtet.

- [x] `MCP-P2-02` FTS-Index auf den tatsaechlichen Suchausdruck ausrichten  
  Umsetzung: `003_rebuild_fts_indexes.sql` hinzugefuegt und ausgefuehrt.  
  Verifikation:
    - `EXPLAIN ANALYZE` zeigt `Bitmap Index Scan` fuer die Standard-FTS-Query.
    - Suchabfragen laufen stabil und schnell.

- [x] `MCP-P2-03` Importer-Fehlerpfad transaktionssicher machen  
  Umsetzung: Savepoint-basiertes Row-Handling im TE-Importer aktiv.  
  Verifikation:
    - Fehlerfall-Test mit absichtlich fehlerhafter Row: nur die defekte Row faellt aus.
    - Folge-Rows werden weiter sauber upserted, keine Kaskadenfehler.

### P3 - Security-Hardening

- [x] `MCP-P3-01` Unsichere Default-Passwoerter als Fallback entfernen  
  Umsetzung:
    - `docker/docker-compose.mcp.internal.yml` auf required-env (`:?`) umgestellt,
    - `docker/.env.example` auf `CHANGE_ME_STRONG_SECRET` umgestellt.
  Verifikation:
    - Compose bricht ohne gesetzte Secrets mit klarer Fehlermeldung ab (fail fast).

- [x] `MCP-P3-02` Feingranulare AuthZ fuer MCP-Tools aktivieren  
  Umsetzung: Tool-Policy pro Modus + privilegierte Toolliste in `docker/login-fix/server.js`, inklusive Admin-Bearer.  
  Verifikation:
    - Privilegiertes Tool (`ask_gemini_zivilrecht`) mit Standard-Token: 403.
    - Dasselbe Tool mit Admin-Token: 200.
    - Nicht privilegierte Tools bleiben mit Standard-Token nutzbar (200).
    - Deny-Events werden im Proxy geloggt.

### Test-Luecken (als Aufgaben)

- [x] `MCP-TST-01` Regressionstest fuer Fake-Cookie/Auth-Bypass in `login-proxy`
- [x] `MCP-TST-02` E2E-Test fuer `ask_gemini_zivilrecht` im Container-Setup
- [x] `MCP-TST-03` Fresh-DB-Migrations-/Schema-Kompatibilitaetstest gegen produktive MCP-Queries
- [x] `MCP-TST-04` Deploy-Sync-Test: `/api/legalchat/mcp/status` darf auf Hetzner nie `404` sein

---

## 🧭 Roadmap: MCP intern ueber George

Geplant und vorgemerkt:

- Interner MCP-Lane fuer `deep research` und `pruefungsmodus`
- Kein oeffentlicher MCP-Port in der aktuellen Phase
- Zukuenftige externe Freigabe nur ueber autorisierten Gateway (OIDC/JWT)
- Kandidat in Build/Test: `zivil-pruefung` MCP (Exam Harness + Scoring Layer)

Details: [MCP_DEPLOYMENT.md](MCP_DEPLOYMENT.md)

---

## 🔧 Mögliche Langfristige Lösungen

### Option 1: LegalChat Update

**Aufwand:** Hoch
**Risiko:** Mittel

Warten auf oder implementieren eines LegalChat-Updates, das Next-Auth v5 vollständig unterstützt.

**Siehe:**
- https://github.com/lobehub/lobe-chat/issues/7339
- https://github.com/lobehub/lobe-chat/discussions/7343

### Option 2: Next-Auth v4 Downgrade

**Aufwand:** Mittel
**Risiko:** Hoch

LegalChat auf eine Version mit Next-Auth v4 downgraden.

**Problem:** Breaking Changes in der Datenbank-Schema

### Option 3: Custom Auth Handler

**Aufwand:** Hoch
**Risiko:** Mittel

Eigenen Auth-Handler implementieren, der GET-Requests korrekt verarbeitet.

**Ansatz:**
- Next.js Route Handler überschreiben
- Auth.js Provider direkt konfigurieren
- Session-Management selbst implementieren

### Option 4: Externer Auth-Provider

**Aufwand:** Mittel
**Risiko:** Niedrig

Statt Logto einen anderen Provider verwenden, der besser unterstützt wird.

**Alternativen:**
- Auth0
- Keycloak
- Authelia
- Clerk

---

## 📊 Test-Status

| Ansatz | Status | Details |
|--------|--------|---------|
| Auth-Gateway auf Port 3210 | ✅ | GET-Signin wird transparent in CSRF+POST umgesetzt |
| Env-Variablen | ❌ | Kein Effekt |
| AUTH_TRUST_HOST | ❌ | Kein Effekt |
| AUTH_URL | ❌ | Mehr Fehler |
| GET→POST Proxy | ⚠️ | Teilweise, CSRF-Problem |
| Login-Hilfe (3211) | ✅ | Funktioniert |
| Direkter Logto | ✅ | Funktioniert |
| Logto-Client-Config | ✅ | Korrekt konfiguriert |

---

## 🔗 Referenzen

### GitHub Issues
- https://github.com/lobehub/lobe-chat/issues/7339
- https://github.com/lobehub/lobe-chat/discussions/7343
- https://github.com/lobehub/lobe-chat/issues/4074

### Next-Auth Dokumentation
- https://authjs.dev/reference/core/errors
- https://next-auth.js.org/v5

### Logto Dokumentation
- https://docs.logto.io/docs/recipes/integrate-application/next-app-router/
- https://openid.net/specs/openid-connect-core-1_0.html

---

## 📝 Änderungshistorie

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-10 | Kimi | Initiale Dokumentation |
