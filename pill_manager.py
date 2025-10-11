
import json
import logging
import random
from datetime import datetime

class PillManager:
    """
    Gestiona la carga y consulta del horario de pastillas desde pastillero.json.
    """
    # CORRECCIÓN: Apuntar a la nueva carpeta 'jsons'
    def __init__(self, file_path='jsons/pastillero.json'):
        self.file_path = file_path
        self.schedule = self.load_schedule()
        self.last_reminded = {} # Para no repetir recordatorios en el mismo minuto

    def load_schedule(self):
        """Carga el fichero JSON del pastillero."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                logging.info("Cargando datos del pastillero desde pastillero.json.")
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"No se pudo cargar el pastillero: {e}")
            return {"horarios": [], "pastillas": {}, "colores": {}}

    def add_pill(self, pill_name, day, time_slot):
        """Añade una pastilla al horario y guarda el fichero JSON."""
        try:
            if day not in self.schedule['pastillas']:
                self.schedule['pastillas'][day] = {}
            if time_slot not in self.schedule['pastillas'][day]:
                self.schedule['pastillas'][day][time_slot] = []
            if pill_name not in self.schedule['pastillas'][day][time_slot]:
                self.schedule['pastillas'][day][time_slot].append(pill_name)
                logging.info(f"Añadida '{pill_name}' al pastillero para el {day} a las {time_slot}.")

            if time_slot not in self.schedule['horarios']:
                self.schedule['horarios'].append(time_slot)
                self.schedule['horarios'].sort()

            if pill_name not in self.schedule['colores']:
                colores_disponibles = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#e67e22", "#1abc9c"]
                self.schedule['colores'][pill_name] = random.choice(colores_disponibles)

            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.schedule, f, indent=4, ensure_ascii=False)
            
            return True
        except (IOError, KeyError) as e:
            logging.error(f"Error al escribir en el pastillero: {e}")
            return False

    def delete_pill(self, pill_name, day, time_slot):
        """Elimina una pastilla del horario y guarda el fichero JSON."""
        try:
            if day in self.schedule['pastillas'] and \
               time_slot in self.schedule['pastillas'][day] and \
               pill_name in self.schedule['pastillas'][day][time_slot]:
                
                self.schedule['pastillas'][day][time_slot].remove(pill_name)
                logging.info(f"Eliminada '{pill_name}' del pastillero para el {day} a las {time_slot}.")

                is_time_slot_used = False
                for d in self.schedule.get('pastillas', {}):
                    if self.schedule['pastillas'][d].get(time_slot):
                        is_time_slot_used = True
                        break
                
                if not is_time_slot_used and time_slot in self.schedule.get('horarios', []):
                    self.schedule['horarios'].remove(time_slot)
                    logging.info(f"Horario '{time_slot}' eliminado de la lista global.")

                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.schedule, f, indent=4, ensure_ascii=False)
                return True
            else:
                logging.warning(f"Intento de eliminar una pastilla no existente: {pill_name} el {day} a las {time_slot}")
                return False
        except (IOError, KeyError) as e:
            logging.error(f"Error al eliminar del pastillero: {e}")
            return False

    def check_reminders(self):
        """Comprueba si hay que tomar pastillas a la hora actual."""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        day_map = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
        current_day_es = day_map.get(now.strftime('%A'), None)

        pills_to_take = self.schedule.get('pastillas', {}).get(current_day_es, {}).get(current_time, [])

        if pills_to_take and self.last_reminded.get(current_time) != now.minute:
            self.last_reminded = {current_time: now.minute}
            return pills_to_take
        return []

    # --- NUEVA FUNCIÓN AÑADIDA ---
    def get_todays_pills_summary(self):
        """
        Lee el horario cargado y devuelve un resumen en texto de las
        pastillas programadas para el día de hoy.
        """
        now = datetime.now()
        day_map = {
            0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
            4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
        }
        current_day_es = day_map.get(now.weekday())

        if not current_day_es or current_day_es not in self.schedule.get('pastillas', {}):
            return ""

        todays_schedule = self.schedule['pastillas'][current_day_es]
        
        if not todays_schedule:
            return ""

        summary_parts = []
        # Iterar por los horarios definidos para mantener el orden
        for time_slot in sorted(todays_schedule.keys()):
            if todays_schedule[time_slot]: # Comprobar que haya pastillas en la franja
                pills = ", ".join(todays_schedule[time_slot])
                summary_parts.append(f"a las {time_slot}, te toca {pills}")
        
        if not summary_parts:
            return ""

        return "; ".join(summary_parts)

    def get_pills_summary_for_day(self, day_es):
        """
        Lee el horario cargado y devuelve un resumen en texto de las
        pastillas programadas para un día específico.
        """
        day_es = day_es.capitalize() # Asegurarse de que la primera letra es mayúscula

        day_schedule = self.schedule.get('pastillas', {}).get(day_es)

        if not day_schedule:
            return f"No hay nada programado para el {day_es}."

        summary_parts = []
        # Iterar por los horarios definidos para mantener el orden
        for time_slot in sorted(day_schedule.keys()):
            pills = day_schedule.get(time_slot)
            if pills: # Comprobar que haya pastillas en la franja
                pills_str = ", ".join(pills)
                summary_parts.append(f"a las {time_slot}, te toca {pills_str}")
        
        if not summary_parts:
            return f"No hay nada programado para el {day_es}."

        return f"el {day_es}, " + "; ".join(summary_parts)