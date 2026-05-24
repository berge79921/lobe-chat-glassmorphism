# OpenLaw Mail API

Stand: 1. April 2026

Diese Dokumentation beschreibt den aktuell implementierten Mail-Zugriff auf `https://www.openlaw.cc`.
Sie basiert auf dem produktiven Code in `docker/openlaw-auth/` und auf Live-Tests gegen die laufende Instanz.

## Überblick

Es gibt zwei API-Arten:

1. Öffentlicher Read-Shortcut mit HTTP Basic Auth:
   `GET /mail/{mailbox}/{folder}/latest`
2. Sessionbasierte JSON-API für die komplette Mail-App:
   `GET/POST /mail/api/*`

Die Session-API ist die eigentliche Arbeits-API der Weboberfläche. Der `latest`-Endpoint ist ein schmaler programmatischer Direktzugriff auf die neueste Mail einer Mailbox.

## Basis-URL

```text
https://www.openlaw.cc
```

Der kanonische Mail-Prefix ist:

```text
https://www.openlaw.cc/mail
```

`/mailbox` existiert als Alias und leitet auf `/mail` um, ist für API-Clients aber nicht nötig.

## Verfügbare Mailboxen

Unterstützte Mailbox-Keys:

- `inbox`
- `office`
- `kanzlei`
- `buero`
- `thomas`
- `george`
- `berger`

Typische Zuordnung:

- `office` -> `office@openlaw.cc`
- `kanzlei` -> `kanzlei@openlaw.cc`
- `george` -> `george@openlaw.cc`

## Ordner-Slugs

Unterstützte Folder-Slugs:

- `inbox` -> `INBOX`
- `sent` -> `Sent`
- `drafts` -> `Drafts`
- `draft` -> `Drafts`
- `trash` -> `Trash`

Ein ungültiger Folder liefert `400 INVALID_FOLDER`.
Ein gültiger, aber leerer Folder liefert bei `latest` in der Regel `404 NOT_FOUND`.

## Authentifizierung

### 1. Basic Auth für `latest`

Der Read-Shortcut `GET /mail/{mailbox}/{folder}/latest` akzeptiert HTTP Basic Auth.

Empfohlen:

- Username: volle Mailadresse, z. B. `office@openlaw.cc`
- Passwort: das Passwort dieser Mailbox

Zusätzlich akzeptiert der Server derzeit auch den lokalen Teil als Username, z. B. `office`.
Für Clients und Dokumentation sollte trotzdem die volle Adresse verwendet werden.

### 2. Session für `/mail/api/*`

Die JSON-API unter `/mail/api/*` benötigt eine gültige Session-Cookie.
Der Login erfolgt lokal über OpenLaw selbst, nicht über einen externen Provider.

Login-Request:

```http
POST /login
Content-Type: application/x-www-form-urlencoded
```

Form-Felder:

- `email`
- `password`
- `callbackUrl`

Bei Erfolg:

- `302 Found`
- `Set-Cookie: openlaw.sid=...`

Session prüfen:

```http
GET /api/auth/session
```

Ohne Session:

```json
{}
```

Mit Session:

```json
{
  "user": {
    "email": "george@openlaw.cc",
    "primaryEmail": "george@openlaw.cc",
    "name": "George",
    "accountKey": "george"
  }
}
```

## Allgemeines Antwortformat

JSON-Endpunkte liefern grundsätzlich:

Erfolg:

```json
{
  "ok": true,
  "data": {}
}
```

Fehler:

```json
{
  "ok": false,
  "error": "Beschreibung",
  "code": "ERROR_CODE"
}
```

Ausnahme:

- `GET /mail/api/attachment` liefert Binärdaten, nicht JSON.

## Öffentlicher Endpoint: Neueste Nachricht

### Route

```http
GET /mail/{mailbox}/{folder}/latest
```

Beispiele:

```text
GET /mail/office/inbox/latest
GET /mail/george/sent/latest
GET /mail/kanzlei/drafts/latest
```

### Verhalten ohne Auth

Wenn der Request HTML-Navigation erwartet:

- `Accept: text/html`
- Antwort: `302` auf `/login?...`

Wenn der Request JSON erwartet:

- `Accept: application/json`
- Antwort: `401`
- `WWW-Authenticate: Basic realm="OpenLaw Mail {mailbox}", charset="UTF-8"`

Beispiel:

```bash
curl -H 'Accept: application/json' \
  https://www.openlaw.cc/mail/office/inbox/latest
```

Antwort:

```json
{
  "ok": false,
  "error": "Mailbox password required",
  "code": "MAIL_PASSWORD_REQUIRED"
}
```

Wichtig:

- Auch bei falschem Passwort wird der Fehler nach außen derzeit auf denselben `401`-Challenge vereinheitlicht.
- Clients sollten also auf `401` reagieren und Credentials prüfen, nicht auf einen separaten "wrong password"-Code warten.

### Erfolgsbeispiel

```bash
curl -u 'office@openlaw.cc:<MAILBOX_PASSWORD>' \
  https://www.openlaw.cc/mail/office/inbox/latest
```

Beispielantwort:

```json
{
  "ok": true,
  "data": {
    "accessMode": "password",
    "accountKey": "office",
    "folder": "INBOX",
    "message": {
      "accountKey": "office",
      "attachments": [
        {
          "filename": "api-send-check.txt",
          "contentType": "text/plain",
          "size": 27
        }
      ],
      "bcc": [],
      "cc": [],
      "date": "2026-03-31T22:49:13.000Z",
      "from": {
        "address": "george@openlaw.cc",
        "name": "George · OpenLaw"
      },
      "htmlBody": "<p>Direkter API-Sendetest.</p>",
      "messageId": "<...>",
      "seen": false,
      "subject": "API send verification 20260401-0050",
      "textBody": "Direkter API-Sendetest.",
      "to": [
        {
          "address": "office@openlaw.cc",
          "name": ""
        }
      ],
      "uid": 12
    }
  }
}
```

### Relevante Felder

- `data.accessMode`
  `password` bei Basic Auth, `session` bei eingeloggter Session
- `data.accountKey`
  die aufgelöste Mailbox
- `data.folder`
  aufgelöster IMAP-Folder
- `data.message.uid`
  eindeutige UID innerhalb des Ordners
- `data.message.attachments`
  nur Metadaten, nicht der Dateiinhalt
- `data.message.textBody`
  Plaintext
- `data.message.htmlBody`
  HTML-Inhalt

## Session-API

### Login mit Cookie-Jar

```bash
curl -c cookies.txt \
  -X POST https://www.openlaw.cc/login \
  -d 'email=george%40openlaw.cc' \
  --data-urlencode 'password=<MAILBOX_PASSWORD>' \
  --data-urlencode 'callbackUrl=/mail'
```

Danach:

```bash
curl -b cookies.txt https://www.openlaw.cc/api/auth/session
```

### `GET /mail/api/accounts`

Liefert die zugänglichen Konten und die aktuell konfigurierten Limits.

Beispiel:

```bash
curl -b cookies.txt https://www.openlaw.cc/mail/api/accounts
```

Antwort:

```json
{
  "ok": true,
  "data": {
    "accounts": [
      {
        "email": "george@openlaw.cc",
        "fromName": "George · OpenLaw",
        "hasSignature": false,
        "inboxTotal": 98,
        "key": "george",
        "label": "George",
        "status": "ok",
        "unread": 49
      }
    ],
    "defaultAccountKey": "george",
    "limits": {
      "maxAttachments": 8,
      "maxJsonBodyBytes": 26214400,
      "maxTotalAttachmentBytes": 12582912
    }
  }
}
```

### `GET /mail/api/contacts`

Liefert das Kontaktverzeichnis für Compose-Autocomplete.

Antwortstruktur:

```json
{
  "ok": true,
  "data": {
    "contacts": [],
    "groups": []
  }
}
```

### `GET /mail/api/list`

Query-Parameter:

- `account` Pflicht in der Praxis
- `folder` Pflicht
- `limit` optional, Standard `50`, Maximum `100`

Beispiel:

```bash
curl -b cookies.txt \
  'https://www.openlaw.cc/mail/api/list?account=george&folder=inbox&limit=20'
```

Antwortfelder je Nachricht:

- `uid`
- `subject`
- `from`
- `to`
- `date`
- `seen`
- `size`

### `GET /mail/api/unread-count`

Ohne `account`:

- aggregierter Wert über alle zugänglichen Mailboxen
- zusätzlich `perAccount`

Mit `account`:

- nur der Zähler für diese Mailbox

Beispiele:

```bash
curl -b cookies.txt https://www.openlaw.cc/mail/api/unread-count
curl -b cookies.txt 'https://www.openlaw.cc/mail/api/unread-count?account=george'
```

### `GET /mail/api/message`

Query-Parameter:

- `account`
- `folder`
- `uid`

Beispiel:

```bash
curl -b cookies.txt \
  'https://www.openlaw.cc/mail/api/message?account=office&folder=inbox&uid=11'
```

Die Antwort entspricht dem `message`-Objekt aus `latest`, aber ohne äußeren `latest`-Wrapper.

### `GET /mail/api/attachment`

Query-Parameter:

- `account`
- `folder`
- `uid`
- `index`
- `inline` optional

Beispiel:

```bash
curl -L -b cookies.txt \
  'https://www.openlaw.cc/mail/api/attachment?account=office&folder=inbox&uid=11&index=0' \
  -o anhang.bin
```

Verhalten:

- Antwort ist Binärinhalt
- `Content-Type` entspricht dem Attachment
- `Content-Disposition` ist standardmäßig `attachment`
- mit `inline=1` wird `Content-Disposition: inline` gesetzt

## Schreiben von Nachrichten

Alle Schreiboperationen sind `POST`-Requests auf `/mail/api/*` mit JSON-Body und Session-Cookie.

### Attachment-Format

Attachments müssen Base64-codiert gesendet werden.

```json
[
  {
    "filename": "beispiel.txt",
    "contentType": "text/plain",
    "contentBase64": "SGFsbG8gd2VsdA=="
  }
]
```

Akzeptierte Feldnamen:

- `filename` oder `name`
- `contentBase64` oder `content`
- `contentType` oder `type`

### `POST /mail/api/send`

Minimaler Body:

```json
{
  "account": "george",
  "to": "office@openlaw.cc",
  "subject": "Test",
  "text": "Hallo"
}
```

Mögliche Felder:

- `account`
- `to`
- `cc`
- `bcc`
- `subject`
- `text`
- `html`
- `attachments`
- `priority`
- `useSignature`

`priority` unterstützt:

- `normal`
- `high`
- `hoch`
- `low`
- `niedrig`

Beispiel:

```bash
curl -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d @payload.json \
  https://www.openlaw.cc/mail/api/send
```

Antwort:

```json
{
  "ok": true,
  "data": {
    "accountKey": "george",
    "message": "Sent"
  }
}
```

### `POST /mail/api/reply`

Zusätzlich relevant:

- `inReplyTo` optional

Wenn `subject` nicht mit `Re:` beginnt, ergänzt der Server das Präfix automatisch.

Antwort:

```json
{
  "ok": true,
  "data": {
    "accountKey": "george",
    "message": "Reply sent"
  }
}
```

### `POST /mail/api/forward`

Zusätzlich notwendig:

- `forwardSource.account`
- `forwardSource.folder`
- `forwardSource.uid`
- `forwardSource.attachmentIndices` optional

Beispiel:

```json
{
  "account": "george",
  "to": "office@openlaw.cc",
  "subject": "Weiterleitung",
  "text": "Siehe unten.",
  "forwardSource": {
    "account": "george",
    "folder": "inbox",
    "uid": 108,
    "attachmentIndices": [0]
  }
}
```

Verhalten:

- vorhandene Anhänge der Quellnachricht können übernommen werden
- zusätzliche hochgeladene Attachments können gleichzeitig mitgesendet werden
- fehlendes `Fwd:`-Präfix wird automatisch ergänzt

### `POST /mail/api/mark-read`

Body:

```json
{
  "account": "george",
  "folder": "inbox",
  "uid": 108
}
```

Antwort:

```json
{
  "ok": true,
  "data": {
    "accountKey": "george",
    "uid": 108
  }
}
```

### `POST /mail/api/delete`

Body:

```json
{
  "account": "george",
  "folder": "inbox",
  "uid": 108
}
```

Verhalten:

- aus normalen Ordnern wird nach `Trash` verschoben
- aus `Trash` und `Drafts` wird direkt gelöscht

## Fehlercodes

Häufige Fehlercodes:

- `AUTH_REQUIRED`
- `MAIL_PASSWORD_REQUIRED`
- `MAIL_ACCOUNT_FORBIDDEN`
- `NO_MAIL_ACCESS`
- `NOT_CONFIGURED`
- `INVALID_ACCOUNT`
- `INVALID_FOLDER`
- `INVALID_PARAM`
- `INVALID_TO`
- `INVALID_SUBJECT`
- `INVALID_BODY`
- `INVALID_FORWARD_SOURCE`
- `INVALID_ATTACHMENTS`
- `ATTACHMENTS_TOO_LARGE`
- `INVALID_JSON`
- `BODY_TOO_LARGE`
- `NOT_FOUND`
- `IMAP_ERROR`
- `SMTP_ERROR`

Typische HTTP-Statuscodes:

- `200` Erfolg
- `302` Redirect auf Login bei Browser-Navigation ohne Session
- `400` ungültige Parameter oder ungültiger JSON-Body
- `401` keine Auth oder Basic-Auth-Challenge
- `403` keine Berechtigung für angeforderte Mailbox
- `404` Nachricht oder Attachment nicht gefunden
- `413` Request oder Attachments zu groß
- `500` IMAP-/SMTP-Fehler
- `503` Mail-Konfiguration fehlt

## Limits und Betriebsverhalten

Im aktuellen Code gibt es kein separates anwendungsspezifisches HTTP-Rate-Limit.
Relevant sind stattdessen diese technischen Grenzen:

- JSON-Request-Body: `25 MiB`
- maximale Anzahl Attachments: `8`
- maximale Gesamtsumme der Attachments: `12 MiB`
- IMAP-Connection-Timeout: `12 s`
- IMAP-Socket-Timeout: `20 s`
- Timeout für Mailbox-Statistiken: `8 s`
- IMAP-Connection-Cache-TTL: `45 s`

Für Polling-Clients gilt:

- nicht aggressiv pollen
- auf `401`, `403`, `404`, `413` und `5xx` sauber reagieren
- `latest` nicht als High-Frequency-Stream missbrauchen, da der Server dafür echte IMAP-Zugriffe ausführt

## Verifizierter Stand

Live geprüft am 1. April 2026:

- `GET /mail/office/inbox/latest` ohne Auth und mit `Accept: application/json` -> `401 MAIL_PASSWORD_REQUIRED`
- derselbe Pfad ohne Auth und mit `Accept: text/html` -> `302` auf `/login?...`
- `GET /mail/office/inbox/latest` mit Basic Auth -> `200`
- `GET /mail/george/sent/latest` -> `200`
- `GET /mail/george/drafts/latest` -> `404` bei leerem Folder
- `GET /mail/george/bogus/latest` -> `400 INVALID_FOLDER`
- `POST /login` -> `302` plus `openlaw.sid`
- `GET /mail/api/accounts` mit Session -> `200`
- `GET /mail/api/list` mit Session -> `200`
- `GET /mail/api/message` mit Session -> `200`
- `POST /mail/api/send` mit Session -> `200`
- Zustellung einer per API gesendeten Testmail an `office@openlaw.cc` wurde serverseitig bestätigt
