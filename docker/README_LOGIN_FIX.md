# LobeChat Logto Login - Workaround

## Problem

Next-Auth v5 (Beta) in LobeChat erfordert POST-Requests für `/api/auth/signin/logto`, aber die LobeChat-UI macht GET-Requests. Dies führt zu einem "MissingCSRF" oder "Configuration" Fehler.

## Lösung

Ein Proxy-Service läuft auf Port 3211, der:
1. Eine benutzerfreundliche Login-Seite anzeigt
2. Die Logto-OAuth-Flow-URLs korrekt handhabt
3. Callbacks an LobeChat weiterleitet

## Verwendung

### Option 1: Direkter Login über Logto (Empfohlen)

1. Öffne die Login-Hilfe-Seite:
   ```
   http://localhost:3211/login
   ```

2. Klicke auf "Direkt zu Logto Login"

3. Nach erfolgreicher Anmeldung bei Logto wirst du automatisch zu LobeChat weitergeleitet

### Option 2: Manuelle URL

Du kannst auch direkt zur Logto-Anmeldeseite gehen:

```
http://192.168.1.240:3001/oidc/auth?client_id=berge79921&redirect_uri=http%3A%2F%2Flocalhost%3A3210%2Fapi%2Fauth%2Fcallback%2Flogto&response_type=code&scope=openid+profile+email&state=xyz
```

## Konfiguration

Alle Dienste laufen korrekt:
- **LobeChat**: http://localhost:3210
- **Login-Hilfe**: http://localhost:3211  
- **Logto Auth**: http://192.168.1.240:3001
- **Logto Admin**: http://localhost:3002

## Technische Details

Die Konfiguration in `docker-compose.yml` wurde angepasst:
- `LOGTO_ENDPOINT` und `AUTH_LOGTO_ISSUER` verwenden die Host-IP (192.168.1.240)
- Die Logto-Anwendung `berge79921` wurde in der Datenbank erstellt
- Der Proxy-Service `login-proxy` läuft auf Port 3211

## Bekannte Einschränkungen

1. Der Login-Button in der LobeChat-UI funktioniert nicht direkt (Next-Auth v5 Beta-Limitation)
2. Benutzer müssen über http://localhost:3211/login oder direkt zu Logto gehen
3. Nach dem Login funktioniert LobeChat normal
