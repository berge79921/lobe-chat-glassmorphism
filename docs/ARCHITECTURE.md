# Systemarchitektur: LegalChat Glassmorphism

> 🚧 **Diese Dokumentation ist in Arbeit**

## Übersicht

Dieses Dokument beschreibt die Systemarchitektur der LegalChat-Installation mit Glassmorphism-Theme und Logto-Authentifizierung.

## Inhaltsverzeichnis

1. [Systemkomponenten](#systemkomponenten)
2. [Datenfluss](#datenfluss)
3. [Multimodaler Bildfluss](#multimodaler-bildfluss)
4. [Authentifizierungs-Architektur](#authentifizierungs-architektur)
5. [Netzwerk-Konfiguration](#netzwerk-konfiguration)
6. [Sicherheitskonzept](#sicherheitskonzept)
7. [MCP Lane (Intern)](#mcp-lane-intern)

---

## Systemkomponenten

### 1. LegalChat (Main Application)
- **Image**: `lobehub/lobe-chat-database:latest`
- **Port**: 3210
- **Framework**: Next.js 15 + Auth.js 5.0.0-beta.30
- **Funktion**: Chat-UI, AI-Integration, Session-Management

### 2. Logto (Authentication Provider)
- **Image**: `svhd/logto:latest`
- **Ports**: 3001 (OIDC), 3002 (Admin)
- **Protokoll**: OpenID Connect (OIDC)
- **Funktion**: Benutzerauthentifizierung, Token-Management

### 3. PostgreSQL (Database)
- **Image**: `pgvector/pgvector:pg16`
- **Port**: 5432
- **Datenbanken**:
  - `lobe` - LegalChat Daten
  - `logto` - Logto Benutzerdaten
- **Funktion**: Persistente Datenspeicherung, Vektor-Suche

### 4. MinIO (Object Storage)
- **Image**: `minio/minio`
- **Ports**: 9000 (API), 9001 (Console)
- **Funktion**: S3-kompatibler Dateispeicher für Uploads

### 5. Login Proxy (Workaround)
- **Image**: `node:20-alpine`
- **Port**: 3211
- **Funktion**: Next-Auth v5 GET/POST Konvertierung

---

## Datenfluss

### Normaler Betrieb (authentifizierter User)

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Browser │────▶│ LegalChat │────▶│  AI API  │
│          │◄────│ Port 3210│◄────│OpenRouter│
└──────────┘     └──────────┘     └──────────┘
       │
       │    ┌──────────┐
       └───▶│  MinIO   │
            │Port 9000 │
            └──────────┘
```

### Authentifizierungs-Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Browser │────▶│  Proxy   │────▶│  Logto   │
│          │     │Port 3211 │     │Port 3001 │
└──────────┘     └──────────┘     └──────────┘
       │                                │
       │         ┌──────────┐           │
       └────────▶│ LegalChat │◀──────────┘
                 │Port 3210 │
                 └──────────┘
```

---

## Multimodaler Bildfluss

### Ziel

Verarbeitung von Bildern mit externen Cloud-Providern (z. B. OpenRouter/Google), ohne dass der Provider auf private `localhost`- oder LAN-URLs zugreifen muss.

### Architektur

```
┌──────────┐   Upload    ┌──────────┐  presigned URL   ┌───────────────┐
│ Browser  │────────────▶│  MinIO   │─────────────────▶│   LegalChat    │
└──────────┘             └──────────┘                  │ image->base64 │
                                                        └──────┬────────┘
                                                               │ data URI
                                                               ▼
                                                          OpenRouter API
```

### Konfigurationsprinzip

1. `S3_SET_ACL=0`  
   Objekte bleiben privat, LegalChat nutzt presigned Preview-URLs.
2. `LLM_VISION_IMAGE_USE_BASE64=1`  
   LegalChat uebertraegt Bilder als Base64 (statt URL) an externe Modelle.
3. `SSRF_ALLOW_PRIVATE_IP_ADDRESS=0` + `SSRF_ALLOW_IP_ADDRESS_LIST=<MINIO_IP>`  
   SSRF-Schutz bleibt aktiv; nur die eigene MinIO-IP ist erlaubt.
4. `S3_PUBLIC_DOMAIN` darf nicht auf `localhost` zeigen.

### Wirkung

- Kein Fehler mehr: `Cannot fetch from private/localhost URLs`
- Keine dauerhafte oeffentliche Freigabe des Buckets erforderlich
- Gleiche Konfiguration fuer lokale Uebergabe und Produktion nutzbar

---

## Authentifizierungs-Architektur

### Komponenten-Interaktion

1. **LegalChat** (Next-Auth v5)
   - Verwendet `@auth/core` 0.40.0
   - Provider: `next-auth/providers/logto`
   - Session-Strategie: JWT (default)

2. **Logto** (OIDC Provider)
   - Endpunkt: `/.well-known/openid-configuration`
   - Authorization Flow: Authorization Code + PKCE
   - Token: ID Token (ES384), Access Token

3. **Login Proxy** (Node.js)
   - Problem: Next-Auth v5 erwartet POST, UI macht GET
   - Lösung: Proxy konvertiert GET → POST
   - Routing: Port 3211 → Port 3210

### Konfigurations-Parameter

| Parameter | Wert | Beschreibung |
|-----------|------|--------------|
| `AUTH_LOGTO_ISSUER` | `http://192.168.1.240:3001/oidc` | OIDC Discovery URL |
| `AUTH_LOGTO_ID` | `berge79921` | Client ID |
| `AUTH_LOGTO_SECRET` | `X6duaf3@L` | Client Secret |
| `NEXTAUTH_URL` | `http://localhost:3210` | Callback Base URL |

---

## Netzwerk-Konfiguration

### Docker Network

Alle Services laufen im Docker-Compose-Network:
- **Name**: `lobe-chat-glassmorphism_default`
- **Mode**: Bridge

### Service-Discovery

| Service | Container Name | Interne URL | Externe URL |
|---------|---------------|-------------|-------------|
| LegalChat | `lobe-chat-glass` | `http://lobe-chat-glass:3210` | `http://localhost:3210` |
| Logto | `lobe-logto` | `http://lobe-logto:3001` | `http://localhost:3001` |
| PostgreSQL | `lobe-postgres` | `postgresql://lobe-postgres:5432` | `localhost:5432` |
| MCP Super RIS PostgreSQL | `mcp-super-ris-postgres` | `postgresql://mcp-super-ris-postgres:5432/super_ris` | _nicht exponiert_ |
| MinIO | `lobe-minio` | `http://lobe-minio:9000` | `http://localhost:9000` |

### Host IP Referenz

Da Container nicht über `localhost` miteinander kommunizieren können:
- **Host IP**: `192.168.1.240` (anpassen an dein Netzwerk)
- **Logto Endpoint**: `http://192.168.1.240:3001`
- **MinIO Endpoint**: `http://192.168.1.240:9000`

---

## Sicherheitskonzept

### Secrets-Management

Secrets werden über Environment Variables injiziert:
- Niemals in Git committen (`.gitignore`)
- Distribution über `.env.example` Templates
- Generierung via `openssl rand -base64 32`

### TLS/SSL

Aktuell: Keine TLS-Verschlüsselung (lokale Entwicklung)

Für Produktion empfohlen:
- Traefik oder Nginx als Reverse Proxy
- Let's Encrypt Zertifikate
- `https://` Endpunkte

### Netzwerk-Sicherheit

- Interne Services (PostgreSQL) nur im Docker-Netzwerk erreichbar
- Externe Ports nur für UI und API notwendig
- Logto Admin Console (`:3002`) sollte gegebenenfalls restricted werden
- SSRF-Schutz bleibt standardmaessig aktiv; nur explizit erlaubte MinIO-IP darf fuer interne Bild-Fetches verwendet werden

---

## MCP Lane (Intern)

Ziel: George kann interne MCP-Tools fuer `deep research` und `pruefungsmodus` nutzen, ohne oeffentliche Exponierung.

### Architekturprinzip

```
Browser -> legalchat.net -> login-proxy/lobe -> mcp_internal network -> MCP Server
```

- MCP-Netzwerk ist intern (`internal: true`)
- Keine oeffentlichen MCP-Ports
- Nur `login-proxy` wird an das MCP-Netzwerk gehaengt
- MCP-Server werden als stdio-Prozesse ueber interne HTTP-Bridges betrieben
- `mcp-zivilrecht` nutzt `mcp-super-ris-postgres` im privaten MCP-Netz
- Option fuer spaeter: separater MCP-Gateway mit OIDC/JWT-Autorisierung

### Geplanter MCP `zivil-pruefung`

Der MCP `zivil-pruefung` ist vorgemerkt und befindet sich im Build/Test.

Kurzprofil:
- Skill heute: Orchestrierung (Exam Harness, Scoring, Fusion)
- MCP morgen: API-faehige Tool-Schnittstelle (10 Tools, Tier 1 + Tier 2)
- Kritischer Fix: `fp_runner._p` auf stderr patchen, damit MCP-stdio JSON-RPC sauber bleibt

Siehe Detailkonzept: [MCP_DEPLOYMENT.md](MCP_DEPLOYMENT.md)

---

## Offene Themen

- [ ] Load Balancing für Production
- [ ] Redis für Session-Speicher (statt JWT)
- [ ] Monitoring/Logging (Prometheus/Grafana)
- [ ] Backup-Strategie für PostgreSQL
- [ ] Kubernetes-Deployment
- [ ] MCP Gateway mit OIDC/JWT fuer externe Client-Freigabe (optional)

---

## Verwandte Dokumente

- [OPEN_ISSUES.md](OPEN_ISSUES.md) - Bekannte Probleme
- [LOGTO_M2M.md](LOGTO_M2M.md) - Logto M2M (Service-to-Service) Rollen & Tokens
- [MCP_DEPLOYMENT.md](MCP_DEPLOYMENT.md) - MCP Deployment Blueprint (intern + spaeter extern)
- [../INSTALL.md](../INSTALL.md) - Installationsanleitung
- [../docker/README_LOGIN_FIX.md](../docker/README_LOGIN_FIX.md) - Login Proxy Details
