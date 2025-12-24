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

# Start Application
python NeoCore.py
