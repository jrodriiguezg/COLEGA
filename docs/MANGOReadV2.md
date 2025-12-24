# 🥭 MANGO: The Sysadmin AI Assistant

MANGO es un modelo de Inteligencia Artificial especializado en Administración de Sistemas Linux y DevOps. Su objetivo es traducir lenguaje natural (desde peticiones técnicas formales hasta jerga coloquial de "compañero de trabajo") en comandos de Bash ejecutables y precisos.

> "Tu compañero de batalla en la terminal, que entiende lo que necesitas incluso a las 3 de la mañana."

## 🚀 Novedades de la Versión 2.0

### 🧠 Nueva Arquitectura: CodeT5

Hemos migrado del enfoque Decoder-only (tipo GPT/Qwen) a una arquitectura Encoder-Decoder basada en T5.

* **¿Por qué?** T5 trata la generación de código como un problema de "traducción" (Español → Bash), lo que elimina la "verborrea" innecesaria y garantiza una sintaxis mucho más estricta y segura.
* **Resultado:** Un modelo más ligero, rápido y con una tasa de acierto sintáctico superior.

### 📚 Dataset "Gold Standard" & "Bro-Slang"

El modelo ha sido entrenado con un dataset híbrido de +2.600 instrucciones curadas manualmente (MANGO_DATA), dividido en dos vertientes:

* **Core Técnico:** Basado en documentación oficial, apuntes académicos de administración de sistemas y ejercicios de certificación (LVM, RAID, Redes, Systemd).
* **Modo "Bro":** Miles de variaciones con jerga real de oficina ("tumba el servicio", "cepíllate los logs", "levanta el chiringuito").

## 🛠️ Instalación y Uso

### Requisitos

* Python 3.8+
* PyTorch
* Transformers (Hugging Face)

**Inferencia Rápida (Python)**
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Cargar el modelo MANGO
```python
model_name = "tusuario/mango-sysadmin-t5"  # (Sustituir por tu repo real)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def ask_mango(prompt):
    input_ids = tokenizer.encode(prompt, return_tensors="pt")
    outputs = model.generate(input_ids, max_length=128)
    print(f"🥭 Mango dice: {tokenizer.decode(outputs[0], skip_special_tokens=True)}")

# Ejemplos:
ask_mango("Búscame los archivos más grandes del disco")
ask_mango("Tumba la interfaz de red eth0")
ask_mango("Cepíllate los logs viejos de docker")
``` 
## 📊 Capacidades del Modelo

MANGO es capaz de generar one-liners complejos para:

| Categoría | Ejemplos de lo que puede hacer |
| --- | --- |
| Sistemas | systemctl, journalctl, gestión de procesos (kill, htop). |
| Redes | Diagnóstico (ping, dig, traceroute), Firewall (ufw, iptables), Configuración IP. |
| DevOps | Docker (ciclo de vida completo), Git (flujo de trabajo), Kubernetes básico. |
| Ficheros | Búsquedas complejas (find, grep), permisos, compresión, manipulación de texto (awk, sed). |
| Seguridad | Gestión de claves SSH, GPG, OpenSSL, auditoría básica. |

## 📂 Estructura del Dataset de Entrenamiento

El conocimiento de MANGO reside en dos ficheros JSONL principales:

* **gold_commands.jsonl:** 1.400+ Comandos técnicos, académicos y legacy.
* **bro_commands.jsonl:** 1.200+ Variaciones coloquiales, jerga y situaciones de estrés.


