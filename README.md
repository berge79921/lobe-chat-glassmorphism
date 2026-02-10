# LobeChat - Glassmorphism Design

Eine modifizierte LobeChat-Installation mit dem Design des Kostenrechners (Glassmorphism, abgerundete Karten, Dark Mode).

## ✅ Bereit zum Starten

**Die `.env` ist bereits konfiguriert mit:**
- ✅ OpenRouter API Key (aus Ihrer Key-Rotation)
- ✅ Generiertem Auth Secret
- ✅ Datenbank & MinIO Einstellungen

## 🚀 Schnellstart

```bash
cd /Users/reinhardberger/HCS/lobe-chat-custom
./start.sh
```

Dann öffnen: http://localhost:3210

## 🎨 Features

- **Glassmorphism Design**: Backdrop-blur, transparenter Hintergrund, dekorativer Glow-Effekte
- **OpenRouter Integration**: Bereits konfiguriert mit API Key
- **Projekt-Management**: Organisation in Workspaces und Projekten
- **Knowledge Base**: Datei-Upload pro Projekt (PDF, Word, etc.)
- **Multi-User**: Authentifizierung via Logto (einmalig einrichten)
- **Dark Mode Only**: Optimiert für das Kostenrechner-Farbschema

## 📁 Projekt-Struktur

```
lobe-chat-custom/
├── docker/
│   ├── docker-compose.yml      # Container-Setup
│   └── custom-css/
│       └── custom.css          # Glassmorphism-Theme (Live-Mount)
├── src/styles/
│   └── glassmorphism-theme.css # Source CSS
├── .env                        # ✅ Bereits konfiguriert
├── .env.example                # Konfigurationsvorlage
├── start.sh                    # Start-Skript
├── INSTALL.md                  # Detaillierte Anleitung
└── README.md                   # Diese Datei
```

## 🔧 Einmalig: Logto einrichten

1. Nach dem Start: http://localhost:3002 öffnen
2. Admin-Account erstellen
3. Application erstellen:
   - Type: "Next.js (App Router)"
   - Redirect URI: `http://localhost:3210/api/auth/callback/logto`
4. Client ID & Secret in `.env` eintragen
5. `docker compose restart lobe`

Danach ist alles einsatzbereit!

## 🎨 Design-Anpassung

Das Theme befindet sich in:
```
src/styles/glassmorphism-theme.css
```

Änderungen sind nach Container-Neustart sofort sichtbar:
```bash
cd docker && docker compose restart lobe
```

### Design-Merkmale

| Element | Wert |
|---------|------|
| Border Radius (Cards) | 2.5rem (40px) |
| Border Radius (Buttons) | 1.25rem (20px) |
| Backdrop Blur | 24px-40px |
| Primary Color | Blue (#3b82f6) |
| Background | Slate 950 (#020617) |
| Accent | Amber (#f59e0b) |

## 🔑 API Keys

Der erste OpenRouter Key (OPENROUTER_API_KEY_1) ist bereits aktiviert.

Weitere Keys verfügbar in:
```
/Users/reinhardberger/HCS/.env
```
(OPENROUTER_API_KEY_1 bis OPENROUTER_API_KEY_273)

## 🌐 Zugriff

| Service | URL | Beschreibung |
|---------|-----|--------------|
| **LobeChat** | http://localhost:3210 | Haupt-UI mit Chat |
| Logto Admin | http://localhost:3002 | Benutzerverwaltung |
| MinIO | http://localhost:9001 | Datei-Speicher |

## 🛠️ Befehle

```bash
# Starten
./start.sh

# Stoppen
cd docker && docker compose down

# Logs anzeigen
cd docker && docker compose logs -f lobe

# Neustarten
cd docker && docker compose restart lobe

# Mit Daten löschen
cd docker && docker compose down -v && rm -rf data/ s3_data/
```

## 💾 Backup

```bash
cd docker
docker compose exec -T postgresql pg_dump -U postgres lobe > backup.sql
tar -czf lobe-backup-$(date +%Y%m%d).tar.gz data/ s3_data/ backup.sql
```

## 📄 Lizenz

LobeChat: [Apache 2.0](https://github.com/lobehub/lobe-chat/blob/main/LICENSE)  
Custom Theme: MIT License
