# Schnell-Installation

## ✅ Voraussetzungen erfüllt

Die `.env` Datei ist bereits mit einem OpenRouter API Key konfiguriert.

## 🚀 Schnellstart

```bash
cd /Users/reinhardberger/HCS/lobe-chat-custom
./start.sh
```

## 🔧 Manuelle Schritte (falls nötig)

### 1. Logto einrichten (einmalig)

Nach dem ersten Start:

1. Öffne http://localhost:3002
2. Erstelle Admin-Account
3. Erstelle Application:
   - Type: "Next.js (App Router)"
   - Name: "LegalChat"
   - Redirect URI: `http://localhost:3210/api/auth/callback/logto`
4. Kopiere Client ID & Secret in `.env`:
   ```
   AUTH_LOGTO_ID=deine-client-id
   AUTH_LOGTO_SECRET=dein-client-secret
   ```
5. Neustarten: `cd docker && docker compose restart lobe`

### 2. OpenRouter ist bereit

Der erste OpenRouter API Key (OPENROUTER_API_KEY_1) ist bereits konfiguriert.

Nach dem Login unter http://localhost:3210:
- Einstellungen → Sprachmodell → OpenRouter
- API Key sollte bereits funktionieren

### 3. Vision-Pipeline fuer Bilder pruefen

Diese Installation nutzt standardmaessig den strukturellen Fix fuer externe Provider:
- `S3_SET_ACL=0`
- `LLM_VISION_IMAGE_USE_BASE64=1`
- `SSRF_ALLOW_PRIVATE_IP_ADDRESS=0`
- `SSRF_ALLOW_IP_ADDRESS_LIST=<MinIO-Host-IP>`

Pruefen:
```bash
cd docker
docker compose up -d
docker inspect lobe-chat-glass --format '{{range .Config.Env}}{{println .}}{{end}}' | \
  egrep 'S3_SET_ACL|LLM_VISION_IMAGE_USE_BASE64|SSRF_ALLOW_PRIVATE_IP_ADDRESS|SSRF_ALLOW_IP_ADDRESS_LIST|S3_PUBLIC_DOMAIN'
```

## 📋 Alle Befehle

```bash
# Starten
./start.sh

# Oder manuell:
cd docker && docker compose up -d

# Stoppen
cd docker && docker compose down

# Logs
cd docker && docker compose logs -f lobe

# Neustarten
cd docker && docker compose restart lobe
```

## 🔗 URLs

| Service | URL |
|---------|-----|
| **LegalChat UI** | http://localhost:3210 |
| Logto Admin | http://localhost:3002 |
| MinIO Console | http://localhost:9001 |

## 🎨 Weitere API Keys

Weitere OpenRouter Keys verfügbar in:
```
/Users/reinhardberger/HCS/.env
```

Keys: OPENROUTER_API_KEY_1 bis OPENROUTER_API_KEY_273

Um einen anderen Key zu verwenden, einfach in `.env` austauschen.

## 🗑️ Vollständiges Löschen

```bash
cd docker
docker compose down -v
rm -rf data/ s3_data/
```

Dadurch werden **alle Daten gelöscht** (Chats, Einstellungen, etc.)!
