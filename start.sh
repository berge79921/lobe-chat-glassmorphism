#!/bin/bash

# LobeChat Glassmorphism - Start-Skript
# ======================================

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}     ${GREEN}LobeChat Glassmorphism - Setup${NC}                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}     Design: Kostenrechner-Style                             ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Prüfe ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker läuft nicht!${NC}"
    echo "Bitte starte Docker Desktop oder Docker Daemon."
    exit 1
fi

echo -e "${GREEN}✓ Docker läuft${NC}"

# Prüfe Docker Compose
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker Compose nicht gefunden!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker Compose verfügbar${NC}"

# Erstelle .env falls nicht vorhanden
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}→ Erstelle .env aus Vorlage...${NC}"
    cp .env.example .env
    
    # Generiere zufälligen Secret
    if command -v openssl >/dev/null 2>&1; then
        SECRET=$(openssl rand -base64 32)
        # Ersetze Platzhalter (macOS und Linux kompatibel)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/your_random_secret_here/$SECRET/g" .env
        else
            sed -i "s/your_random_secret_here/$SECRET/g" .env
        fi
        echo -e "${GREEN}✓ NEXT_AUTH_SECRET generiert${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}⚠ Bitte passe die .env Datei an:${NC}"
    echo "   1. OPENROUTER_API_KEY setzen (von https://openrouter.ai/keys)"
    echo ""
    read -p "Drücke Enter um fortzufahren oder Ctrl+C zum Abbrechen..."
fi

# Prüfe Vision/S3 Konfiguration fuer stabilen Bild-Upload mit OpenRouter
echo ""
echo -e "${BLUE}→ Prüfe Vision/S3 Konfiguration...${NC}"
DOCKER_ENV_FILE="docker/.env"
VISION_WARNINGS=0

if [ -f "$DOCKER_ENV_FILE" ]; then
    get_env_value() {
        local key="$1"
        grep -E "^${key}=" "$DOCKER_ENV_FILE" | tail -n 1 | cut -d '=' -f2-
    }

    S3_PUBLIC_DOMAIN_VAL=$(get_env_value "S3_PUBLIC_DOMAIN")
    S3_SET_ACL_VAL=$(get_env_value "S3_SET_ACL")
    BASE64_VAL=$(get_env_value "LLM_VISION_IMAGE_USE_BASE64")
    SSRF_ALLOW_PRIVATE_VAL=$(get_env_value "SSRF_ALLOW_PRIVATE_IP_ADDRESS")
    SSRF_ALLOW_LIST_VAL=$(get_env_value "SSRF_ALLOW_IP_ADDRESS_LIST")

    if [[ "$S3_PUBLIC_DOMAIN_VAL" == *"localhost"* || "$S3_PUBLIC_DOMAIN_VAL" == *"127.0.0.1"* ]]; then
        echo -e "${YELLOW}  ⚠ S3_PUBLIC_DOMAIN zeigt auf localhost (OpenRouter kann das nicht erreichen).${NC}"
        VISION_WARNINGS=$((VISION_WARNINGS + 1))
    fi

    if [ "$S3_SET_ACL_VAL" != "0" ]; then
        echo -e "${YELLOW}  ⚠ S3_SET_ACL ist nicht auf 0 (empfohlen: private Objekte + presigned URLs).${NC}"
        VISION_WARNINGS=$((VISION_WARNINGS + 1))
    fi

    if [ "$BASE64_VAL" != "1" ]; then
        echo -e "${YELLOW}  ⚠ LLM_VISION_IMAGE_USE_BASE64 ist nicht aktiv (empfohlen: 1).${NC}"
        VISION_WARNINGS=$((VISION_WARNINGS + 1))
    fi

    if [ "$SSRF_ALLOW_PRIVATE_VAL" = "1" ]; then
        echo -e "${YELLOW}  ⚠ SSRF_ALLOW_PRIVATE_IP_ADDRESS=1 deaktiviert SSRF-Schutz fuer private Netze.${NC}"
        VISION_WARNINGS=$((VISION_WARNINGS + 1))
    fi

    if [ -z "$SSRF_ALLOW_LIST_VAL" ]; then
        echo -e "${YELLOW}  ⚠ SSRF_ALLOW_IP_ADDRESS_LIST ist leer (MinIO-IP sollte explizit gesetzt sein).${NC}"
        VISION_WARNINGS=$((VISION_WARNINGS + 1))
    fi

    if [ "$VISION_WARNINGS" -eq 0 ]; then
        echo -e "${GREEN}  ✓ Vision/S3 Konfiguration sieht konsistent aus${NC}"
    else
        echo -e "${YELLOW}  ⚠ Bitte docker/.env fuer produktionsfaehige Bildverarbeitung pruefen.${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ docker/.env nicht gefunden, Vision/S3 Check wurde uebersprungen.${NC}"
fi

# Prüfe ob Ports belegt sind
echo ""
echo -e "${BLUE}→ Prüfe Ports...${NC}"
PORTS=("3210" "3001" "3002" "9000" "9001")
PORTS_OK=true

for PORT in "${PORTS[@]}"; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}  ✗ Port $PORT ist belegt!${NC}"
        PORTS_OK=false
    else
        echo -e "${GREEN}  ✓ Port $PORT frei${NC}"
    fi
done

if [ "$PORTS_OK" = false ]; then
    echo ""
    echo -e "${RED}Fehler: Einige Ports sind bereits belegt.${NC}"
    echo "Bitte stoppe die Prozesse oder ändere die Ports in docker/docker-compose.yml"
    exit 1
fi

# Erstelle Verzeichnisse
echo ""
echo -e "${BLUE}→ Erstelle Verzeichnisse...${NC}"
mkdir -p docker/data docker/s3_data
mkdir -p uploads

echo -e "${GREEN}✓ Verzeichnisse erstellt${NC}"

# Starte Container
echo ""
echo -e "${BLUE}→ Starte LobeChat mit Glassmorphism-Design...${NC}"
cd docker

# Pull latest images
docker compose pull

# Starte im Hintergrund
docker compose up -d

echo ""
echo -e "${GREEN}✓ Container gestartet!${NC}"
echo ""

# Warte auf Datenbank
echo -e "${BLUE}→ Warte auf Datenbank...${NC}"
sleep 5

# Prüfe Status
echo ""
echo -e "${BLUE}→ Prüfe Status...${NC}"
docker compose ps

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}                    ${GREEN}✓ Installation erfolgreich!${NC}             ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BLUE}LobeChat UI:${NC}     http://localhost:3210                    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BLUE}Logto Admin:${NC}     http://localhost:3002                    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BLUE}MinIO Console:${NC}   http://localhost:9001                    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${YELLOW}Nächste Schritte:${NC}                                        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  1. Logto Admin öffnen und ersten Benutzer erstellen       ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  2. Application "LobeChat" erstellen                       ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  3. Client ID/Secret in .env eintragen                     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  4. Container neustarten: docker compose restart lobe      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Zeige Logs
echo -e "${BLUE}→ Zeige Logs (Ctrl+C zum Beenden der Logs)...${NC}"
echo ""
docker compose logs -f lobe --tail=50
