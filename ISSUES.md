# Issue Log: LobeChat Glassmorphism

> Projekt: LobeChat mit Glassmorphism Theme  
> Repository: https://github.com/berge79921/lobe-chat-glassmorphism  
> Letzte Aktualisierung: 10. Februar 2026

---

## Issue #1: Bild-Upload funktioniert nicht mit OpenRouter

### Status
✅ **Geloest und live verifiziert** (2026-02-10, 12:58-12:59 UTC)

### Zusammenfassung
Bilder wurden erfolgreich zu MinIO hochgeladen, aber OpenRouter scheiterte am Abruf privater `localhost`-URLs.  
Die Architektur wurde auf einen provider-unabhaengigen Bildpfad umgestellt (Presigned URL + serverseitige Base64-Konvertierung) und im echten UI-Live-Test erfolgreich bestaetigt.

### Fehlermeldung
```json
{
  "error": {
    "code": 400,
    "message": "Cannot fetch from private/localhost URLs: http://localhost:9000/lobe/files/491868/82bec7e3-5a60-4ebd-af87-9151657e5848.jpeg",
    "metadata": {
      "provider_name": "Google"
    }
  }
}
```

### Funktionsmatrix

| Komponente | Status | Details |
|------------|--------|---------|
| Text-Chat mit OpenRouter | ✅ Funktioniert | GM 3.0 Flash Preview erfolgreich getestet |
| Dokumenten-Upload (PDF, TXT) | ✅ Funktioniert | Inhalt wird als Text extrahiert und gesendet |
| Bild-Upload zu MinIO | ✅ Funktioniert | Datei wird korrekt in S3-Bucket gespeichert |
| Bild-Verarbeitung durch OpenRouter | ✅ Funktioniert | Live-E2E erfolgreich: `file.checkFileHash=200`, `file.createFile=200`, `aiChat.sendMessageInServer=200` |

### Technische Analyse

#### Architektur-Problem

```
┌─────────────┐      Bild-URL      ┌─────────────────┐      ┌──────────────┐
│   Browser   │ ───────────────────▶│   OpenRouter    │ ────▶│ Google Model │
│  (User)     │  http://localhost:9000│  (API Gateway)  │      │              │
└─────────────┘                     └─────────────────┘      └──────────────┘
                                          │
                                          ▼
                              "Cannot fetch from private/localhost URLs"
```

#### Root Cause
1. Bild-Upload zu MinIO war korrekt.
2. LobeChat gab eine private URL (`http://localhost:9000/...`) an OpenRouter weiter.
3. OpenRouter/Google blockt private oder localhost-Ziele per Design.
4. Die MinIO-URL war anonym zusaetzlich nicht lesbar (`403 AccessDenied`), damit war URL-basiertes Fetching doppelt fragil.

#### Warum Dokumente funktionieren, Bilder aber nicht

| Dateityp | Verarbeitung | Grund |
|----------|-------------|-------|
| **Dokumente (PDF, TXT)** | Inhalt wird ausgelesen und als Text im Prompt gesendet | Kein URL-Zugriff nötig |
| **Bilder (JPG, PNG)** | URL wird an OpenRouter gesendet, Modell lädt Bild herunter | **Erfordert öffentlich erreichbare URL** |

### Implementierte strukturelle Loesung

Die Konfiguration wurde auf einen robusten, produktionsfaehigen Datenfluss standardisiert:

1. `S3_SET_ACL=0`  
   MinIO-Objekte bleiben privat; LobeHub nutzt presigned Preview-URLs.
2. `LLM_VISION_IMAGE_USE_BASE64=1`  
   Bilder werden serverseitig als Base64 in den Provider-Request eingebettet.
3. `SSRF_ALLOW_PRIVATE_IP_ADDRESS=0` + `SSRF_ALLOW_IP_ADDRESS_LIST=<MINIO_IP>`  
   SSRF-Schutz bleibt aktiv; nur die eigene MinIO-IP wird erlaubt.
4. `S3_PUBLIC_DOMAIN` zeigt nicht mehr auf `localhost`.
5. `NEXT_PUBLIC_S3_DOMAIN` wurde als deprecated aus dem Compose-Pfad entfernt.

### Neue Standard-Konfiguration (docker/.env.example)
```yaml
# S3 Storage (MinIO)
S3_ENDPOINT=http://192.168.1.240:9000
S3_PUBLIC_DOMAIN=http://192.168.1.240:9000
S3_BUCKET=lobe
S3_ACCESS_KEY_ID=admin
S3_SECRET_ACCESS_KEY=***
S3_ENABLE_PATH_STYLE=1
S3_SET_ACL=0
S3_PREVIEW_URL_EXPIRE_IN=1800

# Vision hardening
LLM_VISION_IMAGE_USE_BASE64=1
SSRF_ALLOW_PRIVATE_IP_ADDRESS=0
SSRF_ALLOW_IP_ADDRESS_LIST=192.168.1.240
```

### Warum das strukturell ist

- Kein Tunnel- oder Provider-spezifischer Hack
- Kein oeffentliches `public-read` als Zwang
- Funktioniert fuer OpenRouter und andere externe Cloud-Provider gleich
- Sicherer Betrieb durch SSRF-Allowlist statt globalem Freischalten privater Netze

### Finaler Live-Nachweis (2026-02-10, Start 12:58:55Z)

Echter Browser-Flow wurde komplett durchgespielt (Logto Login -> Bild-Upload -> Nachricht senden):

- Testbild: `/Users/reinhardberger/Downloads/WhatsApp Image 2026-02-10 at 09.16.16.jpeg`
- UI/Network Ergebnis:
  - `POST /trpc/lambda/file.checkFileHash` -> `200`
  - `POST /trpc/lambda/file.createFile` -> `200`
  - `POST /trpc/lambda/aiChat.sendMessageInServer` -> `200`
- Chat-Antwort wurde generiert (OpenRouter/Claude Sonnet im Testlauf).
- DB-Beleg:
  - Datei erstellt: `files.id=file_kKgaCT7Ithik` (2026-02-10 12:59:04+00)
  - Verknuepfung erstellt: `messages_files.file_id=file_kKgaCT7Ithik` -> `message_id=msg_up7NnepMgv4Uby`
- Log-Beleg:
  - Kein Treffer fuer `Cannot fetch from private/localhost URLs`
  - Kein Treffer fuer `ProviderBizError`
- Artefakte:
  - `artifacts-live-test-final-pass-v2/result.json`
  - `artifacts-live-test-final-pass-v2/05-after-upload.png`
  - `artifacts-live-test-final-pass-v2/06-after-send.png`

### Querpruefung (fuer Kollegen)

1. `docker/.env` gegen die oben dokumentierte Standard-Konfiguration pruefen.
2. `cd docker && docker compose up -d --force-recreate lobe`
3. Vor dem manuellen UI-Test Startzeit merken:
   `START_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")`
4. In der UI ein JPG/PNG hochladen und senden (mit vision-faehigem Modell).
5. Direkt danach Logs pruefen:
   `docker logs --since "$START_TS" lobe-chat-glass 2>&1 | rg -n "Cannot fetch from private/localhost URLs|ProviderBizError|file.checkFileHash|file.createFile|aiChat.sendMessageInServer"`
6. DB querpruefen:
   - `docker exec -i lobe-postgres psql -U postgres -d lobe -c "SELECT id,user_id,file_type,name,url,created_at FROM files ORDER BY created_at DESC LIMIT 5;"`
   - `docker exec -i lobe-postgres psql -U postgres -d lobe -c "SELECT mf.file_id,mf.message_id,m.role,m.created_at FROM messages_files mf JOIN messages m ON m.id=mf.message_id ORDER BY m.created_at DESC LIMIT 5;"`
7. Erwartetes Ergebnis:
   - Keine alte Fehlermeldung (`Cannot fetch from private/localhost URLs`)
   - Upload + Send Endpunkte mit `200`
   - Neue Zeilen in `files` und `messages_files`
   - Assistant-Antwort im Chat

### Verbleibende Risiken

- Base64 vergroessert Request-Payloads (Kosten/Latenz bei sehr grossen Bildern).
- Bei Host-IP-Wechsel muss `SSRF_ALLOW_IP_ADDRESS_LIST` angepasst werden.
- Optionaler naechster Schritt fuer Produktion: eigenes HTTPS-Objektdomain (S3/R2) + CDN.
- Falls ein Modell keine Vision-Capability hat, erscheint kein `image/*` Upload-Input fuer diesen Modellkontext.

### Verwandte Issues

- Keine

### Referenzen

- OpenRouter Docs: https://openrouter.ai/docs
- MinIO Docs: https://min.io/docs
- LobeChat S3 Config: https://lobehub.com/docs/self-hosting/environment-variables/s3

---

## Issue #2: [RESOLVED] Authentifizierungs-Fehler mit Logto

### Status
✅ **Gelöst** durch Auth-Gateway

### Ursache
Next-Auth v5 Beta erwartet POST-Requests für Provider-Login, LobeChat sendet GET.

### Lösung
Auth-Gateway auf Port 3210 übersetzt GET → POST transparent.

### Commit
`e736084` - fix(auth): restore Logto sign-in by translating GET provider login to CSRF POST

---

## Issue #3: [RESOLVED] Dokumenten-Upload S3-Konfiguration

### Status
✅ **Gelöst**

### Problem
S3_ENDPOINT war auf `localhost:9000` gesetzt, Container konnten MinIO nicht erreichen.

### Lösung
S3_ENDPOINT auf `http://192.168.1.240:9000` (Host-IP) geändert.

### Commit
`c65458a` - fix(s3): correct MinIO configuration for file uploads

---

## Allgemeine Hinweise

### Support-Kontakt
Bei technischen Fragen zu diesem Projekt:
1. Repository prüfen: https://github.com/berge79921/lobe-chat-glassmorphism
2. Dokumentation lesen: docs/ARCHITECTURE.md, docs/OPEN_ISSUES.md
3. Neue Issues im GitHub-Repository erstellen

### Änderungshistorie

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-10 | Codex | Issue #1 mit finalem Live-E2E-Nachweis + Querpruefung aktualisiert (Status auf geloest) |
| 2026-02-10 | Codex | Issue #1 auf strukturelle Loesung umgestellt (Base64 + presigned + SSRF-Allowlist) |
| 2026-02-10 | Kimi | Issue #1 hinzugefügt (Bild-Upload) |
| 2026-02-10 | Kimi | Issue #2 als gelöst markiert |
| 2026-02-10 | Kimi | Issue #3 als gelöst markiert |
