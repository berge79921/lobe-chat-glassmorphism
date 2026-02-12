# LegalChat Logto Login - Gateway Fix

## Problem

Next-Auth v5 (Beta) in LegalChat erfordert POST-Requests fuer `/api/auth/signin/logto`, aber die LegalChat-UI macht GET-Requests. Das fuehrt zu `Configuration` und `MissingCSRF` Fehlern.

## Lösung

Ein Auth-Gateway sitzt jetzt vor LegalChat (Port `3210`) und uebersetzt den fehlerhaften GET-Flow serverseitig in einen gueltigen CSRF-geschuetzten POST-Flow:

1. GET auf `/api/auth/signin/logto` kommt beim Gateway an
2. Gateway holt CSRF-Token + Cookie von `/api/auth/csrf`
3. Gateway sendet serverseitig POST an `/api/auth/signin/logto`
4. Browser erhaelt den korrekten 302 Redirect zu Logto inklusive Session-Cookies

## Verwendung

### Standard (UI-Login funktioniert wieder)

1. Oeffne LegalChat:
   - `http://localhost:3210`
2. Klicke normal auf `Sign in with Logto`
3. Redirect zu Logto erfolgt ohne `Configuration` Fehler

### Optionale Login-Hilfe

Zusatzseite (gleicher Gateway-Service):
- `http://localhost:3211/login`

## Konfiguration

Alle Dienste laufen korrekt:
- **LegalChat (via Gateway)**: `http://localhost:3210`
- **Login-Hilfe**: `http://localhost:3211/login`
- **Logto Auth**: `http://localhost:3001`
- **Logto Admin**: `http://localhost:3002`

## Technische Details

`docker-compose.yml`:
- `lobe` ist nur intern erreichbar (`expose: 3210`)
- `login-proxy` published `3210:3210` (Hauptzugang) und `3211:3210` (Helper)

`docker/login-fix/server.js`:
- Reverse-Proxy fuer alle normalen Requests
- Spezieller Handler fuer GET `/api/auth/signin/:provider` und `/next-auth/signin/:provider`
- Korrekte Cookie-Deduplizierung fuer mehrfach gesetzte `authjs.csrf-token` Cookies

## Bekannte Einschränkungen

1. Der Fix adressiert den Sign-in GET/POST-Mismatch; Upstream-Inkompatibilitaeten in anderen Endpunkten sind weiterhin moeglich.
2. Bei aendernder Upstream-Auth-API muss der Gateway-Handler angepasst werden.
