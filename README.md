# COLEGA

[🇺🇸 English](#english) | [🇪🇸 Español](#español)

---

<a name="english"></a>
## English

**C.O.L.E.G.A.** (Language Copilot for Group and Administration Environments)

> Formerly known as **OpenKompai Nano**

COLEGA is a proactive and modular personal assistant designed to run locally on modest hardware. It combines the efficiency of a rule-based system for system control and home automation with the intelligence of a local LLM (**Gemma 2B**) for natural conversations and reasoning.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)

### 🚀 Key Features

#### 🧠 Hybrid Intelligence
*   **Local LLM**: Integration with **Gemma 2B** (4-bit) for fluid conversations, personality, and complex reasoning without cloud dependency.
*   **Memory (Brain)**: Long-term memory system and alias learning for commands.
*   **RAG (Retrieval-Augmented Generation)**: Ability to query documents and learned data to enrich responses.

#### 🗣️ Natural Interaction
*   **Voice**: Offline voice recognition with **Vosk** (fast) or **Whisper** (accurate).
*   **Speech**: Natural and emotive speech synthesis with **Piper TTS**.
*   **Visual Interface**: Reactive "Face" (Web UI) showing states (listening, thinking, speaking) and notifications.

#### 🛠️ System & Network Administration
*   **SysAdmin**: Service control, system updates, resource monitoring (CPU/RAM/Disk), and power management.
*   **SSH Manager**: SSH connection manager to administer remote servers via voice.
*   **Network Tools**: Network scanning (Nmap), Ping, Whois, and public IP detection.
*   **File Manager**: Search and reading of files on the local system.

#### 🏠 Home Automation & Organization
*   **Organizer**: Management of calendars, alarms, timers, and reminders.
*   **Media**: Online radio playback and **Cast** capability (send video/audio) to compatible devices (DLNA/Chromecast).
*   **Network Bros**: Inter-agent communication protocol (MQTT) for alerts and distributed telemetry.
*   **Bluetooth**: Support for communication and control via Bluetooth.

### 🏗️ Architecture

The core (`NeoCore.py`) orchestrates several independent modules:

*   **Managers**: `VoiceManager`, `IntentManager`, `AIEngine`, `MQTTManager`, `SSHManager`, etc.
*   **Skills**: Specific functional modules (`skills/system`, `skills/network`, `skills/media`, etc.).
*   **Web Admin**: Web control panel for management and visualization.

### 📋 Requirements

*   **Operating System**: Linux (Debian, Ubuntu).
*   **Hardware**:
    *   CPU: Processor with AVX2 support.
    *   RAM: Minimum 4GB (8GB recommended for Gemma 2B).
    *   Storage: 16GB+ (SSD).
*   **Audio**: Microphone and Speakers connected.

### 🔧 Installation

For detailed instructions on all installation modes (Headless, Client, etc.), please refer to the [Installation Guide](public_docs/install.md).

**Quick Start:**

```bash
# Clone the repository
git clone https://github.com/jrodriiguezg/NEO.git
cd NEO

# Run the unified installer
./install_wizard.sh
```

The wizard will guide you through:
1.  **Main Node (Full)**: Complete installation (Core + Local Web) inside a container.
2.  **Main Node (Headless)**: Core only, optimized for servers/RPi Zero.
3.  **Remote Web Client**: Lightweight interface to control a Main Node from another PC.

### ⚙️ Configuration

The main configuration is found in `config/config.json`. You can modify it manually or via the **Web Admin**.

*   **Wake Word**: Activation word (default "tio", "colega", etc.).
*   **Paths**: Scanning directories, models, etc.
*   **Preferences**: Language, TTS voice, listening sensitivity.

### 🖥️ Usage

Once installed, COLEGA will run as a background service.

*   **Web Interface**: Access `http://localhost:5000/face` (or the device IP) to see the assistant's "face".
*   **Logs**: You can view real-time activity with:
    ```bash
    journalctl --user -u neo.service -f
    ```
*   **Voice Commands**: Simply say the wake word and your command (e.g., *"Colega, what time is it?", "Colega, play the radio", "Colega, scan the network"*).

### 🤝 Contribution

Contributions are welcome! Please open an *issue* or submit a *pull request* for improvements or corrections.

### 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the `LICENSE` file for more details.

---

<a name="español"></a>
## Español

**C.O.L.E.G.A.** (COpiloto de Lenguaje para Entornos de Grupo y Administración)

> Anteriormente conocido como **OpenKompai Nano**

COLEGA es un asistente personal proactivo y modular diseñado para ejecutarse localmente en hardware modesto. Combina la eficiencia de un sistema basado en reglas para el control del sistema y domótica, con la inteligencia de un LLM local (**Gemma 2B**) para conversaciones naturales y razonamiento.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)

### 🚀 Características Principales

#### 🧠 Inteligencia Híbrida
*   **LLM Local**: Integración con **Gemma 2B** (4-bit) para conversaciones fluidas, personalidad y razonamiento complejo sin depender de la nube.
*   **Memoria (Brain)**: Sistema de memoria a largo plazo y aprendizaje de alias para comandos.
*   **RAG (Retrieval-Augmented Generation)**: Capacidad de consultar documentos y datos aprendidos para enriquecer las respuestas.

#### 🗣️ Interacción Natural
*   **Voz**: Reconocimiento de voz offline con **Vosk** (rápido) o **Whisper** (preciso).
*   **Habla**: Síntesis de voz natural y emotiva con **Piper TTS**.
*   **Interfaz Visual**: "Cara" reactiva (Web UI) que muestra estados (escuchando, pensando, hablando) y notificaciones.

#### 🛠️ Administración de Sistemas & Redes
*   **SysAdmin**: Control de servicios, actualizaciones del sistema, monitoreo de recursos (CPU/RAM/Disco) y gestión de energía.
*   **SSH Manager**: Gestor de conexiones SSH para administrar servidores remotos mediante voz.
*   **Network Tools**: Escaneo de red (Nmap), Ping, Whois, y detección de IP pública.
*   **File Manager**: Búsqueda y lectura de archivos en el sistema local.

#### 🏠 Domótica & Organización
*   **Organizador**: Gestión de calendarios, alarmas, temporizadores y recordatorios.
*   **Media**: Reproducción de radio online y capacidad de **Cast** (enviar video/audio) a dispositivos compatibles (DLNA/Chromecast).
*   **Network Bros**: Protocolo de comunicación entre agentes (MQTT) para alertas y telemetría distribuida.
*   **Bluetooth**: Soporte para comunicación y control via Bluetooth.

### 🏗️ Arquitectura

El núcleo (`NeoCore.py`) orquesta varios módulos independientes:

*   **Managers**: `VoiceManager`, `IntentManager`, `AIEngine`, `MQTTManager`, `SSHManager`, etc.
*   **Skills**: Módulos funcionales específicos (`skills/system`, `skills/network`, `skills/media`, etc.).
*   **Web Admin**: Panel de control web para gestión y visualización.

### 📋 Requisitos

*   **Sistema Operativo**: Linux (Debian, Ubuntu).
*   **Hardware**:
    *   CPU: Procesador con soporte para AVX2. 
    *   RAM: Mínimo 4GB (8GB recomendado para Gemma 2B).
    *   Almacenamiento: 16GB+ (SSD).
*   **Audio**: Micrófono y Altavoces conectados.

### 🔧 Instalación

Para instrucciones detalladas sobre todos los modos de instalación (Headless, Cliente, etc.), consulta la [Guía de Instalación](public_docs/install.md).

**Inicio Rápido:**

```bash
# Clona el repositorio
git clone https://github.com/jrodriiguezg/NEO.git
cd NEO

# Ejecuta el instalador unificado
./install_wizard.sh
```

El asistente te guiará a través de:
1.  **Nodo Principal (Completo)**: Instalación completa (Núcleo + Web Local) en contenedor.
2.  **Nodo Principal (Headless)**: Solo núcleo, optimizado para servidores/RPi Zero.
3.  **Cliente Web Remoto**: Interfaz ligera para controlar un Nodo Principal desde otro PC.

### ⚙️ Configuración

La configuración principal se encuentra en `config/config.json`. Puedes modificarla manualmente o a través del **Web Admin**.

*   **Wake Word**: Palabra de activación (por defecto "tio", "colega", etc.).
*   **Rutas**: Directorios de escaneo, modelos, etc.
*   **Preferencias**: Idioma, voz TTS, sensibilidad de escucha.

### 🖥️ Uso

Una vez instalado, COLEGA funcionará como un servicio en segundo plano.

*   **Interfaz Web**: Accede a `http://localhost:5000/face` (o la IP del dispositivo) para ver la "cara" del asistente. 
*   **Logs**: Puedes ver la actividad en tiempo real con:
    ```bash
    journalctl --user -u neo.service -f
    ```
*   **Comandos de Voz**: Simplemente di la palabra de activación y tu comando (ej: *"Colega, ¿qué hora es?", "Colega, pon la radio", "Colega, escanea la red"*).

### 🤝 Contribución

¡Las contribuciones son bienvenidas! Por favor, abre un *issue* o envía un *pull request* para mejoras o correcciones.

### 📄 Licencia

Este proyecto está licenciado bajo la **GNU General Public License v3.0 (GPLv3)**. Consulta el archivo `LICENSE` para más detalles.
