#!/bin/bash

# Detect VENV
if [ -d "venv_distrobox" ]; then
    VENV_PATH="venv_distrobox"
    echo "Usando entorno Distrobox ($VENV_PATH)"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
    echo "Usando entorno Standard ($VENV_PATH)"
else
    echo "ERROR: No se encontró entorno virtual (venv o venv_distrobox)."
    echo "Ejecuta ./setup_distrobox.sh (Fedora) o ./install.sh (Debian/Ubuntu)."
    exit 1
fi

source $VENV_PATH/bin/activate

# Check for updates or other pre-start checks could go here

# Fix Timezone in Distrobox
if [ -f /etc/timezone ]; then
    export TZ=$(cat /etc/timezone)
fi

# Fix Jack Segfaults
export JACK_NO_START_SERVER=1

# Start Mosquitto if not running and installed
if ! pgrep -x "mosquitto" > /dev/null; then
    if command -v mosquitto > /dev/null; then
        echo "Iniciando Broker MQTT..."
        mosquitto -d
    fi
fi

# Start Application
python NeoCore.py
