#!/bin/bash

# Definition of colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Configuración de Entorno Distrobox para NeoCore ===${NC}"

# 1. Check Distrobox Installation
if ! command -v distrobox &> /dev/null; then
    echo -e "${YELLOW}Distrobox no detectado. Instalando...${NC}"
    if command -v dnf &> /dev/null; then
        sudo dnf install -y distrobox podman
    elif command -v apt &> /dev/null; then
        sudo apt install -y distrobox podman
    else
        echo -e "${RED}No se pudo instalar distrobox automáticamente. Por favor instálalo manualmente.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Distrobox ya está instalado.${NC}"
fi

CONTAINER_NAME="neocore-box"
IMAGE="debian:12" # Stable Bookworm

# 2. Check/Create Container
echo -e "${YELLOW}Verificando contenedor '${CONTAINER_NAME}'...${NC}"
if distrobox list | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}El contenedor existe.${NC}"
else
    echo -e "${YELLOW}Creando contenedor '${CONTAINER_NAME}' con imagen '${IMAGE}'...${NC}"
    distrobox create -n "$CONTAINER_NAME" -i "$IMAGE" -Y
fi

# 3. Enter and Setup
echo -e "${GREEN}Instalando dependencias dentro de Distrobox...${NC}"

# Script to run INSIDE the container
SETUP_SCRIPT="
set -e
echo 'Actualizando repositorios...'
sudo apt-get update && sudo apt-get install -y \
    python3 python3-pip python3-venv \
    git build-essential cmake swig libopenblas-dev wget unzip \
    libvlc-dev vlc \
    portaudio19-dev libasound2-dev \
    libgl1 libglib2.0-0 \
    ffmpeg

echo 'Creando entorno virtual (venv_distrobox)...'
cd \"$PWD\"
if [ ! -d \"venv_distrobox\" ]; then
    python3 -m venv venv_distrobox
fi

source venv_distrobox/bin/activate

echo 'Instalando pip requirements...'
pip install --upgrade pip wheel setuptools
# Fix fann2 separately if needed, but lets try direct install first
if grep -q 'fann2' requirements.txt; then
    # Clone and build fann first if missing system lib
    if [ ! -f /usr/lib/libfann.so ] && [ ! -f /usr/local/lib/libfann.so ]; then
       echo 'Compilando libfann C...'
       if [ ! -d \"FANN\" ]; then
           git clone https://github.com/libfann/fann.git FANN
       fi
       cd FANN
       cmake .
       sudo make install
       cd ..
       sudo ldconfig
    fi
fi

pip install -r requirements.txt

echo 'Instalación Completada en Distrobox.'
"

# Execute setup inside distrobox
distrobox enter "$CONTAINER_NAME" -- bash -c "$SETUP_SCRIPT"

# 4. Create Launcher Shortcut
LAUNCHER_SCRIPT="run_neocore_distrobox.sh"
echo "#!/bin/bash" > "$LAUNCHER_SCRIPT"
echo "echo 'Iniciando NeoCore en Distrobox...'" >> "$LAUNCHER_SCRIPT"
echo "distrobox enter $CONTAINER_NAME -- bash -c 'cd \"$PWD\" && source venv_distrobox/bin/activate && ./start.sh'" >> "$LAUNCHER_SCRIPT"
chmod +x "$LAUNCHER_SCRIPT"

echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}¡Configuración finalizada!${NC}"
echo -e "Para iniciar la aplicación, ejecuta:"
echo -e "${YELLOW}./$LAUNCHER_SCRIPT${NC}"
echo -e "${GREEN}==============================================${NC}"
