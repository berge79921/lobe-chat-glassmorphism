#!/bin/bash

# Theme-Setup Skript für LobeChat Glassmorphism
# =============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}→ Theme-Setup wird ausgeführt...${NC}"

# Pfad zum CSS
CSS_PATH="$(pwd)/src/styles/glassmorphism-theme.css"

if [ ! -f "$CSS_PATH" ]; then
    echo -e "${RED}✗ CSS-Datei nicht gefunden: $CSS_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✓ CSS-Datei gefunden${NC}"

# Erstelle custom-css Verzeichnis im Docker-Ordner
mkdir -p docker/custom-css

# Kopiere CSS-Datei
cp "$CSS_PATH" docker/custom-css/custom.css

echo -e "${GREEN}✓ CSS in Docker-Verzeichnis kopiert${NC}"

# Modifiziere docker-compose.yml um das CSS zu mounten
DOCKER_COMPOSE="docker/docker-compose.yml"

if grep -q "custom.css" "$DOCKER_COMPOSE"; then
    echo -e "${YELLOW}→ CSS-Mount bereits in docker-compose.yml vorhanden${NC}"
else
    echo -e "${BLUE}→ Füge CSS-Mount zu docker-compose.yml hinzu...${NC}"
    
    # Backup erstellen
    cp "$DOCKER_COMPOSE" "$DOCKER_COMPOSE.backup"
    
    # Füge Volume-Mount hinzu (macOS sed)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' '/restart: always/a\      volumes:\n        - ./custom-css/custom.css:/app/public/custom.css:ro' "$DOCKER_COMPOSE"
    else
        sed -i '/restart: always/a\      volumes:\n        - ./custom-css/custom.css:/app/public/custom.css:ro' "$DOCKER_COMPOSE"
    fi
    
    echo -e "${GREEN}✓ CSS-Mount hinzugefügt${NC}"
fi

echo ""
echo -e "${GREEN}✓ Theme-Setup abgeschlossen!${NC}"
echo ""
echo "Das Custom CSS wird automatisch in den LobeChat-Container gemountet."
echo "Starte die Container mit: ./start.sh"
