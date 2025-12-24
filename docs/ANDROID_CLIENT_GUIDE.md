# Guía de Despliegue de WebUI en Android (Termux)

Esta guía te permitirá ejecutar la interfaz web de COLEGA en una tablet o teléfono Android utilizando Termux. De esta forma, puedes usar tu dispositivo móvil como un panel de control dedicado, mientras el núcleo del sistema (NeoCore) se ejecuta en tu PC o Raspberry Pi.

## Prerrequisitos

1.  **Termux**: Debes tener instalado Termux en tu dispositivo Android. Puedes descargarlo desde [F-Droid](https://f-droid.org/en/packages/com.termux/) (recomendado) o Google Play Store (versión antigua, no recomendada).
2.  **Conexión de Red**: Tu dispositivo Android y el servidor NeoCore deben estar en la misma red WiFi.

## Paso 1: Preparación del Entorno en Termux

Abre la aplicación Termux y ejecuta los siguientes comandos uno por uno para actualizar el sistema e instalar las herramientas necesarias:

```bash
# 1. Actualizar repositorios y paquetes
pkg update && pkg upgrade -y

# 2. Instalar Python y Git
pkg install python git -y

# 3. (Opcional) Instalar nano si quieres editar archivos fácilmente
pkg install nano -y
```

## Paso 2: Obtener el Código

Clona el repositorio de COLEGA en tu dispositivo:

```bash
git clone https://github.com/jrodriiguezg/COLEGA.git
cd COLEGA
```

## Paso 3: Instalación de Dependencias del Cliente

El cliente web es muy ligero y no requiere todas las dependencias del servidor. Solo necesitamos instalar lo siguiente:

```bash
pip install flask requests flask-wtf
```

## Paso 4: Conexión con el Servidor

Necesitas saber la dirección IP de tu ordenador donde se ejecuta NeoCore (ej. `192.168.1.50`).

Antes de arrancar, debemos decirle al cliente dónde encontrar al servidor:

```bash
# Reemplaza la IP con la de tu servidor real
export NEO_API_URL="http://192.168.1.50:5000"
```

> **Nota:** Si cierras Termux, perderás esta configuración. Mira la sección "Automatización" para hacerlo permanente.

## Paso 5: Ejecutar el Cliente

Inicia la interfaz web:

```bash
python web_client/app.py
```

Verás un mensaje como este:
```
🚀 Neo Headless Client starting...
🔗 Connected to NeoCore at: http://192.168.1.50:5000
🌍 Web Interface at: http://0.0.0.0:8000
```

Ahora, abre tu navegador favorito en Android (Chrome, Firefox) y ve a:
`http://localhost:8000`

¡Listo! Deberías ver la interfaz de control de COLEGA.

---

## Automatización (Script de Inicio Rápido)

Para no tener que escribir los comandos cada vez, puedes crear un pequeño script de lanzamiento en tu carpeta home.

1.  Asegúrate de estar en el inicio:
    ```bash
    cd ~
    ```

2.  Crea un archivo llamado `iniciar_colega.sh`:
    ```bash
    nano iniciar_colega.sh
    ```

3.  Pega el siguiente contenido (ajustando la IP):
    ```bash
    #!/bin/bash
    
    # CAMBIA ESTO POR LA IP DE TU PC
    SERVER_IP="192.168.1.50"
    
    echo "🔵 Conectando a COLEGA en $SERVER_IP..."
    
    cd ~/COLEGA
    export NEO_API_URL="http://$SERVER_IP:5000"
    python web_client/app.py
    ```

4.  Guarda (Ctrl+O, Enter) y Sal (Ctrl+X).

5.  Dale permisos de ejecución:
    ```bash
    chmod +x iniciar_colega.sh
    ```

6.  Ahora, cada vez que abras Termux, solo escribe:
    ```bash
    ./iniciar_colega.sh
    ```
