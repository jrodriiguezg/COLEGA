#!/bin/bash

# install.sh
# Script de instalación para el proyecto OpenKompai.
# Este script automatiza la instalación de dependencias del sistema,
# librerías de Python y la configuración del entorno para el autoarranque.

# Detiene el script si algún comando falla
set -e

echo "========================================="
echo "===   Instalador de OpenKompai nano   ==="
echo "========================================="
echo "Este script instalará todo lo necesario para ejecutar la aplicación."
echo "Se requerirá tu contraseña para instalar paquetes del sistema (sudo)."
echo ""

# --- 1. INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA ---
echo "[PASO 1/6] Instalando dependencias del sistema con APT..."
sudo apt-get update
sudo apt-get install -y \
    git \
    python3-pip \
    python3-tk \
    vlc \
    libvlc-dev \
    portaudio19-dev \
    python3-pyaudio \
    flac \
    alsa-utils \
    unzip \
    libatlas-base-dev \
    libgl1-mesa-glx \
    unclutter # Utilidad para ocultar el cursor

echo "Dependencias del sistema instaladas correctamente."
echo ""

# --- 2. DESCARGA DEL CÓDIGO FUENTE ---
echo "[PASO 2/6] Descargando el código fuente desde GitHub..."
if [ -d "OpenKompai_nano" ]; then
    echo "El directorio 'OpenKompai_nano' ya existe. Omitiendo la descarga."
else
    git clone https://github.com/jrodriiguezg/OpenKompai_nano.git
fi
cd OpenKompai_nano
echo "Código fuente descargado en el directorio 'OpenKompai_nano'."
echo ""

# --- 3. INSTALACIÓN DE LIBRERÍAS DE PYTHON ---
echo "[PASO 3/6] Instalando las librerías de Python con PIP..."
# Se instalan las librerías del requirements.txt y las adicionales detectadas en el código.
pip3 install -r requirements.txt --break-system-packages
echo "Librerías de Python instaladas correctamente."
echo ""

# --- 4. DESCARGA Y CONFIGURACIÓN DEL MODELO DE VOZ (VOSK) ---
echo "[PASO 4/6] Descargando y configurando el modelo de voz en español (Vosk)..."
if [ -d "vosk-models/es" ]; then
    echo "El modelo de Vosk ya parece estar instalado. Omitiendo."
else
    MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
    MODEL_ZIP="vosk-model-small-es-0.42.zip"
    MODEL_DIR="vosk-model-small-es-0.42"

    echo "Descargando modelo desde $MODEL_URL..."
    wget -q --show-progress "$MODEL_URL"

    echo "Descomprimiendo modelo..."
    unzip -q "$MODEL_ZIP"

    # La aplicación espera el modelo en 'vosk-models/es'
    mkdir -p vosk-models
    mv "$MODEL_DIR" vosk-models/es
    rm "$MODEL_ZIP"

    echo "Modelo de voz configurado correctamente."
fi
echo ""

# --- 5. VERIFICACIÓN Y CONFIGURACIÓN DEL ENTORNO GRÁFICO ---
echo "[PASO 5/6] Configurando el autoarranque de la aplicación..."

# Definimos la ruta de la aplicación y el directorio de autostart
# Usamos PWD para obtener la ruta absoluta del directorio actual (OpenKompai_nano)
APP_PATH="$(pwd)/OpenKompaiTK.py"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/openkompai.desktop"

# Comprueba si la variable de entorno DISPLAY está vacía, lo que indica un entorno de texto.
if [ -z "$DISPLAY" ]; then
    echo "-> Entorno de solo texto detectado. Se configurará un entorno gráfico mínimo (Openbox)."

    echo "Instalando Openbox (gestor de ventanas ligero)..."
    sudo apt-get install -y openbox

    echo "Creando el fichero de configuración ~/.xinitrc..."
    echo "exec openbox-session" > ~/.xinitrc

    echo "Creando script de autoarranque para Openbox..."
    mkdir -p ~/.config/openbox

    cat <<EOT > ~/.config/openbox/autostart
# Desactivar el salvapantallas y el apagado de pantalla por inactividad
xset s off -dpms
unclutter -idle 5 &
while true; do
  python3 $APP_PATH
  sleep 5
done &
EOT
    echo "La aplicación OpenKompai se ha configurado para iniciarse automáticamente."

else
    echo "-> Entorno gráfico detectado. Se creará un lanzador de autoarranque estándar."
    mkdir -p "$AUTOSTART_DIR"
    echo "Creando fichero de autoarranque en $DESKTOP_FILE..."
    cat <<EOT > "$DESKTOP_FILE"
[Desktop Entry]
Name=OpenKompai
Comment=Inicia la aplicación de asistencia OpenKompai
Exec=python3 $APP_PATH
Type=Application
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
EOT
    echo "La aplicación OpenKompai se ha configurado para iniciarse automáticamente en el próximo inicio de sesión."
fi
echo ""

# --- 6. MENSAJES FINALES Y PASOS MANUALES ---
echo "[PASO 6/6] Finalizando la instalación y mostrando avisos importantes..."
echo ""

echo "---------------------- ¡AVISO IMPORTANTE: CÁMARA ESP32! ----------------------"
echo "Si vas a usar una cámara ESP32, recuerda configurar su firmware con los"
echo "datos de tu red Wi-Fi y después, modificar el fichero 'OpenKompaiTK.py'"
echo "para establecer la dirección IP correcta de la cámara en la variable"
echo "'ESP32_STREAM_URL'."
echo "-----------------------------------------------------------------------------"
echo ""

echo "-------------------------- ¡ATENCIÓN: MOTOR DE VOZ! --------------------------"
echo "El motor de Texto a Voz (Piper) requiere una instalación manual."
echo "La aplicación está configurada para buscarlo en:"
echo "  - Ejecutable: piper/install/piper"
echo "  - Modelo de voz: piper/voices/es_ES/es_ES-davefx-medium.onnx"
echo "Por favor, asegúrate de instalar Piper y colocar los ficheros en esas rutas,"
echo "o modifica las rutas en el fichero 'OpenKompaiTK.py' para que coincidan"
echo "con tu instalación."
echo "----------------------------------------------------------------------------"
echo ""

echo "🎉 ¡Instalación completada!"
echo "Para que todos los cambios surtan efecto, es necesario reiniciar el sistema."
read -p "Pulsa [Enter] para finalizar."

# Mensaje final para el usuario
echo "Por favor, reinicia tu sistema con 'sudo reboot'."
