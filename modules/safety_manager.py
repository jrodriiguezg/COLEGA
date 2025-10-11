import time
import random
import os
import math
import json

class SafetyManager:
    """
    Módulo de seguridad proactiva.
    Monitoriza la actividad del usuario y los datos de wearables (simulados)
    para detectar posibles emergencias como inactividad prolongada o caídas.
    """
    def __init__(self, contact_manager):
        # --- Umbrales para alertas del wearable ---
        self.HEART_RATE_LOW_THRESHOLD = 50
        self.HEART_RATE_HIGH_THRESHOLD = 130
        self.FALL_IMPACT_THRESHOLD = 25.0 # m/s^2, un valor alto para detectar un impacto

        self.contact_manager = contact_manager
        
        # Umbral para la alerta de inactividad (24 horas en segundos)
        self.INACTIVITY_ALERT_THRESHOLD_SECONDS = 12 * 3600 # Cambiado a 12 horas
        
        # Registra el último momento en que se detectó cualquier tipo de actividad
        self.last_activity_timestamp = time.time()
        
        # Flag para evitar enviar alertas de inactividad repetidamente
        self.inactivity_alert_sent = False

    def update_activity(self):
        """
        Debe ser llamado cada vez que se detecta una interacción del usuario
        (movimiento, clic, comando de voz, etc.).
        """
        #print("DEBUG: SafetyManager - Actividad actualizada.")
        self.last_activity_timestamp = time.time()
        # Si se detecta actividad, reseteamos el flag de la alerta
        self.inactivity_alert_sent = False

    def check_for_emergency(self):
        """
        Comprueba periódicamente si se ha superado el umbral de inactividad.
        Devuelve acciones de emergencia si es necesario.
        """
        actions = []
        inactivity_duration = time.time() - self.last_activity_timestamp

        # Comprobar si se ha superado el umbral y si no se ha enviado ya una alerta
        if inactivity_duration > self.INACTIVITY_ALERT_THRESHOLD_SECONDS and not self.inactivity_alert_sent:
            print(f"ALERTA DE SEGURIDAD: Inactividad prolongada detectada ({inactivity_duration / 3600:.1f} horas).")
            self.inactivity_alert_sent = True # Marcar como enviada para no repetir
            
            emergency_contact = self.contact_manager.get_emergency_contact()
            contact_name = emergency_contact['name'] if emergency_contact else "el contacto de emergencia"

            actions.append({
                'type': 'speak',
                'text': f"Alerta de inactividad prolongada. No se ha detectado actividad en más de 24 horas. Iniciando protocolo de emergencia. Contactando con {contact_name} y los servicios de emergencia."
            })
            actions.append({
                'type': 'emergency_call',
                'target': 'contact',
                'details': emergency_contact
            })
            actions.append({
                'type': 'emergency_call',
                'target': 'services',
                'details': {'number': '112'} # Número de emergencia
            })
        
        return actions

    def check_wearable_data_file(self):
        """
        Comprueba si existe el fichero 'wearable_data.json' con nuevos datos,
        lo lee y luego lo elimina para no procesarlo de nuevo.
        """
        data_file = 'wearable_data.json'
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    event_data = json.load(f)
                os.remove(data_file) # Eliminar para marcar como procesado
                return event_data
            except (json.JSONDecodeError, IOError) as e:
                print(f"SafetyManager: Error al leer el fichero de datos del wearable: {e}")
                # Si el fichero está corrupto o hay un problema, lo eliminamos
                os.remove(data_file)
        return None

    def simulate_wearable_data(self):
        """
        Simula la recepción de datos de una pulsera de actividad.
        En un futuro, esta función se conectaría a una app o API real.
        
        :return: Un diccionario con el evento detectado o None.
        """
        # Para la simulación, hay una pequeña probabilidad de que ocurra un evento
        if random.random() < 0.0001: # Probabilidad muy baja para que no sea constante
            return {'type': 'fall_detected'}
        
        if random.random() < 0.0002:
            # Simular un pulso anómalo (muy alto o muy bajo)
            return {'type': 'heart_rate_alert', 'value': random.choice([45, 140])}

        return None

    def process_wearable_data(self, data):
        """
        Procesa los datos brutos del wearable (nuevo formato JSON) y devuelve acciones.
        """
        actions = []

        # 1. Comprobar datos del acelerómetro para detectar caídas
        if 'accelerometer' in data:
            accel = data['accelerometer']
            # Calcular la magnitud del vector del acelerómetro
            magnitude = math.sqrt(accel['x']**2 + accel['y']**2 + accel['z']**2)
            
            # Si la magnitud supera un umbral de impacto, es una posible caída.
            # Nota: una detección de caídas real es más compleja (implica detectar
            # un periodo de 'caída libre' antes del impacto), pero esto es un buen comienzo.
            if magnitude > self.FALL_IMPACT_THRESHOLD:
                print(f"SAFETY_MANAGER: ¡Impacto detectado! Magnitud: {magnitude:.2f}")
                actions.append({'type': 'speak', 'text': "¡Se ha detectado una posible caída! ¿Estás bien?"})

        # 2. Comprobar el ritmo cardíaco para detectar anomalías
        if 'heart_rate' in data:
            hr = data['heart_rate']
            if hr < self.HEART_RATE_LOW_THRESHOLD:
                print(f"SAFETY_MANAGER: ¡Ritmo cardíaco bajo detectado! Valor: {hr}")
                actions.append({'type': 'speak', 'text': f"Alerta de pulso: se ha detectado un ritmo bajo de {hr} pulsaciones. ¿Te encuentras bien?"})
            elif hr > self.HEART_RATE_HIGH_THRESHOLD:
                print(f"SAFETY_MANAGER: ¡Ritmo cardíaco alto detectado! Valor: {hr}")
                actions.append({'type': 'speak', 'text': f"Alerta de pulso: se ha detectado un ritmo alto de {hr} pulsaciones. ¿Te encuentras bien?"})

        return actions