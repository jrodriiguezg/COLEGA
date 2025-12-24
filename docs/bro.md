# 🤖 Network Bros (MNB) - Documentación Oficial

**Network Bros** es la iniciativa para extender los sentidos de TIO más allá del servidor principal, utilizando microcontroladores y ordenadores de placa reducida (SBC) como agentes satélite.

---

## 1. Arquitectura

El sistema utiliza una arquitectura híbrida **WiFi (MQTT) + Bluetooth (RFCOMM)** para garantizar la comunicación incluso en entornos inestables.

### 1.1. Protocolo de Comunicación
Los agentes envían mensajes en formato **JSON** a TIO.

*   **Canal MQTT**: `tio/agents/{HOSTNAME}/{TYPE}`
*   **Canal Bluetooth**: RFCOMM Puerto 1 (Serial)

### 1.2. Tipos de Mensajes (`TYPE`)

#### A. Telemetría (`telemetry`)
Datos periódicos de estado. TIO muestra una notificación visual (Pop-up Azul).
```json
{
  "agent": "salon_pi",
  "type": "telemetry",
  "data": {
    "temp": 24.5,
    "humidity": 60,
    "cpu": 15.2,
    "status": "online"
  }
}
```

#### B. Alertas (`alert`)
Eventos críticos. TIO interrumpe, habla por voz y muestra una alerta roja.
```json
{
  "agent": "puerta_entrada",
  "type": "alert",
  "data": {
    "msg": "Movimiento detectado en la entrada",
    "level": "critical"
  }
}
```

---

## 2. Implementación en TIO (Servidor)

TIO (`NeoCore.py`) ejecuta dos gestores en segundo plano:

1.  **`MQTTManager`**:
    *   Se conecta al broker local (Mosquitto).
    *   Se suscribe a `tio/agents/#`.
    *   Gestiona la reconexión automática.

2.  **`BluetoothManager`**:
    *   Abre un socket servidor RFCOMM en el **Puerto 1**.
    *   Espera conexiones entrantes de agentes emparejados.
    *   Inyecta los mensajes recibidos en la misma cola de eventos que MQTT.

---

## 3. Guía de Despliegue de Agentes

El código fuente de los agentes se encuentra en `resources/MNB/`.

### 3.1. Raspberry Pi Zero (Python)
Ideal para agentes con cámara o sensores complejos.

**Requisitos:**
*   Python 3
*   Librerías: `paho-mqtt`, `psutil` (opcional: `bluez` para bluetooth).

**Instalación:**
1.  Copiar `resources/MNB/PiZero/agent.py` a la Pi.
2.  Editar la configuración (IP del servidor TIO).
3.  Ejecutar: `python3 agent.py`.

### 3.2. ESP32 (MicroPython)
Ideal para sensores de bajo consumo (temperatura, puertas).

**Requisitos:**
*   Firmware MicroPython.
*   Librería `umqtt.simple`.

**Instalación:**
1.  Flashar MicroPython en el ESP32.
2.  Subir `resources/MNB/ESP32/boot.py` y `main.py`.
3.  Configurar WiFi y Broker IP en `main.py`.

---

## 4. Modo Fallback (Bluetooth)

Si el WiFi falla, los agentes están programados (o deben programarse) para intentar conectar por Bluetooth al servidor TIO.

1.  **Escaneo**: El agente busca dispositivos Bluetooth cercanos.
2.  **Conexión**: Intenta conectar al servicio RFCOMM en el Puerto 1 de TIO.
3.  **Envío**: Envía el mismo JSON que enviaría por MQTT, seguido de un salto de línea (`\n`).

> **Nota**: Para que esto funcione, es recomendable emparejar previamente los dispositivos Bluetooth (`bluetoothctl pair <MAC_AGENTE>`) en el servidor TIO para evitar problemas de permisos, aunque el socket RFCOMM suele aceptar conexiones si está configurado en modo "Visible" o "Discoverable" temporalmente.
