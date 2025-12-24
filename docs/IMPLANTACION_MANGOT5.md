# IMPLANTACIÓN DE MANGO T5: Guía Técnica

**Versión:** 1.0
**Fecha:** 18/12/2025
**Proyecto:** COLEGA - Sysadmin AI

## 1. Introducción

Este documento detalla la integración del modelo **MANGO T5** (Fine-Tuned for Bash) en la arquitectura del sistema COLEGA. Esta actualización introduce una capacidad especializada de "Natural Language to Bash" (NL2Bash), permitiendo al asistente ejecutar comandos de sistema complejos con alta precisión sintáctica, algo que los modelos de chat generalistas (Llama/Qwen) no logran de forma fiable.

## 2. Arquitectura Implementada

### 2.1 Componentes Nuevos

*   **`modules/mango_manager.py`**: Nuevo gestor encargado de cargar el modelo T5 y realizar inferencias.
    *   **Modelo**: Carga artefactos desde el directorio `MANGOT5/` usando `transformers` (Hugging Face).
    *   **Inferencia**: Utiliza generación secuencial (Beam Search) para traducir texto a código.
    *   **Salida**: Retorna el comando generado y un *score* de confianza.

### 2.2 Integración en NeoCore

El flujo de procesamiento de comandos ha sido modificado en `NeoCore.py` para seguir esta lógica de cascada:

1.  **Intents (Padatious/Regex)**: Se, prioriza la detección de intenciones predefinidas (alarmas, hora, chistes).
2.  **MANGO T5 (NL2Code)**: Si no hay intent, se pasa el texto a MANGO.
    *   Si la confianza es alta (> 0.6), se evalúa el comando.
    *   **Safe List**: Comandos inofensivos (`echo`, `ls`) se ejecutan automáticamente.
    *   **Confirmación**: Comandos potencialmente peligrosos (`rm`, `service restart`, etc.) requieren la confirmación explícita del usuario ("He generado X, ¿ejecuto?").
3.  **Chat (Llama/Gemma)**: Si MANGO no detecta una instrucción técnica clara, el texto pasa al motor de chat para una respuesta conversacional.

## 3. Requisitos de Ejecución

Se han añadido las siguientes dependencias al `requirements.txt`:
*   `transformers`: Librería base para manejar modelos Hugging Face.
*   `torch`: Framework de Deep Learning (PyTorch).
*   `sentencepiece`: Tokenizer necesario para modelos T5.

## 4. Instrucciones de Uso

### 4.1 Comandos Automáticos
El usuario puede pedir información de lectura segura:
> *"Busca los archivos en /home"* -> Ejecuta `ls` o `find` inmediatamente.

### 4.2 Comandos Críticos
Para acciones de modificación:
> *"Reinicia el servicio nginx"* -> MANGO genera `systemctl restart nginx`.
> **COLEGA**: *"He generado el comando: systemctl restart nginx. ¿Quieres que lo ejecute?"*
> **Usuario**: *"Sí"* -> Se ejecuta.

## 5. Mantenimiento y Optimización

*   **Modelo**: Si se entrena una nueva versión de MANGO, basta con reemplazar los archivos en la carpeta `MANGOT5`.
*   **Safety**: La lista de comandos seguros ("whitelist") está hardcodeada en `NeoCore.py` y debería expandirse según se validen más casos de uso.
*   **Hardware**: Actualmente corre en CPU (por defecto en i3/8GB). Si se dispone de GPU, `MangoManager` intentará usar CUDA automáticamente.
