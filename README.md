# LegalChat ⚖️

Ein KI-gestützter Rechtsassistent mit benutzerdefiniertem Glassmorphism-Theme.

> **Powered by LegalChat** • **KI-Jurist: George** • **Secure Auth with Logto**

![Theme Preview](https://img.shields.io/badge/Theme-Glassmorphism-blue)
![Auth](https://img.shields.io/badge/Auth-Logto-green)
![AI](https://img.shields.io/badge/AI-OpenRouter-orange)

## 🚀 Schnellstart

```bash
# Repository klonen
git clone https://github.com/berge79921/lobe-chat-glassmorphism.git
cd lobe-chat-glassmorphism

# Environment konfigurieren
cp .env.example .env
cp docker/.env.example docker/.env
# → .env Dateien mit eigenen Werten füllen

# Starten
./start.sh
```

## 🎨 Features

### Glassmorphism Theme
- **Dark Mode**: Slate-950 Hintergrund
- **Glass Cards**: `rounded-[2.5rem]`, `backdrop-blur-3xl`
- **Gradient Blobs**: Dekorative Blur-Effekte
- **Blue/Indigo Accents**: Primärfarben #3b82f6 / #6366f1

### Authentifizierung
- **Provider**: Logto (OIDC)
- **Fix**: Auth-Gateway behebt Next-Auth v5 GET/POST-Mismatch transparent
- **Zugriff**: http://localhost:3210 (Standard), http://localhost:3211/login (optional)

### KI-Assistent: George 🎩
- **Name**: George - Ihr intelligenter KI-Jurist
- **Avatar**: Professionelles LegalChat-Avatar Design
- **Expertise**: Rechtsfragen, Vertragsanalyse, Recherche

### AI Provider
- **Primär**: OpenRouter (GPT-4, Claude, Gemini, etc.)
- **Fallback**: OpenAI, Anthropic, Google (optional)

### Infrastruktur
- **Datenbank**: PostgreSQL mit pgvector
- **Storage**: MinIO S3-kompatibel
- **Container**: Docker Compose
- **Vision-Pipeline**: Presigned S3 + Base64-Transfer fuer externe AI-Provider

## 📋 Architektur

Detaillierte Architekturdokumentation:

→ **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** (in Arbeit)

Übersicht der Komponenten:
```
┌───────────────────────┐     ┌───────────────────────┐     ┌─────────────────┐
│ Browser / LegalChat UI│────▶│ Auth Gateway          │────▶│ LegalChat App    │
│ Ports: 3210, 3211     │     │ Port: 3210 (+3211)    │     │ Internal: 3210  │
└───────────────────────┘     └───────────────────────┘     └─────────────────┘
                                         │
                                         ├──────────────▶ Logto (OIDC, 3001/3002)
                                         ├──────────────▶ PostgreSQL (5432)
                                         └──────────────▶ MinIO (9000/9001)
```

## 🔧 Konfiguration

### Wichtige Umgebungsvariablen

| Variable | Beschreibung | Beispiel |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API Key | `sk-or-v1-...` |
| `NEXT_AUTH_SECRET` | Auth.js Session Secret | `openssl rand -base64 32` |
| `AUTH_LOGTO_ID` | Logto Client ID | `berge79921` |
| `AUTH_LOGTO_SECRET` | Logto Client Secret | `X6duaf3@L` |
| `LOGTO_ENDPOINT` | Logto URL (Host IP!) | `http://192.168.1.240:3001` |
| `LEGALCHAT_LOGOUT_MODE` | Logout-Verhalten (`local` oder `oidc`) | `local` |

### Logout ohne sichtbare Logto-Seite

Standard in diesem Setup:

```env
LEGALCHAT_LOGOUT_MODE=local
LEGALCHAT_LOCAL_LOGOUT_REDIRECT_URL=/login?logged_out=1
LEGALCHAT_FORCE_LOGIN_PROMPT=1
```

Wenn vollständiger OIDC-Logout gegen Logto gewünscht ist:

```env
LEGALCHAT_LOGOUT_MODE=oidc
LOGTO_END_SESSION_ENDPOINT=https://auth.legalchat.net/oidc/session/end
LOGTO_POST_LOGOUT_REDIRECT_URL=https://legalchat.net
```

Hinweis: Bei `oidc` muss `https://legalchat.net` in Logto als **Post sign-out redirect URI** hinterlegt sein.

### Gehostete Logto-Anmeldeseite im LegalChat-Stil

Die Seite `https://auth.legalchat.net/sign-in` wird über den `login-proxy` geleitet und serverseitig
mit LegalChat-Branding versehen (Farben, Hintergrund, Logo, Button-Stil).

Relevante Variablen:

```env
LEGALCHAT_LOGTO_BRANDING=1
LEGALCHAT_LOGTO_BRANDING_HOSTS=auth.legalchat.net
LEGALCHAT_PUBLIC_ASSET_BASE=https://legalchat.net
LEGALCHAT_LOGTO_LOGO_URL=https://legalchat.net/custom-assets/legalchat-avatar.jpg
LOGTO_UPSTREAM_HOST=logto
LOGTO_UPSTREAM_PORT=3001
```

### Welcome-Text und Standard-Agent anpassen

Der Begruessungstext im Chat-Header ist aktuell **nicht** in den normalen UI-Settings konfigurierbar.
In diesem Repo wird er jetzt zentral ueber `.env` + `login-proxy` gesteuert:

```env
LEGALCHAT_APP_NAME=LegalChat
LEGALCHAT_DEFAULT_AGENT_NAME=George
LEGALCHAT_FAVICON_URL=/custom-assets/legalchat-avatar.jpg
LEGALCHAT_ASSISTANT_ROLE_DE=persönlicher KI-Jurist
LEGALCHAT_TAB_TITLE=George · LegalChat
LEGALCHAT_VOICE_MODE=off
LEGALCHAT_STT_MAX_RECORDING_MS=90000
LEGALCHAT_STT_SILENCE_STOP_MS=3000
LEGALCHAT_WELCOME_PRIMARY_DE=Ich bin George, Ihr persönlicher KI-Jurist bei LegalChat. Wie kann ich Ihnen jetzt helfen?
LEGALCHAT_WELCOME_SECONDARY_DE=Wenn Sie einen professionelleren oder maßgeschneiderten Assistenten benötigen, klicken Sie auf +, um einen benutzerdefinierten Assistenten zu erstellen.
```

Danach neu starten:

```bash
docker compose -f docker/docker-compose.yml up -d --force-recreate login-proxy
```

### Voice-Off Modus (produktionstauglich)

Wenn Teams keine Sprachaufnahme erlauben sollen, kann Voice via Proxy zentral deaktiviert werden:

```env
LEGALCHAT_VOICE_MODE=off
```

Fuer aktivierte Sprache wieder auf `guarded` stellen.

Wirkung:
- Mikrofon-/Voice-Controls werden im UI ausgeblendet
- `getUserMedia({ audio: ... })` wird hart blockiert (`NotAllowedError`)
- laufende STT-Sessions werden gestoppt

Aktivierung:

```bash
docker compose -f docker/docker-compose.yml up -d --force-recreate login-proxy
```

### Produktionsprofil: Bildverarbeitung mit OpenRouter

Fuer stabile Bildverarbeitung in Produktion (ohne `localhost`-Probleme) nutzt dieses Repo jetzt standardmaessig folgende Architektur:

1. Bilder bleiben in MinIO (private Objekte, kein `public-read`)
2. LegalChat erzeugt presigned Preview-URLs
3. LegalChat konvertiert die Bilddaten serverseitig in Base64
4. OpenRouter erhaelt nur Base64-Daten, keine private URL

Pflicht-Variablen in `docker/.env`:

| Variable | Sollwert |
|----------|----------|
| `S3_SET_ACL` | `0` |
| `LLM_VISION_IMAGE_USE_BASE64` | `1` |
| `SSRF_ALLOW_PRIVATE_IP_ADDRESS` | `0` |
| `SSRF_ALLOW_IP_ADDRESS_LIST` | Host-IP von MinIO, z.B. `192.168.1.240` |
| `S3_PUBLIC_DOMAIN` | Keine localhost-URL |

Zusaetzlich fuer zuverlässigen JPEG/PNG-Upload inkl. OCR:

| Variable | Sollwert |
|----------|----------|
| `OPENROUTER_MODEL_LIST` | Enthält mindestens ein `vision`-faehiges Modell, z.B. `google/gemini-2.5-flash-lite...<...:vision:...>` |
| `DEFAULT_AGENT_CONFIG` | `provider=openrouter;model=google/gemini-2.5-flash-lite` |

Hinweis: LegalChat blockiert Bild-Upload clientseitig, wenn das aktive Modell keine `vision`-Capability hat.

### Automatisches JPEG-OCR (modellunabhaengig)

LegalChat kann JPEGs serverseitig immer zuerst ueber Gemini 2.5 Flash Lite OCR laufen lassen und
anschliessend den eigentlichen Chat weiterhin mit dem im UI gewaehlten Modell ausfuehren.

Technik:
- `file.createFile`-Requests werden im Proxy mitgeschnitten, damit pro `fileId` die echte Storage-URL gecacht wird.
- Falls der Cache leer ist, holt der Proxy `file.getFileItemById` (authentifiziert ueber User-Cookies) als Fallback.
- OCR-Download versucht zuerst `/f/:id` (falls im Build vorhanden), danach S3/MinIO per signierter GET-URL.
- Damit funktioniert OCR auch auf Builds ohne exponierte `/f/:id`-Route.

Pflicht-Variablen im `login-proxy` (bereits im Compose verdrahtet):

| Variable | Sollwert |
|----------|----------|
| `LEGALCHAT_OCR_ENABLED` | `1` |
| `LEGALCHAT_OCR_MODEL` | `google/gemini-2.5-flash-lite` |
| `OPENROUTER_API_KEY` | gesetzt |

Optionales Tuning:
- `LEGALCHAT_OCR_MAX_IMAGES` (Default `6`)
- `LEGALCHAT_OCR_MAX_IMAGE_BYTES` (Default `12582912`)
- `LEGALCHAT_OCR_MAX_TEXT_CHARS` (Default `12000`)
- `LEGALCHAT_OCR_TIMEOUT_MS` (Default `45000`)
- `LEGALCHAT_OCR_FILE_CACHE_TTL_MS` (Default `7200000`)
- `LEGALCHAT_OCR_S3_PRESIGN_EXPIRES_SEC` (Default `300`)

### Erstmalige Einrichtung

1. **Logto Admin Console öffnen**: http://localhost:3002
2. **Admin-Account erstellen**
3. **Application erstellen**:
   - Type: "Next.js (App Router)"
   - Name: "LegalChat"
   - Redirect URI: `http://localhost:3210/api/auth/callback/logto`
4. **Credentials in `.env` eintragen**

## ⚠️ Bekannte Probleme

Siehe detaillierte Dokumentation:

→ **[OPEN_ISSUES.md](docs/OPEN_ISSUES.md)**

### Zusammenfassung
- ✅ Login-Button in LegalChat UI funktioniert wieder (Gateway-Fix aktiv)
- ℹ️ Optionale Login-Hilfe bleibt unter http://localhost:3211/login verfügbar
- ✅ Struktureller Bild-Upload-Fix fuer OpenRouter/MinIO dokumentiert und als Default hinterlegt

## 📚 Dokumentation

| Dokument | Beschreibung |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Detaillierte Installationsanleitung |
| [docker/README_LOGIN_FIX.md](docker/README_LOGIN_FIX.md) | Login-Proxy Dokumentation |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Systemarchitektur (🚧 in Arbeit) |
| [docs/OPEN_ISSUES.md](docs/OPEN_ISSUES.md) | Offene Probleme & Lösungsansätze |

## 🔁 CI/CD

Dieses Repo enthält jetzt GitHub Actions:

- `.github/workflows/ci.yml`: Syntax- und Compose-Validierung bei Push/PR
- `.github/workflows/deploy-hetzner.yml`: manueller Deploy nach Hetzner per `workflow_dispatch`

Benötigte GitHub Secrets für Deploy:

- `HETZNER_HOST`
- `HETZNER_USER`
- `HETZNER_SSH_PRIVATE_KEY`
- optional: `HETZNER_SSH_PORT`

## 🔗 Links

- **LegalChat UI**: http://localhost:3210
- **Login Hilfe**: http://localhost:3211
- **Logto Admin**: http://localhost:3002
- **MinIO Console**: http://localhost:9001

## 📝 Lizenz

MIT License - Siehe [LICENSE](LICENSE)
