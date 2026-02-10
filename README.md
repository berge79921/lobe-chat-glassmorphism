# LegalChat ⚖️

Ein KI-gestützter Rechtsassistent mit benutzerdefiniertem Glassmorphism-Theme.

> **Powered by LobeChat** • **KI-Jurist: George** • **Secure Auth with Logto**

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
- **Avatar**: Professionelles LEGO-Style Design
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
│ Browser / Lobe UI     │────▶│ Auth Gateway          │────▶│ LobeChat App    │
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

### Produktionsprofil: Bildverarbeitung mit OpenRouter

Fuer stabile Bildverarbeitung in Produktion (ohne `localhost`-Probleme) nutzt dieses Repo jetzt standardmaessig folgende Architektur:

1. Bilder bleiben in MinIO (private Objekte, kein `public-read`)
2. LobeHub erzeugt presigned Preview-URLs
3. LobeHub konvertiert die Bilddaten serverseitig in Base64
4. OpenRouter erhaelt nur Base64-Daten, keine private URL

Pflicht-Variablen in `docker/.env`:

| Variable | Sollwert |
|----------|----------|
| `S3_SET_ACL` | `0` |
| `LLM_VISION_IMAGE_USE_BASE64` | `1` |
| `SSRF_ALLOW_PRIVATE_IP_ADDRESS` | `0` |
| `SSRF_ALLOW_IP_ADDRESS_LIST` | Host-IP von MinIO, z.B. `192.168.1.240` |
| `S3_PUBLIC_DOMAIN` | Keine localhost-URL |

### Erstmalige Einrichtung

1. **Logto Admin Console öffnen**: http://localhost:3002
2. **Admin-Account erstellen**
3. **Application erstellen**:
   - Type: "Next.js (App Router)"
   - Name: "LobeChat"
   - Redirect URI: `http://localhost:3210/api/auth/callback/logto`
4. **Credentials in `.env` eintragen**

## ⚠️ Bekannte Probleme

Siehe detaillierte Dokumentation:

→ **[OPEN_ISSUES.md](docs/OPEN_ISSUES.md)**

### Zusammenfassung
- ✅ Login-Button in LobeChat UI funktioniert wieder (Gateway-Fix aktiv)
- ℹ️ Optionale Login-Hilfe bleibt unter http://localhost:3211/login verfügbar
- ✅ Struktureller Bild-Upload-Fix fuer OpenRouter/MinIO dokumentiert und als Default hinterlegt

## 📚 Dokumentation

| Dokument | Beschreibung |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Detaillierte Installationsanleitung |
| [docker/README_LOGIN_FIX.md](docker/README_LOGIN_FIX.md) | Login-Proxy Dokumentation |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Systemarchitektur (🚧 in Arbeit) |
| [docs/OPEN_ISSUES.md](docs/OPEN_ISSUES.md) | Offene Probleme & Lösungsansätze |

## 🔗 Links

- **LobeChat UI**: http://localhost:3210
- **Login Hilfe**: http://localhost:3211
- **Logto Admin**: http://localhost:3002
- **MinIO Console**: http://localhost:9001

## 📝 Lizenz

MIT License - Siehe [LICENSE](LICENSE)
