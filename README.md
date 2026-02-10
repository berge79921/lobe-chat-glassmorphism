# LobeChat Glassmorphism

Eine LobeChat-Installation mit benutzerdefiniertem Glassmorphism-Theme (Kostenrechner Design) und Logto-Authentifizierung.

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
- **Workaround**: Login-Proxy für Next-Auth v5 Kompatibilität
- **Zugriff**: http://localhost:3211 (Login-Hilfe)

### AI Provider
- **Primär**: OpenRouter (GPT-4, Claude, etc.)
- **Fallback**: OpenAI, Anthropic, Google (optional)

### Infrastruktur
- **Datenbank**: PostgreSQL mit pgvector
- **Storage**: MinIO S3-kompatibel
- **Container**: Docker Compose

## 📋 Architektur

Detaillierte Architekturdokumentation:

→ **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** (in Arbeit)

Übersicht der Komponenten:
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   LobeChat UI   │────▶│  Login Proxy    │────▶│  Logto (OIDC)   │
│   Port: 3210    │     │   Port: 3211    │     │   Port: 3001    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   PostgreSQL    │     │     MinIO       │
│   Port: 5432    │     │  Port: 9000/1   │
└─────────────────┘     └─────────────────┘
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
- ❌ Login-Button in LobeChat UI funktioniert nicht (Next-Auth v5 Beta Bug)
- ✅ Workaround: Login über http://localhost:3211

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
