# Offene Probleme & Lösungsansätze

> Stand: 10. Februar 2026

## 🔴 Kritisch: Authentifizierungs-Fehler

### Problem
Der Login-Button in der LobeChat UI funktioniert nicht. Beim Klicken auf "Sign in with Logto" wird eine Fehlerseite angezeigt:

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

**Next-Auth v5.0.0-beta.30** erwartet für Provider-Logins einen **POST-Request** an `/api/auth/signin/logto`, aber die LobeChat-UI (oder der Browser-Redirect) macht einen **GET-Request**.

**Auth.js Fehler im Log:**
```
[auth][error] UnknownAction: Unsupported action. Read more at https://errors.authjs.dev#unknownaction
    at Object.signin (/app/.next/server/chunks/15359.js:3215:23)
```

### Warum passiert das?

1. Next-Auth v5 hat die API geändert - `signin()` erwartet POST
2. LobeChat wurde für eine ältere Version entwickelt
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

**Ergebnis:** LobeChat erkennt die Variablen (zeigt Deprecation-Warnungen), aber der Fehler bleibt

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

## 🎯 Aktueller Workaround

### Für Endbenutzer

1. **Nicht** den Login-Button in LobeChat verwenden
2. Stattdessen zu http://localhost:3211 gehen
3. Auf "Direkt zu Logto Login" klicken
4. Nach erfolgreichem Login automatisch zurück zu LobeChat

### Für Entwickler

Nach dem Login funktioniert LobeChat vollständig:
- ✅ Chat-Funktionalität
- ✅ OpenRouter AI Integration
- ✅ File Uploads (MinIO)
- ✅ Session Management

---

## 🔧 Mögliche Langfristige Lösungen

### Option 1: LobeChat Update

**Aufwand:** Hoch
**Risiko:** Mittel

Warten auf oder implementieren eines LobeChat-Updates, das Next-Auth v5 vollständig unterstützt.

**Siehe:**
- https://github.com/lobehub/lobe-chat/issues/7339
- https://github.com/lobehub/lobe-chat/discussions/7343

### Option 2: Next-Auth v4 Downgrade

**Aufwand:** Mittel
**Risiko:** Hoch

LobeChat auf eine Version mit Next-Auth v4 downgraden.

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
