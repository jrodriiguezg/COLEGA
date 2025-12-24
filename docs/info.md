# Neo Nano - Asistente de Administración de Sistemas

## 📖 Descripción General
**Neo Nano** ha evolucionado. Lo que comenzó como un asistente para el cuidado de mayores se ha transformado en una potente herramienta **Headless** (sin monitor) para **Administradores de Sistemas**.

Diseñado para ejecutarse en dispositivos ligeros como la **Raspberry Pi** o en estaciones de trabajo Linux (**Fedora/Debian**), Neo actúa como tu compañero de laboratorio. Puedes pedirle el estado del servidor por voz mientras trabajas en hardware, o gestionar servicios y terminales desde su panel web profesional desde cualquier dispositivo de la red.

## 🚀 Características Principales

### 🗣️ Control por Voz (Offline)
*   **Privacidad Total**: Todo el reconocimiento de voz se realiza en local usando **Vosk**. Nada se envía a la nube.
*   **Cerebro (Brain)**: Aprende alias y datos ("Aprende que X es Y").
*   **Seguridad de Red**: Escanea la red local, hace pings y consultas WHOIS ("Escanea mi red", "Ping a google").
*   **Monitorización**: "Neo, ¿cómo está la CPU?", "Neo, reinicia la red".
*   **Personalidad Tech**: Respuestas ajustadas al contexto técnico.

### 💻 Consola de Administración Web (Pro)
Accede a `http://<IP-DEL-DISPOSITIVO>:5000` para un control total:
*   **Dashboard**: Gráficas y métricas en tiempo real (CPU, RAM, Disco, Temperatura).
*   **Gestor de Servicios**: Arranca, para y reinicia servicios (Docker, SSH, Nginx, etc.) con un clic.
*   **Terminal Web**: Una consola completa en tu navegador. Soporta `cd`, historial de comandos y colores. Ideal para arreglos rápidos desde el móvil.
*   **Red**: Herramientas de diagnóstico, visualización de IPs y test de conectividad.
*   **Acciones Rápidas**: Scripts predefinidos para actualizar el sistema, limpiar caché o hacer backups.
*   **Logs en Vivo**: Depura problemas viendo la salida de la aplicación en tiempo real.

### 🛠️ Arquitectura Robusta
*   **Headless**: Diseñado para funcionar como un servicio `systemd` en segundo plano.
*   **Multi-Hilo**: La voz, la web y las tareas de fondo corren en paralelo sin bloquearse.
*   **Configurable**: Cambia el usuario, contraseña y palabra de activación desde la propia web.

## 📂 Estructura del Proyecto

```
Neo_nano/
├── NeoCore.py       # Cerebro de la aplicación (Punto de entrada)
├── install.sh              # Script de instalación automática
├── config.json             # Configuración (Credenciales, Wake Word)
├── modules/
│   ├── sysadmin.py         # Módulo de interacción con el SO
│   ├── web_admin.py        # Servidor Web Flask
│   ├── speaker.py          # Motor de Texto a Voz (TTS)
│   └── logger.py           # Sistema de logs centralizado
├── templates/              # Interfaz Web (HTML5 + Jinja2)
├── static/                 # Estilos CSS (Dark Mode Profesional)
├── jsons/                  # Base de conocimientos y comandos
└── logs/                   # Registros de actividad
```

## 🔧 Instalación

El sistema detecta automáticamente si estás en Debian (Raspberry Pi OS) o Fedora y usa el gestor de paquetes adecuado (`apt` o `dnf`).

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-usuario/Neo_nano.git
    cd Neo_nano
    ```

2.  **Ejecutar instalador**:
    ```bash
    chmod +x install.sh
    ./install.sh
    ```
    *Esto instalará dependencias (Python, Vosk, Piper, Flask) y configurará el servicio systemd.*

3.  **Verificar**:
    El servicio debería arrancar automáticamente. Puedes ver el estado con:
    ```bash
    systemctl status neo.service
    ```

## 💡 Uso

### Vía Voz
1.  Asegúrate de tener un micrófono conectado.
2.  Di **"Neo"** (o tu palabra clave configurada).
3.  Espera el sonido de escucha o di el comando directamente: *"Neo, dame un reporte de estado"*.

### Vía Web
1.  Abre un navegador en tu PC o Móvil.
2.  Ve a `http://<IP-DE-LA-PI>:5000`.
3.  Loguéate (Por defecto: Usuario `user`, Contraseña `user`).
4.  ¡Toma el control!

## �️ Seguridad
*   La terminal web y las acciones de sistema ejecutan comandos con privilegios.
*   Se recomienda cambiar la contraseña por defecto inmediatamente desde el menú **Settings**.
*   El servidor web escucha en `0.0.0.0` (toda la red local). Asegúrate de que tu red es segura.

---
*Desarrollado con ❤️ y Python.*
