# COLEGA (v2.5.0-Experimental)

[🇺🇸 English](#english) | [🇪🇸 Español](#español)

---

## English

> [!WARNING]
> **Beta Stability**: This release (v2.5.0) is on the `main` branch but is considered **Experimental**. While feature-complete, you may encounter bugs or instability as we optimize the new Core V2.5 architecture. Report issues on GitHub!

**C.O.L.E.G.A.** (Language Copilot for Group and Administration Environments)

COLEGA is a proactive and modular personal assistant designed to run locally on modest hardware. It combines the efficiency of a rule-based system for system control and home automation with the intelligence of a local LLM (**Gemma 2B**) for natural conversations and reasoning.

![Status](https://img.shields.io/badge/Status-Beta-yellow)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)

### 🌟 New in v2.5.0 (Experimental)

* **⚡ Core V2.5 (Optimization)**: Deep internal optimization for dual-core CPUs (i3).
  * **Thread Watchdog**: Self-healing for internal processes (Voice, Events).
  * **Resource Tuning**: Strict PyTorch threading limits to prevent audio stuttering.
* **🖥️ Web Interface V3**:
  * **Drag-and-Drop Dashboard**: Customize your workspace with persistent layouts.
  * **Unified Notifications**: Replaced browser alerts with a modern Toast system + Desktop Notifications.
  * **Connection Monitor**: Full-screen overlay that automatically detects system restarts/outages.
  * **About & Updates**: Dedicated section for version management.
* **🥭 SysAdmin AI ([MANGOT5](https://huggingface.co/jrodriiguezg/mango-t5-770m))**: Robust translation of natural language to Bash commands.

### 🚀 Key Features

#### 🧠 Hybrid Intelligence

* **Local LLM**: Integration with **Gemma 2B** (4-bit) for fluid conversations.
* **SysAdmin AI**: **MANGO T5** model for robust Natural Language to Bash translation.
* **Memory (Brain)**: Long-term memory system and alias learning.
* **RAG (Retrieval-Augmented Generation)**: Query local documents.

#### 🗣️ Natural Interaction

* **Visual Interface**: Reactive "Face" (Web UI) showing states (listening, thinking, speaking).
* **Speech**: Natural synthesis with **Piper TTS** and offline recognition (Vosk/Whisper).

#### 🛡️ Security & Maintenance (Advanced)

* **NeoGuard**: IDS (Intrusion Detection System) that monitors logs (`auth.log`) and resources to detect brute-force attacks or anomalies.
* **Auto-Diagnosis**: C.O.L.E.G.A. can read its own logs, find errors, and use AI to explain what is failing and how to fix it.



### 🔧 Installation

**Quick Install (One-line command):**

```bash
wget -O install.sh https://raw.githubusercontent.com/jrodriiguezg/COLEGA/refs/heads/main/install.sh && chmod +x install.sh && ./install.sh
```

**Manual Installation:**

```bash
# Clone the repository
git clone https://github.com/jrodriiguezg/COLEGA.git
cd COLEGA

# Run the installer
./install.sh
```

### ⚙️ Configuration

Main configuration: `config/config.json`.
Access the Web Interface at `http://localhost:5000`.

---

## Español

> [!WARNING]
> **Estabilidad Beta**: Esta versión (v2.5.0) está en la rama `main` pero se considera **Experimental**. Aunque es funcional, puedes encontrar errores mientras pulimos la nueva arquitectura del Core V2,5. ¡Reporta fallos en GitHub!

**C.O.L.E.G.A.** (COpiloto de Lenguaje para Entornos de Grupo y Administración)

COLEGA es un asistente personal proactivo y modular diseñado para ejecutarse localmente.

![Status](https://img.shields.io/badge/Status-Beta-yellow)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![License](https://img.shields.io/badge/License-GPLv3-green)

### 🌟 Novedades en v2.5.0 (Experimental)

* **⚡ Core V2.5 (Optimización)**: Optimización interna profunda para CPUs de doble núcleo (i3).
  * **Thread Watchdog**: Sistema de "autocuración" para procesos internos (Voz, Eventos).
  * **Ajuste de Recursos**: Limitación estricta de hilos PyTorch para evitar cortes de audio.
* **🖥️ Interfaz Web V2.2**:
  * **Dashboard Personalizable**: Organiza los widgets con **Drag-and-Drop** (se guarda solo).
  * **Notificaciones Unificadas**: Sistema de Toasts moderno + Notificaciones de Escritorio.
  * **Monitor de Conexión**: Overlay a pantalla completa que detecta reinicios del servidor automáticamente.
  * **Actualizaciones**: Nueva sección "About" para gestión de versiones.
* **🥭 SysAdmin AI (MANGO T5)**: Traducción robusta de comandos.

### 🚀 Características Principales

#### 🧠 Inteligencia Híbrida

* **LLM Local**: **Gemma 2B** para conversaciones.
* **SysAdmin AI**: **MANGO T5** para comandos Bash.
* **Memoria (Brain)**: Memoria a largo plazo y RAG.

#### 🗣️ Interacción Natural

* **Voz**: Reconocimiento offline con **Vosk** o **Whisper**.
* **Habla**: Síntesis natural con **Piper TTS**.
* **Interfaz Visual**: "Cara" reactiva que muestra estados del asistente.

#### 🛡️ Advanced Capabilities

* **NeoGuard**: Monitor de seguridad en tiempo real.
* **Auto-Diagnóstico**: Análisis de logs asistido por IA.
* **Multi-Room**: Control de dispositivos Cast.

#### 🛠️ Administración de Sistemas & Redes

### 🔧 Instalación

**Instalación Rápida (Comando único):**

```bash
wget -O install.sh https://raw.githubusercontent.com/jrodriiguezg/COLEGA/refs/heads/main/install.sh && chmod +x install.sh && ./install.sh
```

**Instalación Manual:**

```bash
git clone https://github.com/jrodriiguezg/COLEGA.git
cd COLEGA
./install.sh
```

### 🖥️ Uso

* **Interfaz Web**: `http://localhost:5000`
* **Logs**: `journalctl --user -u neo.service -f`
