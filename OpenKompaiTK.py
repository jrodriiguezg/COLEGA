import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import queue
import time
import logging
import locale
import json
import random
import socket
import subprocess
from datetime import datetime, date, timedelta

# --- Módulos Externos ---
try:
    from video_sensor import VideoSensor
except ImportError:
    VideoSensor = None
try:
    import vlc
except ImportError:
    vlc = None
try:
    import vosk
    import pyaudio
    VOSK_DISPONIBLE = True
except ImportError:
    vosk = pyaudio = None
    VOSK_DISPONIBLE = False
try:
    from PIL import Image, ImageTk
    import psutil
except ImportError:
    Image = ImageTk = None
    psutil = None
# --- NUEVO: Librería para reconocimiento de voz robusto ---
try:
    from thefuzz import fuzz
    THEFUZZ_DISPONIBLE = True
except ImportError:
    THEFUZZ_DISPONIBLE = False

from pill_manager import PillManager
from modules.safety_manager import SafetyManager
from modules.contacts import ContactManager
from modules.calendar import CalendarManager
from modules.alarms import AlarmManager
from modules.date_parser import parse_reminder_from_text, parse_alarm_from_text

# --- Paleta de Colores (Versión Completa) ---
COLOR_PRIMARY_BG = "#F0F4F8"
COLOR_SECONDARY_BG = "#CFD8DC"
COLOR_HEADER_BG = "#78909C"
COLOR_TEXT_DARK = "#333333"
COLOR_TEXT_LIGHT = "white"
COLOR_BUTTON_NORMAL = "#90CAF9"
COLOR_BUTTON_HOVER = "#64B5F6"
COLOR_BUTTON_PRESSED = "#42A5F5"
COLOR_BUTTON_FOCUS = "#2196F3"
COLOR_ERROR_RED = "#EF5350"
COLOR_ERROR_RED_HOVER = "#E53935"
COLOR_ERROR_RED_PRESSED = "#C62828"
COLOR_LOG_BG = "#263238"
COLOR_LOG_TEXT = "#CFD8DC"
COLOR_LOG_HEADER = "#455A64"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

# --- NUEVO: Configuración de logging por módulos en la carpeta 'logs' ---
os.makedirs('logs', exist_ok=True)

def setup_logger(name, log_file, level=logging.INFO):
    """Función para configurar un logger específico."""
    handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

# Configurar un logger para cada módulo
app_logger = setup_logger('app', 'logs/app.log')
tts_logger = setup_logger('tts', 'logs/tts.log')
vosk_logger = setup_logger('vosk', 'logs/vosk.log')
video_logger = setup_logger('video', 'logs/video.log')
app_logger.info("El registro de logs ha sido iniciado.")
# --- Clases Auxiliares ---
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    def emit(self, record):
        self.log_queue.put(self.format(record))

class Speaker:
    def __init__(self, ui_queue):
        self.speak_queue = queue.Queue()
        self.ui_queue = ui_queue
        self._is_busy = False
        self.is_available = False
        # CORRECCIÓN: Usar las rutas absolutas y exactas proporcionadas por el usuario.
        self.piper_bin = '/home/user/piper/install/piper'
        self.piper_model = '/home/user/piper/voices/es_ES/es_ES-davefx-medium.onnx'

        # --- Comprobación detallada de los ficheros de Piper ---
        piper_ok = os.path.isfile(self.piper_bin)
        model_ok = os.path.isfile(self.piper_model)

        if not piper_ok:
            tts_logger.error(f"ERROR CRÍTICO: El ejecutable de Piper NO se encontró en: '{self.piper_bin}'")
        if not model_ok:
            tts_logger.error(f"ERROR CRÍTICO: El modelo de voz de Piper NO se encontró en: '{self.piper_model}'")

        if piper_ok and model_ok:
            self.is_available = True
            tts_logger.info("Motor de voz 'Piper' encontrado.")
            self.speak_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.speak_thread.start()
        else:
            tts_logger.error("El motor de voz no se iniciará debido a los errores anteriores.")

    def _process_queue(self):
        while True:
            text = self.speak_queue.get()
            self._is_busy = True
            try:
                # SOLUCIÓN: Volver a un pipeline simple y robusto usando 'printf' en lugar de 'echo'
                # para evitar problemas con caracteres especiales. Esto es más fiable que el pipeline
                # de subprocesos de Python para este caso de uso.
                tts_logger.info(f"Intentando decir: '{text}'")
                command = f'printf "%s" "{text}" | {self.piper_bin} --model {self.piper_model} --length_scale 1.1 --output_raw | aplay -r 22050 -f S16_LE -t raw -'
                # Notificar a la UI que el asistente está hablando
                self.ui_queue.put({'type': 'speaker_status', 'status': 'speaking'})
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    tts_logger.error(f"El comando de Piper/aplay falló con código {result.returncode}.")
                    tts_logger.error(f"STDERR: {result.stderr.strip()}")
            except subprocess.CalledProcessError as e:
                tts_logger.error(f"Error al ejecutar Piper/aplay: {e}")
                tts_logger.error(f"STDERR del error: {e.stderr}")
            finally:
                self._is_busy = False
                # Notificar a la UI que el asistente ha terminado de hablar
                self.ui_queue.put({'type': 'speaker_status', 'status': 'idle'})

    def speak(self, text):
        if self.is_available: self.speak_queue.put(text)
    def set_rate(self, rate): pass
    def get_rate(self): return 150
    @property
    def is_busy(self): return self._is_busy or not self.speak_queue.empty()

# --- Clase de Vista de Cámara ---
class CameraView(tk.Frame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg="black")
        self.controller = controller
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=5)
        header.pack(fill="x")
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("MainView"))
        back_button.pack(side="left", padx=10)
        title_label = tk.Label(header, text="Visor de Cámara", font=("Helvetica", 16, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)
        self.video_label = tk.Label(self, bg="black")
        self.video_label.pack(expand=True, fill="both")

    def update_frame(self, frame_rgb):
        try:
            pil_image = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=pil_image)
            self.video_label.config(image=imgtk)
            self.video_label.image = imgtk
        except Exception as e:
            logging.debug(f"Error al actualizar frame de cámara: {e}")


# --- Clase Principal de la Aplicación ---
class KompaiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OpenKompai")
        self.attributes('-fullscreen', True)
        self.configure(bg=COLOR_PRIMARY_BG)

        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            app_logger.warning("Localización 'es_ES.UTF-8' no encontrada.")

        self.ui_queue = queue.Queue()
        self.pill_manager = PillManager()
        self.speaker = Speaker(self.ui_queue)
        # --- ACTIVACIÓN DE MÓDULOS PROACTIVOS ---
        self.contact_manager = ContactManager('jsons/datos_emergencia.json')
        self.calendar_manager = CalendarManager()
        self.alarm_manager = AlarmManager()
        self.vlc_instance, self.player = self.setup_vlc()
        # self.safety_manager = SafetyManager(self.contact_manager)

        self.log_queue = queue.Queue()
        queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
        # No añadir el handler a la raíz para evitar duplicados, ya que cada logger tiene el suyo.
        logging.getLogger().addHandler(queue_handler)
        # CORRECCIÓN: Apuntar a la nueva carpeta 'jsons'
        self.intents = self.load_json_data('jsons/intents.json', 'intents')
        self.radios = self.load_json_data('jsons/radios.json', 'emisoras')
        # --- OPTIMIZACIÓN: Pre-procesar intenciones para búsqueda rápida ---
        self.intent_map = {}
        if self.intents:
            for intent in self.intents:
                for trigger in intent.get('triggers', []):
                    # Guardamos la intención completa asociada a cada trigger
                    self.intent_map[trigger] = intent
        app_logger.info(f"Pre-procesadas {len(self.intent_map)} intenciones para búsqueda rápida.")
        self.datos_emergencia = self.load_json_data('jsons/datos_emergencia.json')
        # --- NUEVO: Cargar chistes y datos curiosos ---
        self.chistes = self.load_json_data('jsons/chistes.json', 'chistes')
        self.datos_curiosos = self.load_json_data('jsons/datos_curiosos.json', 'datos')
        
        self.setup_vosk()
        # --- Variables de estado para flujos conversacionales ---
        self.waiting_for_fall_response = False
        self.fall_response_timer = None
        self.consecutive_failures = 0
        self.morning_summary_sent_today = False
        self.waiting_for_timer_duration = False
        self.active_timer_end_time = None
        self.is_processing_command = False # Bloqueo para evitar eco
        # --- NUEVO: Variables para el diálogo de creación de pastillas ---
        self.waiting_for_pill_info = False
        self.pill_dialog_step = None # 'name', 'days', 'time', 'confirm'
        self.pill_creation_data = {}
        # --- NUEVO: Variables para el diálogo de creación de recordatorios ---
        self.waiting_for_reminder_date = False
        self.pending_reminder_description = None
        self.waiting_for_reminder_confirmation = False
        self.pending_reminder_data = None
        # --- NUEVO: Variables para el diálogo de creación de alarmas ---
        self.waiting_for_alarm_confirmation = False
        self.pending_alarm_data = None

        self.last_spoken_text = "" # NUEVO: Para eliminar el eco del texto reconocido
        self.emergency_view_instance = None

        self.camera_status = "Desconocido"
        self.video_sensor = None
        if VideoSensor:
            self.video_sensor_start()

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.pack_propagate(False)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainView, CalendarView, PillboxView, LogView, SettingsView, AlarmView, SystemStatusView, HealthDataView):
            page_name = F.__name__
            frame = F(parent=container, controller=self, log_queue=self.log_queue) if F == LogView else F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MainView")
        self.start_background_tasks()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind('<Alt-F4>', lambda event: self.on_closing())

    def setup_vlc(self):
        if vlc:
            instance = vlc.Instance()
            return instance, instance.media_player_new()
        return None, None
    
    def setup_vosk(self):
        self.vosk_model = None
        if VOSK_DISPONIBLE:
            model_path = "vosk-models/es"
            if os.path.isdir(model_path):
                try:
                    self.vosk_model = vosk.Model(model_path)
                    vosk_logger.info("Modelo Vosk cargado.")
                except Exception as e:
                    vosk_logger.error(f"Error al cargar modelo Vosk: {e}")
            else:
                vosk_logger.warning(f"Modelo Vosk no encontrado en '{model_path}'.")
                
    def video_sensor_start(self):
        ESP32_STREAM_URL = "http://10.115.128.54/stream" # CAMBIA ESTO
        self.video_sensor = VideoSensor(stream_url=ESP32_STREAM_URL, ui_queue=self.ui_queue)

    def load_json_data(self, filepath, key=None):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                app_logger.info(f"Fichero '{filepath}' cargado.")
                return data.get(key) if key else data
        except Exception as e:
            app_logger.error(f"Error al cargar '{filepath}': {e}")
            return [] if key else {}

    def on_closing(self):
        app_logger.info("Cerrando la aplicación.")
        self.destroy()

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, 'on_show'): frame.on_show()

    def start_background_tasks(self):
        threading.Thread(target=self.proactive_update_loop, daemon=True).start()
        self.process_ui_queue()
        if self.video_sensor:
            threading.Thread(target=self.video_sensor.run, daemon=True).start()
        if VOSK_DISPONIBLE and self.vosk_model:
             threading.Thread(target=self.continuous_voice_listener, daemon=True).start()

    def continuous_voice_listener(self):
        main_view = self.frames.get("MainView")
        recognizer = vosk.KaldiRecognizer(self.vosk_model, 16000)
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
        try:
            stream.start_stream()
            vosk_logger.info("Micrófono abierto. Iniciando escucha continua con Vosk.")
            self.after(0, main_view.update_status, "Escuchando...")
        except Exception as e:
            vosk_logger.error(f"CRÍTICO: No se pudo iniciar el stream del micrófono: {e}")
            return

        while True:
            try:
                # --- SOLUCIÓN AL ECO ACÚSTICO ---
                # Si el altavoz está ocupado O estamos procesando un comando, no escuchamos.
                if self.speaker.is_busy or self.is_processing_command:
                    time.sleep(0.1) # Pequeña pausa para no consumir CPU inútilmente
                    continue

                data = stream.read(4096, exception_on_overflow=False)

                partial_result = json.loads(recognizer.PartialResult())
                if partial_result.get('partial'): vosk_logger.info(f"Parcial: {partial_result['partial']}")
                
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    command = result.get('text', '')
                    
                    # --- LÓGICA DE PALABRA DE ACTIVACIÓN ---
                    if command:
                        vosk_logger.info(f"Reconocido (final): '{command}'")
                        wake_word = "teo"

                        # --- NUEVO: Lógica para eliminar el eco de la última frase hablada ---
                        if self.last_spoken_text:
                            # Comprobamos si el texto reconocido empieza con las últimas palabras del asistente
                            # Esto es útil si el usuario habla justo cuando el asistente termina.
                            last_words = ' '.join(self.last_spoken_text.lower().split()[-4:]) # Coger las últimas 4 palabras
                            if command.startswith(last_words):
                                vosk_logger.info(f"Detectado posible eco de: '{last_words}'. Eliminándolo.")
                                command = command[len(last_words):].strip()
                                vosk_logger.info(f"Comando limpio: '{command}'")
                            
                            # Limpiamos la variable para que solo se use una vez
                            self.last_spoken_text = ""


                        command_lower = command.lower()
                        
                        # --- MEJORA: Detectar la palabra de activación al principio o al final ---
                        if wake_word in command_lower:
                            # Extraer el comando real eliminando la palabra de activación
                            actual_command = command_lower.replace(wake_word, "").strip()
                            
                            if actual_command:
                                vosk_logger.info(f"Palabra de activación detectada. Procesando comando: '{actual_command}'")
                                self.after(0, main_view.update_status, f"Entendido: '{actual_command}'")
                                self.is_processing_command = True
                                self.handle_voice_command(actual_command)
                            else:
                                # Se dijo solo la palabra de activación
                                vosk_logger.info("Palabra de activación detectada sin comando. Respondiendo.")
                                self.ui_queue.put({'type': 'speak', 'text': 'Sí, dime.'})
            except Exception as e:
                vosk_logger.error(f"Error en el bucle de escucha: {e}")
                time.sleep(1) # Evitar bucles de error rápidos
                
    def process_ui_queue(self):
        try:
            while not self.ui_queue.empty():
                action = self.ui_queue.get_nowait()
                action_type = action.get('type')

                if action_type == 'speak':
                    # NUEVO: Activar el bloqueo al empezar a hablar para evitar eco.
                    self.is_processing_command = True
                    # NUEVO: Guardar el texto que se va a decir para la cancelación de eco
                    self.last_spoken_text = action['text']
                    self.speaker.speak(action['text'])
                    if action.get('is_question'): # CORRECCIÓN: 'is_question' es un flag, no una acción
                        pass # La lógica de escucha continua lo gestiona
                elif action_type == 'user_gazing': self.set_display_brightness(1.0)
                elif action_type == 'user_present' and not action.get('status', False): self.set_display_brightness(0.4)
                elif action_type == 'fall_detected': self.handle_fall_detection()
                elif action_type == 'camera_status':
                    status = action.get('status')
                    self.camera_status = status
                    if "MainView" in self.frames: self.frames["MainView"].update_camera_status(status)
                elif action_type == 'user_absent_long_time': # CORRECCIÓN: La acción debe ser 'speak'
                    self.ui_queue.put({'type': 'speak', 'text': "Llevas mucho tiempo sin actividad. ¿Estás bien?", 'is_question': True})
                # --- NUEVO: Gestionar el estado del altavoz en la UI ---
                elif action_type == 'speaker_status':
                    if action['status'] == 'speaking':
                        self.frames["MainView"].update_status("Hablando...")
                    else: # 'idle'
                        self.frames["MainView"].update_status("Escuchando...")
                        self.is_processing_command = False # Liberamos el bloqueo
        finally:
            self.after(100, self.process_ui_queue)

    def proactive_update_loop(self):
        """Bucle principal que orquesta las tareas proactivas."""
        last_hourly_check = time.time()
        last_hydration_reminder = time.time()

        while True:
            # Tareas que se comprueban frecuentemente
            self._check_frequent_tasks()

            # Tareas que se comprueban periódicamente para no ser repetitivo
            now = datetime.now()
            current_time = time.time()

            if current_time - last_hydration_reminder > (90 * 60): # Cada 90 minutos
                self.ui_queue.put({'type': 'speak', 'text': "Recuerda beber un vaso de agua para mantenerte hidratado."})
                last_hydration_reminder = current_time

            if now.hour == 9 and not self.morning_summary_sent_today:
                self.give_morning_summary()
                self.morning_summary_sent_today = True
            elif now.hour != 9: # Resetear el flag fuera de la hora del resumen
                self.morning_summary_sent_today = False

            if current_time - last_hourly_check > 3600: # Cada hora
                self.check_calendar_events()
                self.check_social_contact()
                last_hourly_check = current_time
            
            time.sleep(5)

    def _check_frequent_tasks(self):
        """Comprueba tareas de alta frecuencia como pastillas, alarmas y temporizadores."""
        # Comprobar recordatorios de pastillas
        pills = self.pill_manager.check_reminders()
        if pills:
            self.ui_queue.put({'type': 'speak', 'text': f"Recuerda tomar: {', '.join(pills)}"})
        
        # Comprobar alarmas
        alarm_actions = self.alarm_manager.check_alarms(datetime.now())
        for action in alarm_actions:
            self.ui_queue.put(action)
        
        # Comprobar temporizador activo
        if self.active_timer_end_time and datetime.now() >= self.active_timer_end_time:
            self.ui_queue.put({'type': 'speak', 'text': "¡El tiempo del temporizador ha terminado!"})
            self.active_timer_end_time = None

    def check_calendar_events(self):
            today_str = date.today().isoformat()
            events_today = self.calendar_manager.get_events_for_day(date.today().year, date.today().month, date.today().day)
            for event in events_today:
                if event['date'] == today_str:
                    msg = f"Te recuerdo que hoy a las {event['time']} tienes una cita: {event['description']}"
                    self.ui_queue.put({'type': 'speak', 'text': msg})

    def check_social_contact(self):
            for contacto in self.contact_manager.get_all_contacts():
                try:
                    days_since = (date.today() - date.fromisoformat(contacto.get('last_contact', date.today().isoformat()))).days
                    if days_since > 3:
                        msg = f"Hace {days_since} días que no hablas con {contacto['nombre']}. ¿Quieres que le llamemos?"
                        self.ui_queue.put({'type': 'speak', 'text': msg, 'is_question': True})
                        break
                except (ValueError, KeyError): continue

    def handle_voice_command(self, command_text):
        """Procesa un comando de voz, busca una intención y ejecuta una acción."""
        # --- SOLUCIÓN: Usar un bloque try...finally para garantizar la liberación del bloqueo ---
        try:
            # --- Manejo de estados conversacionales (diálogos) ---
            if self.waiting_for_fall_response:
                self.handle_fall_response(command_text)
                return
            if self.waiting_for_timer_duration:
                self.handle_timer_duration_response(command_text)
                return
            # --- NUEVO: Manejo del diálogo de creación de pastillas ---
            if self.waiting_for_pill_info:
                self.handle_pill_creation_dialog(command_text)
                return
            # --- NUEVO: Manejo de diálogos de recordatorios ---
            if self.waiting_for_reminder_date:
                self.handle_reminder_date_response(command_text)
                return
            if self.waiting_for_reminder_confirmation:
                self.handle_reminder_confirmation(command_text)
                return
            # --- NUEVO: Manejo de diálogo de confirmación de alarma ---
            if self.waiting_for_alarm_confirmation:
                self.handle_alarm_confirmation(command_text)
                return


            if not command_text:
                return

            # Normalizar la entrada a minúsculas
            command_lower = command_text.lower()
            app_logger.info(f"Comando: '{command_lower}'. Buscando intención...")

            # --- MEJORA: Búsqueda de intención robusta con FuzzyWuzzy ---
            if THEFUZZ_DISPONIBLE:
                best_match_score = 0
                best_intent = None
                
                # Iteramos sobre todas las intenciones definidas en intents.json
                for intent in self.intents:
                    # Para cada intención, comprobamos todos sus posibles triggers
                    for trigger in intent.get('triggers', []):
                        # Usamos token_set_ratio que es bueno para ignorar el orden de las palabras
                        # y palabras comunes. Ej: "pon la radio teo" vs "teo radio pon"
                        score = fuzz.token_set_ratio(command_lower, trigger)
                        if score > best_match_score:
                            best_match_score = score
                            best_intent = intent
                
                # Si la mejor coincidencia supera nuestro umbral de confianza, la aceptamos
                CONFIDENCE_THRESHOLD = 85 # Umbral de confianza (85%)
                if best_match_score >= CONFIDENCE_THRESHOLD:
                    app_logger.info(f"Intención encontrada con FuzzyMatch: '{best_intent['name']}' (Confianza: {best_match_score}%)")
                    response = random.choice(best_intent['responses'])
                    params = best_intent.get('parameters', {})
                    self.consecutive_failures = 0
                    self.execute_action(best_intent.get('action'), command_lower, params, response)
                    return
                else:
                    app_logger.warning(f"Ninguna intención superó el umbral de confianza. Mejor coincidencia: '{best_intent.get('name', 'Ninguna')}' con {best_match_score}%")
            else:
                # --- Lógica original si thefuzz no está disponible ---
                for trigger in sorted(self.intent_map.keys(), key=len, reverse=True):
                    if trigger in command_lower:
                        # --- CÓDIGO CORREGIDO: Añadir la lógica de búsqueda exacta ---
                        intent = self.intent_map[trigger]
                        app_logger.info(f"Intención encontrada con Búsqueda Exacta: '{intent['name']}'")
                        response = random.choice(intent['responses'])
                        params = intent.get('parameters', {})
                        self.consecutive_failures = 0  # Resetear contador de fallos
                        self.execute_action(intent.get('action'), command_lower, params, response)
                        return
            
            # --- Manejo de fallos si no se encuentra ninguna intención ---
            self.consecutive_failures += 1
            self.handle_unrecognized_command()

        finally:
            # --- SOLUCIÓN: Liberar el bloqueo SIEMPRE, a menos que se haya enviado una acción de 'speak' ---
            # Si se envió una acción de 'speak', el bloqueo se liberará cuando el altavoz termine.
            # Si no se envió (como en el 3er fallo), se libera aquí para evitar el bloqueo.
            # Comprobamos si la cola de UI está vacía o si la última acción no fue 'speak'.
            # Una forma más simple es simplemente liberarlo si el altavoz no está ocupado.
            if not self.speaker.is_busy:
                self.is_processing_command = False
                # Si el altavoz está ocupado, el 'speaker_status' se encargará de liberar el bloqueo.

    def handle_unrecognized_command(self):
        """Gestiona la respuesta cuando un comando no es reconocido."""
        if self.consecutive_failures == 1:
            self.ui_queue.put({'type': 'speak', 'text': "No he entendido esa orden."})
        elif self.consecutive_failures == 2:
            self.ui_queue.put({'type': 'speak', 'text': "Sigo sin entender, ¿puedes repetirlo de otra forma?"})
        else:
            app_logger.warning("Tercer fallo de reconocimiento consecutivo. El asistente permanecerá en silencio pero seguirá escuchando.")
            # No se envía acción de 'speak', por lo que el bloqueo debe liberarse manualmente.
            # El bloque 'finally' en handle_voice_command se encargará de esto.
            if self.frames.get("MainView"):
                self.frames["MainView"].update_status("No te he entendido. Inténtalo de nuevo.")

    def execute_action(self, name, cmd, params, resp):
        action_map = {
            "responder_simple": self.action_responder_simple,
            "accion_apagar": self.action_apagar,
            "mostrar_vista": self.action_mostrar_vista,
            "consultar_pastillero": self.action_consultar_pastillero,
            "consultar_pastillero_dia": self.action_consultar_pastillero_dia,
            "consultar_citas": self.action_consultar_citas,
            "decir_hora_actual": self.action_decir_hora_fecha,
            "decir_fecha_actual": self.action_decir_hora_fecha,
            "llamar_contacto_dinamico": self.action_llamar_contacto,
            "accion_sos": self.action_sos,
            "mostrar_vista_pastillero": self.action_mostrar_vista_pastillero,
            "controlar_radio": self.action_controlar_radio,
            "detener_radio": self.action_detener_radio, "cerrar_vista_emergencia": self.action_cerrar_emergencia,
            "registrar_llamada_completada": self.action_registrar_llamada, "crear_recordatorio_voz": self.action_crear_recordatorio_voz, "crear_alarma_voz": self.action_crear_alarma_voz, "consultar_recordatorios_dia": self.action_consultar_recordatorios_dia, "consultar_alarmas": self.action_consultar_alarmas, "iniciar_dialogo_temporizador": self.action_iniciar_dialogo_temporizador, "consultar_temporizador": self.action_consultar_temporizador, "crear_temporizador_directo": self.action_crear_temporizador_directo,
            "iniciar_dialogo_pastilla": self.action_iniciar_dialogo_pastilla,
            "contar_chiste": self.action_contar_contenido_aleatorio, "decir_frase_celebre": self.action_decir_frase_celebre,
            "contar_dato_curioso": self.action_contar_contenido_aleatorio, "decir_frase_celebre": self.action_decir_frase_celebre,
            "decir_dia_semana": self.action_decir_dia_semana,
            "mostrar_ayuda": self.show_help_window
        }
        if name in action_map:
            action_map[name](command=cmd, params=params, response=resp)
        else:
            app_logger.warning(f"Acción '{name}' no definida.")
            self.is_processing_command = False # Liberar bloqueo si la acción no existe

    def save_health_data(self, new_data):
        """Guarda los datos de salud en el fichero JSON y actualiza el estado interno."""
        try:
            with open('jsons/datos_emergencia.json', 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            self.datos_emergencia = new_data # Actualizar los datos en memoria
            app_logger.info("Datos de salud actualizados correctamente.")
            return True
        except Exception as e:
            app_logger.error(f"Error al guardar los datos de salud: {e}")
            return False
    def action_toggle_fall_detection(self, enabled):
        """Activa o desactiva la detección de caídas en el sensor de vídeo."""
        if self.video_sensor:
            self.video_sensor.toggle_fall_detection(enabled)
            self.speaker.speak(f"Detección de caídas {'activada' if enabled else 'desactivada'}")

    def action_detener_radio(self, response, **kwargs):
        """Detiene la reproducción de la radio y da respuesta por voz."""
        if hasattr(self, 'player') and self.player:
            self.player.stop()
        self.ui_queue.put({'type': 'speak', 'text': response})

    def action_controlar_radio(self, command, params, response, **kwargs):
        """Acción para controlar la radio: muestra un selector y reproduce la emisora elegida."""
        self.ui_queue.put({'type': 'speak', 'text': response})
        emisoras = self.radios if isinstance(self.radios, list) else self.radios.get('emisoras', [])
        if not emisoras:
            messagebox.showerror("Radio", "No se encontraron emisoras en radios.json")
            return
        # Crear ventana de selección
        selector = tk.Toplevel(self)
        selector.title("Selecciona una emisora de radio")
        selector.geometry("400x300")
        selector.configure(bg=COLOR_PRIMARY_BG)
        tk.Label(selector, text="Elige una emisora:", font=("Helvetica", 14, "bold"), bg=COLOR_PRIMARY_BG).pack(pady=10)
        emisora_var = tk.StringVar(value=emisoras[0]['nombre'])
        for emisora in emisoras:
            tk.Radiobutton(selector, text=emisora['nombre'].capitalize(), variable=emisora_var, value=emisora['nombre'], font=("Helvetica", 12), bg=COLOR_PRIMARY_BG).pack(anchor="w", padx=30)
        def reproducir():
            nombre = emisora_var.get()
            url = next((e['url'] for e in emisoras if e['nombre'] == nombre), None)
            if url and self.player:
                self.player.stop()
                media = self.vlc_instance.media_new(url)
                self.player.set_media(media)
                self.player.play()
                self.ui_queue.put({'type': 'speak', 'text': f"Reproduciendo {nombre}"})
            else:
                messagebox.showerror("Radio", "No se pudo reproducir la emisora seleccionada.")
            selector.destroy()
        tk.Button(selector, text="Reproducir", command=reproducir, font=("Helvetica", 12, "bold"), bg=COLOR_BUTTON_NORMAL).pack(pady=20)
        selector.transient(self)
        selector.grab_set()

    def action_responder_simple(self, response, **kwargs):
            self.ui_queue.put({'type': 'speak', 'text': response})

    def action_apagar(self, response, **kwargs):
            self.ui_queue.put({'type': 'speak', 'text': response})
            self.after(2000, self.on_closing)

    def action_mostrar_vista(self, params, response, **kwargs):
            if params.get("vista") in self.frames:
                self.ui_queue.put({'type': 'speak', 'text': response})
                self.show_frame(params["vista"])

    def action_mostrar_vista_pastillero(self, response, **kwargs):
            """Responde y abre la vista del pastillero."""
            self.ui_queue.put({'type': 'speak', 'text': response})
            self.show_frame("PillboxView")

    def action_consultar_pastillero(self, response, **kwargs):
            info = self.pill_manager.get_todays_pills_summary()
            self.ui_queue.put({'type': 'speak', 'text': response + (info or " Hoy no tienes pastillas.")})

    def action_consultar_pastillero_dia(self, command, response, **kwargs):
        """Consulta las pastillas para un día específico de la semana."""
        dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        dia_encontrado = None
        palabras = command.split()
        for palabra in palabras:
            if palabra in dias_semana:
                dia_encontrado = palabra
                break
        
        if dia_encontrado:
            info = self.pill_manager.get_pills_summary_for_day(dia_encontrado)
            self.ui_queue.put({'type': 'speak', 'text': response + " " + info})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "No he entendido a qué día te refieres. Prueba a decir, por ejemplo, 'qué pastillas tocan el lunes'."})

    def action_crear_recordatorio_voz(self, command, response, **kwargs):
        """Parsea un comando de voz para crear un evento en el calendario."""
        # Limpiar el comando de los triggers iniciales
        for trigger in ["recuérdame que", "recuerdame que", "recuérdame el", "recuerdame el", "añade un recordatorio"]:
            if command.startswith(trigger):
                reminder_text = command[len(trigger):].strip()
                break
        else:
            reminder_text = command

        parsed_data = parse_reminder_from_text(reminder_text)

        if not parsed_data:
            self.ui_queue.put({'type': 'speak', 'text': "No he podido entender la descripción del recordatorio. ¿Puedes intentarlo de nuevo?"})
            return

        # --- MEJORA: Lógica de diálogo para confirmación y fechas faltantes ---
        if parsed_data.get("status") == "needs_date":
            # El usuario no dijo una fecha, así que la pedimos.
            self.waiting_for_reminder_date = True
            self.pending_reminder_description = parsed_data['description']
            self.ui_queue.put({'type': 'speak', 'text': f"Claro, ¿para cuándo quieres que te recuerde '{self.pending_reminder_description}'?"})
        else:
            # Tenemos todos los datos, ahora pedimos confirmación.
            self.pending_reminder_data = parsed_data
            self.waiting_for_reminder_confirmation = True
            
            # Si la hora fue inferida, la ponemos a las 9 AM por defecto.
            if parsed_data.get("time_inferred", False):
                self.pending_reminder_data["time"] = "09:00"
                feedback_hora = "a las 9 de la mañana"
            else:
                feedback_hora = f"a las {parsed_data['time']}"

            confirm_text = f"He entendido: recordatorio para {parsed_data['description']} el día {parsed_data['date']} {feedback_hora}. ¿Es correcto?"
            self.ui_queue.put({'type': 'speak', 'text': confirm_text})

    def handle_reminder_confirmation(self, command_text):
        """Gestiona la respuesta de confirmación del usuario para un recordatorio."""
        self.waiting_for_reminder_confirmation = False # Salir del estado de espera
        
        if 'sí' in command_text.lower() or 'si' in command_text.lower() or 'correcto' in command_text.lower():
            data = self.pending_reminder_data
            year, month, day = map(int, data['date'].split('-'))
            hour, minute = map(int, data['time'].split(':'))
            self.calendar_manager.add_event(year, month, day, hour, minute, data['description'])
            self.ui_queue.put({'type': 'speak', 'text': "¡Perfecto! Recordatorio guardado."})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "De acuerdo, he cancelado el recordatorio."})
        
        self.pending_reminder_data = None

    def handle_reminder_date_response(self, command_text):
        """Procesa la fecha que el usuario da en el segundo paso del diálogo."""
        self.waiting_for_reminder_date = False
        full_command = f"{self.pending_reminder_description} {command_text}"
        self.pending_reminder_description = None
        # Volvemos a llamar a la acción principal, pero ahora con la frase completa
        self.action_crear_recordatorio_voz(command=full_command, response="De acuerdo, anotado:")
        
    def action_crear_alarma_voz(self, command, response, **kwargs):
        """Parsea un comando de voz para crear una alarma recurrente."""
        parsed_data = parse_alarm_from_text(command)
    
        if parsed_data:
            # --- MEJORA: Pedir confirmación antes de guardar ---
            self.pending_alarm_data = parsed_data
            self.waiting_for_alarm_confirmation = True
    
            hour, minute = parsed_data['time']
            days = parsed_data['days']
            
            days_str_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
            if len(days) == 7 or not days: # Si no se especifican días, es para todos
                days_text = "todos los días"
            else:
                days_text = "los " + ", ".join([days_str_map[d] for d in sorted(days)])
            
            confirm_text = f"Entendido. Voy a programar una alarma para las {hour:02d}:{minute:02d} {days_text}. ¿Es correcto?"
            self.ui_queue.put({'type': 'speak', 'text': confirm_text})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "No he podido entender la hora de la alarma. Por favor, inténtalo de nuevo."})

    def handle_alarm_confirmation(self, command_text):
        """Gestiona la respuesta de confirmación del usuario para una alarma."""
        self.waiting_for_alarm_confirmation = False # Salir del estado de espera

        if 'sí' in command_text.lower() or 'si' in command_text.lower() or 'correcto' in command_text.lower():
            data = self.pending_alarm_data
            hour, minute = data['time']
            self.alarm_manager.add_alarm(hour, minute, data['days'], data['label'])
            self.ui_queue.put({'type': 'speak', 'text': "¡Hecho! Alarma guardada."})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "De acuerdo, he cancelado la alarma."})
        
        self.pending_alarm_data = None

    def action_consultar_alarmas(self, response, **kwargs):
        """Consulta las alarmas programadas y las lee en voz alta."""
        summary = self.alarm_manager.get_alarms_summary()
        self.ui_queue.put({'type': 'speak', 'text': response + " " + summary})

    def action_consultar_temporizador(self, response, **kwargs):
        """Consulta el estado del temporizador activo y lo comunica."""
        if self.active_timer_end_time:
            remaining_time = self.active_timer_end_time - datetime.now()
            if remaining_time.total_seconds() > 0:
                minutes, seconds = divmod(int(remaining_time.total_seconds()), 60)
                
                feedback = ""
                if minutes > 0:
                    feedback += f"Quedan {minutes} minutos"
                    if seconds > 0:
                        feedback += f" y {seconds} segundos."
                    else:
                        feedback += "."
                else:
                    feedback += f"Quedan menos de un minuto, concretamente {seconds} segundos."
                self.ui_queue.put({'type': 'speak', 'text': feedback})
            else:
                self.ui_queue.put({'type': 'speak', 'text': "El temporizador ya ha terminado."})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "No hay ningún temporizador activo en este momento."})

    def action_iniciar_dialogo_temporizador(self, response, **kwargs):
        """Inicia el diálogo para configurar un temporizador."""
        self.waiting_for_timer_duration = True
        self.ui_queue.put({'type': 'speak', 'text': response})

    def action_crear_temporizador_directo(self, command, response, **kwargs):
        """Crea un temporizador directamente desde un comando de una sola frase."""
        match = re.search(r'(\d+)', command)
        if match:
            minutes = int(match.group(1))
            if minutes > 0:
                self.active_timer_end_time = datetime.now() + timedelta(minutes=minutes)
                feedback = f"{response} Temporizador de {minutes} minutos iniciado."
                self.ui_queue.put({'type': 'speak', 'text': feedback})
            else:
                self.ui_queue.put({'type': 'speak', 'text': "No puedo poner un temporizador de cero minutos."})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "No he entendido la duración del temporizador."})

    def handle_timer_duration_response(self, command_text):
        """Procesa la respuesta del usuario con la duración del temporizador."""
        self.waiting_for_timer_duration = False # Salir del estado de espera
        match = re.search(r'(\d+)', command_text)
        if match:
            minutes = int(match.group(1))
            if minutes > 0:
                self.active_timer_end_time = datetime.now() + timedelta(minutes=minutes)
                feedback = f"Entendido, temporizador de {minutes} minutos iniciado."
                self.ui_queue.put({'type': 'speak', 'text': feedback})
            else:
                self.ui_queue.put({'type': 'speak', 'text': "No puedo poner un temporizador de cero minutos."})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "No he entendido la duración. Por favor, inténtalo de nuevo."})

    # --- NUEVO: Métodos para el diálogo de creación de pastillas ---
    def action_iniciar_dialogo_pastilla(self, response, **kwargs):
        """Inicia el diálogo para añadir una nueva pastilla."""
        self.waiting_for_pill_info = True
        self.pill_dialog_step = 'name'
        self.pill_creation_data = {} # Limpiar datos anteriores
        self.ui_queue.put({'type': 'speak', 'text': response})

    def handle_pill_creation_dialog(self, command_text):
        """Gestiona los pasos del diálogo para crear una pastilla."""
        if "cancelar" in command_text.lower():
            self.reset_pill_dialog()
            self.ui_queue.put({'type': 'speak', 'text': "De acuerdo, cancelando la creación de la pastilla."})
            return

        if self.pill_dialog_step == 'name':
            self.pill_creation_data['name'] = command_text.capitalize()
            self.pill_dialog_step = 'days'
            self.ui_queue.put({'type': 'speak', 'text': f"Entendido, {self.pill_creation_data['name']}. ¿Qué días de la semana la tienes que tomar?"})

        elif self.pill_dialog_step == 'days':
            parsed_days = self._parse_days_from_text(command_text)
            if not parsed_days:
                self.ui_queue.put({'type': 'speak', 'text': "No he entendido los días. Por favor, di algo como 'lunes, miércoles y viernes' o 'todos los días'."})
                return
            self.pill_creation_data['days'] = parsed_days
            self.pill_dialog_step = 'time'
            self.ui_queue.put({'type': 'speak', 'text': "¿Y a qué hora? Por ejemplo, a las 8 de la mañana o a las dos y media."})

        elif self.pill_dialog_step == 'time':
            parsed_time = parse_alarm_from_text(command_text) # Reutilizamos el parser de alarmas
            if not parsed_time or 'time' not in parsed_time:
                self.ui_queue.put({'type': 'speak', 'text': "No he entendido la hora. Por favor, di una hora clara como 'a las 9 y media'."})
                return
            hour, minute = parsed_time['time']
            self.pill_creation_data['time'] = f"{hour:02d}:{minute:02d}"
            self.pill_dialog_step = 'confirm'
            
            days_text = ", ".join(self.pill_creation_data['days'])
            confirm_text = f"Perfecto. Voy a añadir {self.pill_creation_data['name']} para los {days_text} a las {self.pill_creation_data['time']}. ¿Es correcto?"
            self.ui_queue.put({'type': 'speak', 'text': confirm_text})

        elif self.pill_dialog_step == 'confirm':
            if 'sí' in command_text.lower() or 'si' in command_text.lower() or 'correcto' in command_text.lower():
                # Guardar la pastilla
                name = self.pill_creation_data['name']
                time_slot = self.pill_creation_data['time']
                for day in self.pill_creation_data['days']:
                    self.pill_manager.add_pill(name, day, time_slot)
                self.ui_queue.put({'type': 'speak', 'text': "¡Hecho! La pastilla ha sido añadida a tu pastillero."})
            else:
                self.ui_queue.put({'type': 'speak', 'text': "De acuerdo, no guardaré los cambios. Puedes empezar de nuevo si quieres."})
            self.reset_pill_dialog()

    def _parse_days_from_text(self, text):
        """Función auxiliar para extraer días de la semana de un texto."""
        text = text.lower()
        day_map = {"lunes": "Lunes", "martes": "Martes", "miércoles": "Miércoles", "jueves": "Jueves", "viernes": "Viernes", "sábado": "Sábado", "domingo": "Domingo"}
        found_days = []
        if "todos los días" in text or "cada día" in text:
            return list(day_map.values())
        for key, value in day_map.items():
            if key in text:
                found_days.append(value)
        return found_days

    def reset_pill_dialog(self):
        """Resetea el estado del diálogo de creación de pastillas."""
        self.waiting_for_pill_info = False
        self.pill_dialog_step = None
        self.pill_creation_data = {}

    def action_consultar_recordatorios_dia(self, command, response, **kwargs):
        """Consulta los recordatorios para un día específico de la semana."""
        dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo", "hoy"]
        dia_encontrado = None
        palabras = command.split()
        for palabra in palabras:
            if palabra in dias_semana:
                dia_encontrado = palabra
                break
        
        if dia_encontrado:
            if dia_encontrado == "hoy":
                today_weekday = datetime.now().weekday()
                day_map_es = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
                dia_encontrado = day_map_es[today_weekday].lower()
            info = self.calendar_manager.get_events_summary_for_day(dia_encontrado)
            self.ui_queue.put({'type': 'speak', 'text': response + " " + info})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "No he entendido a qué día te refieres. Prueba a decir, por ejemplo, 'qué recordatorios tengo para el lunes'."})
    def action_registrar_llamada(self, command, response, **kwargs):
        """Registra que se ha hablado con un contacto para reiniciar el contador de inactividad social."""
        contacto_encontrado = None
        for contacto in self.contact_manager.get_all_contacts():
            # Buscamos el nombre del contacto en el comando de voz
            if contacto['nombre'].split()[0].lower() in command:
                contacto_encontrado = contacto
                break
        
        if contacto_encontrado:
            self.contact_manager.update_last_contact(contacto_encontrado['nombre'])
            self.ui_queue.put({'type': 'speak', 'text': response})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "Perdona, no he entendido con quién has hablado."})
    def action_consultar_citas(self, response, **kwargs):
            full_response = response
            self.ui_queue.put({'type': 'speak', 'text': full_response})

    def action_consultar_tiempo(self, response, **kwargs):
            full_response = response + f" En Albacete, actualmente son las {datetime.now().strftime('%H:%M')}, hay cielos despejados y una temperatura agradable."
            self.ui_queue.put({'type': 'speak', 'text': full_response})

    def action_decir_hora_fecha(self, command, response, **kwargs):
            if "hora" in command:
                full_response = response + datetime.now().strftime('%H y %M')
            else: # Si es fecha
                full_response = response + datetime.now().strftime('%A, %d de %B de %Y')
            self.ui_queue.put({'type': 'speak', 'text': full_response})

    def action_decir_dia_semana(self, response, **kwargs):
            """Responde con el día de la semana actual."""
            # strftime('%A') devuelve el nombre completo del día de la semana según la localización.
            dia_semana = datetime.now().strftime('%A').capitalize()
            self.ui_queue.put({'type': 'speak', 'text': f"{response} {dia_semana}."})

    def action_llamar_contacto(self, command, response, **kwargs):
            palabras = command.split()
            try:
                indice_a = palabras.index("a")
                contacto = palabras[indice_a + 1].capitalize()
            except (ValueError, IndexError):
                contacto = "tu contacto"

            full_response = response + f" {contacto}"
            self.ui_queue.put({'type': 'speak', 'text': full_response})
            messagebox.showinfo("Acción", f"Simulando llamada a {contacto}")

    def action_sos(self, response, **kwargs):
            self.ui_queue.put({'type': 'speak', 'text': response})
            if not self.datos_emergencia:
                messagebox.showerror("Error Crítico", "No se pudieron cargar los datos de emergencia.")
                return
            # Guardar la instancia para poder cerrarla por voz
            if self.emergency_view_instance and self.emergency_view_instance.winfo_exists():
                self.emergency_view_instance.lift()
            else:
                # --- MEJORA: Pasar el controlador principal a la vista de emergencia ---
                # Esto permite que la vista de emergencia se cierre a sí misma
                # y notifique al controlador principal.
                self.emergency_view_instance = EmergencyView(self, self.datos_emergencia)

    def action_cerrar_emergencia(self, response, **kwargs):
        """Cierra la ventana de emergencia si está abierta."""
        self.ui_queue.put({'type': 'speak', 'text': response})
        if self.emergency_view_instance and self.emergency_view_instance.winfo_exists():
            # --- MEJORA: Llamar a un método de cierre seguro en la propia ventana ---
            self.emergency_view_instance.safe_close()
    
    def handle_fall_detection(self):
        """Inicia el protocolo de pregunta tras una caída."""
        if self.waiting_for_fall_response: return # Ya hay un proceso en curso
        logging.warning("Caída detectada. Iniciando protocolo de confirmación.")
        self.waiting_for_fall_response = True
        self.ui_queue.put({'type': 'speak', 'text': "¿Estás bien?"})
        # Iniciar un temporizador de 10 segundos. Si no hay respuesta, se activa la emergencia.
        self.fall_response_timer = self.after(10000, self.trigger_emergency_protocol)

    def handle_fall_response(self, command_text):
        """Procesa la respuesta del usuario a la pregunta de caída."""
        command_lower = command_text.lower()
        # Cancelar el temporizador porque el usuario ha respondido
        if self.fall_response_timer:
            self.after_cancel(self.fall_response_timer)
            self.fall_response_timer = None

        if "sí" in command_lower or "si" in command_lower:
            app_logger.info("El usuario ha respondido 'SÍ' a la alerta de caída. Cancelando.")
            self.ui_queue.put({'type': 'speak', 'text': "De acuerdo, cancelando alerta."})
        else: # Si dice "no" o cualquier otra cosa, se asume emergencia
            app_logger.warning("El usuario ha respondido 'NO' o una respuesta no afirmativa. Activando emergencia.")
            self.trigger_emergency_protocol()
        self.waiting_for_fall_response = False

    def trigger_emergency_protocol(self):
        """Activa el protocolo de emergencia completo."""
        self.action_sos(response="Entendido. Iniciando protocolo de emergencia AHORA.")
        # --- NUEVAS FUNCIONES GENÉRICAS PARA CONTENIDO EXTERNO ---
    def action_contar_contenido_aleatorio(self, response, **kwargs):
            """Función genérica para chistes y datos curiosos."""
            lista_contenido = []
            if kwargs['params']['fichero'] == 'chistes.json':
                lista_contenido = self.chistes
            elif kwargs['params']['fichero'] == 'datos_curiosos.json':
                lista_contenido = self.datos_curiosos

            if lista_contenido:
                contenido = random.choice(lista_contenido)
                full_response = response + " " + contenido
                self.ui_queue.put({'type': 'speak', 'text': full_response})
            else:
                self.ui_queue.put({'type': 'speak', 'text': "Vaya, parece que me he quedado sin ideas."})

    def action_decir_frase_celebre(self, response, **kwargs):
        if self.frases_celebres:
            frase_obj = random.choice(self.frases_celebres)
            frase_completa = f"{frase_obj['texto']} Dicho por {frase_obj['autor']}."
            full_response = response + " " + frase_completa
            self.ui_queue.put({'type': 'speak', 'text': full_response})
        else:
            self.ui_queue.put({'type': 'speak', 'text': "Ahora mismo no me viene ninguna frase a la mente."})
            
            
    def show_help_window(self, **kwargs):
        """Crea y muestra una ventana Toplevel con los comandos de voz disponibles."""
        help_win = tk.Toplevel(self)
        help_win.title("Ayuda - Comandos de Voz")
        help_win.geometry("750x550")
        help_win.configure(bg=COLOR_PRIMARY_BG)
        help_win.transient(self)
        help_win.grab_set()

        header = tk.Frame(help_win, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        title_label = tk.Label(header, text="Comandos que puedes usar", font=("Helvetica", 16, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack()

        text_frame = tk.Frame(help_win, bg=COLOR_PRIMARY_BG, padx=10, pady=10)
        text_frame.pack(fill="both", expand=True)

        text_widget = tk.Text(text_frame, wrap="word", font=("Helvetica", 12), bg=COLOR_TEXT_LIGHT, relief="flat")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        text_widget.pack(side="left", fill="both", expand=True)

        # Configurar tags para el formato del texto
        text_widget.tag_configure("category", font=("Helvetica", 14, "bold"), foreground=COLOR_BUTTON_FOCUS, spacing1=10, spacing3=5)
        text_widget.tag_configure("command", lmargin1=20, lmargin2=20, spacing1=2)

        if self.intents:
            for intent in self.intents:
                category = intent.get('name', 'Desconocido').split('_')[0].capitalize()
                trigger_example = intent.get('triggers', [''])[0]
                text_widget.insert(tk.END, f"{category}: '{trigger_example}...'\n", "category")

        text_widget.config(state="disabled") # Hacer el texto no editable
        
    def set_display_brightness(self, level):
        """Ajusta el brillo de la pantalla DSI (0.0 a 1.0)."""

        DSI_BRIGHTNESS_FILE = "/sys/class/backlight/10-0045/backlight"
        try:
            # Convertir el nivel (0.0-1.0) a un valor entero entre 0-255
            value = int(level * 255)
            if value < 0: value = 0
            if value > 255: value = 255

            with open(DSI_BRIGHTNESS_FILE, "w") as f:
                f.write(str(value))
            app_logger.info(f"Brillo de la pantalla DSI ajustado a {value} ({level*100:.0f}%)")

        except FileNotFoundError:
            app_logger.warning("No se encontró el control de brillo de la pantalla DSI. ¿Estás usando la pantalla oficial?")
        except PermissionError:
            app_logger.error(f"Error de permisos al ajustar el brillo. Asegúrate de haber ejecutado 'sudo chmod 666 {DSI_BRIGHTNESS_FILE}'")
        except Exception as e:
            app_logger.error(f"Error inesperado al ajustar el brillo: {e}")

    def get_cpu_temperature(self):
        """Lee la temperatura de la CPU del sistema."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().strip()) / 1000
                return f"{temp:.1f} °C"
        except Exception:
            return "No disponible"

    def check_internet_connection(self):
        """Comprueba si hay conexión a Internet."""
        try:
            # Intenta resolver un nombre de dominio conocido
            subprocess.check_output(["ping", "-c", "1", "8.8.8.8"], stderr=subprocess.STDOUT)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_system_usage(self):
        if psutil:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            return f"{cpu}%", f"{ram}%"
        return "N/D", "N/D"
    def get_ip_address(self):
        """Obtiene la dirección IP local del dispositivo."""
        try:
            # Conectar a un host externo (no necesita ser alcanzable) para obtener la IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "No disponible"

class MainView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller
        self.icons = self.load_icons()
        self.setup_styles() # Llama al método de la clase
        self.create_layout()

    def setup_styles(self):
        # Estilo para las pestañas del Notebook
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Helvetica", 12, "bold"), padding=[10, 5])
        style.configure("TNotebook", background=COLOR_PRIMARY_BG)

        style = ttk.Style()
        # Estilo para botones con imagen y texto
        style.configure("ImageText.TButton", 
                        font=("Helvetica", 12, "bold"), 
                        padding=10,
                        background=COLOR_BUTTON_NORMAL,
                        foreground=COLOR_TEXT_DARK)
        style.map("ImageText.TButton", background=[('active', COLOR_BUTTON_HOVER)])
        
        # Estilo para el botón de voz
        style.configure("Grid.TButton", padding=5)
        
        # Estilo para el botón SOS
        style.configure("SOS.TButton", 
                        font=("Helvetica", 12, "bold"), 
                        padding=10, 
                        background=COLOR_ERROR_RED, 
                        foreground=COLOR_TEXT_LIGHT)
        style.map("SOS.TButton", background=[('active', COLOR_ERROR_RED_HOVER)])

    def create_layout(self):
        """Crea y organiza el layout completo de la MainView."""
        # Indicador de estado de la cámara
        self.camera_status_indicator = tk.Label(self, text="●", font=("Helvetica", 20), bg=COLOR_PRIMARY_BG, fg="gray")
        self.camera_status_indicator.place(relx=0.98, rely=0.02, anchor='ne')
        # --- Configurar una única cuadrícula de 4x3 para toda la vista ---
        for i in range(4): self.grid_columnconfigure(i, weight=1)
        for i in range(3): self.grid_rowconfigure(i, weight=1)

        # --- Botones ---
        buttons = {
            "Calendario": "CalendarView",
            "Pastillero": "PillboxView",
            "Llamar a Ana": "call_ana",
            "Alarmas": "AlarmView",
            "Ayuda": "mostrar_ayuda",
            "Recordatorios": "show_reminders", "Salir": "exit_app", 
            "Ver Logs": "LogView"
        }

        # --- Colocar los 8 botones principales en la primera y última fila ---
        button_items = list(buttons.items())
        num_buttons = len(button_items)
        for i in range(4):
            # Fila superior
            if i < num_buttons:
                text, command_name = button_items[i]
                self.create_button_widget(self, text, command_name).grid(row=0, column=i, padx=15, pady=15, sticky="nsew")
            # Fila inferior
            if i + 4 < num_buttons:
                text, command_name = button_items[i+4]
                self.create_button_widget(self, text, command_name).grid(row=2, column=i, padx=15, pady=15, sticky="nsew")

        # --- Colocar los elementos centrales en la segunda fila ---
        self.create_button_widget(self, "Ajustes", "SettingsView").grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
        self.create_button_widget(self, "SOS", "sos_action").grid(row=1, column=3, padx=15, pady=15, sticky="nsew")

        # Reloj y Fecha en el centro
        datetime_frame = tk.Frame(self, bg=COLOR_PRIMARY_BG)
        datetime_frame.grid(row=1, column=1, columnspan=2, sticky="nsew")

        self.clock_label = tk.Label(datetime_frame, text="", font=("Helvetica", 48, "bold"), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
        self.clock_label.pack(expand=True, anchor='s', pady=(10,0))

        self.date_label = tk.Label(datetime_frame, text="", font=("Helvetica", 28), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
        self.date_label.pack(expand=True, anchor='n')

        # --- NUEVO: Hacer que el reloj sea clicable ---
        datetime_frame.config(cursor="hand2")
        datetime_frame.bind("<Button-1>", self.open_clock_timer_window)
        self.clock_label.bind("<Button-1>", self.open_clock_timer_window)
        self.date_label.bind("<Button-1>", self.open_clock_timer_window)

        # --- ETIQUETA DE ESTADO (sin botón de micrófono) ---
        self.status_label = tk.Label(datetime_frame, text="", font=("Helvetica", 11, "italic"), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
        self.status_label.pack(side="bottom", pady=5)

        self.update_datetime() # Iniciar el reloj

    def create_button_widget(self, parent, text, command_name):
        """Crea un widget de botón personalizado: imagen si hay icono, texto si no."""
        bg_color = COLOR_ERROR_RED if text == "SOS" else COLOR_BUTTON_NORMAL
        button_frame = tk.Frame(parent, bg=bg_color, cursor="hand2")
        icon = self.icons.get(text)
        # Solo mostrar imagen si es un objeto PhotoImage válido
        if icon is not None and hasattr(icon, 'width') and icon.width() > 0:
            icon_label = tk.Label(button_frame, image=icon, bg=bg_color)
            icon_label.pack(expand=True, padx=10, pady=10)
            icon_label.image = icon
        else:
            fg_color = COLOR_TEXT_LIGHT if text == "SOS" else COLOR_TEXT_DARK
            text_label = tk.Label(button_frame, text=text, font=("Helvetica", 11, "bold"), bg=bg_color, fg=fg_color)
            text_label.pack(expand=True, padx=10, pady=10)
        if command_name == "sos_action":
            cmd = lambda: self.controller.action_sos(response="Protocolo de emergencia activado.")
        elif command_name == "exit_app":
            cmd = self.controller.on_closing
        elif "View" in command_name:
            cmd = lambda c=command_name: self.controller.show_frame(c)
        elif command_name == "mostrar_ayuda":
            cmd = self.controller.show_help_window
        else:
            cmd = lambda t=text: messagebox.showinfo("Acción", f"Acción '{t}' no implementada.")
        button_frame.bind("<Button-1>", lambda e, c=cmd: c())
        for widget in button_frame.winfo_children():
            widget.bind("<Button-1>", lambda e, c=cmd: c())
        return button_frame
    
    def update_status(self, text):
            self.status_label.config(text=text)
    
    def update_datetime(self):
        """Actualiza el reloj y la fecha cada segundo."""
        now = datetime.now()
        date_str = now.strftime("%A, %d de %B").capitalize()
        time_str = now.strftime("%H:%M:%S")
        self.date_label.config(text=date_str)
        self.clock_label.config(text=time_str)
        self.after(1000, self.update_datetime)

    def update_camera_status(self, status):
        """Actualiza el color del indicador de la cámara."""
        if status == 'connected':
            self.camera_status_indicator.config(fg="green")
        else:
            self.camera_status_indicator.config(fg="red")

    def open_clock_timer_window(self, event=None):
        """Abre la ventana del reloj grande y el temporizador."""
        ClockTimerView(self.controller)

    def load_icons(self):
        """Carga los iconos desde la carpeta 'static/iconos'."""
        icons = {}
        icon_path = "static/iconos"
        if not os.path.exists(icon_path) or not Image:
            return {}
        # Mapeo de nombres de botón a archivo de icono
        nombre_archivo = {
            "Calendario": "calendar.png",
            "Pastillero": "pills.png",
            "Llamar a Ana": "phone.png",
            "Alarmas": "alarmas.png", # Asegúrate de tener un icono 'alarm.png' en static/iconos
            "Ayuda": "help.png",
            "Recordatorios": "reminders.png",
            "Salir": "exit.png",
            "Ver Logs": "logs.png",
            "Ajustes": "st.png",
            "SOS": "sos.png"
        }
        for name, filename in nombre_archivo.items():
            try:
                icons[name] = ImageTk.PhotoImage(Image.open(os.path.join(icon_path, filename)).resize((80, 80), Image.Resampling.LANCZOS))
            except Exception as e:
                app_logger.warning(f"No se pudo cargar el icono '{filename}' para '{name}': {e}")
        return icons
            
class CalendarView(tk.Frame):
    """Vista del Calendario."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller
        self.current_date = date.today()
        self.events = {}

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("MainView"))
        back_button.pack(side="left", padx=10)

        self.month_year_label = tk.Label(header, text="", font=("Helvetica", 18, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        self.month_year_label.pack(side="left", expand=True)

        # --- Controles de Navegación ---
        controls_frame = tk.Frame(self, bg=COLOR_PRIMARY_BG, pady=10)
        controls_frame.pack(fill="x")
        prev_button = ttk.Button(controls_frame, text="< Mes Anterior", command=self.prev_month)
        prev_button.pack(side="left", padx=20)
        next_button = ttk.Button(controls_frame, text="Mes Siguiente >", command=self.next_month)
        next_button.pack(side="right", padx=20)

        # --- Contenedor del Grid del Calendario ---
        self.calendar_frame = tk.Frame(self, bg=COLOR_PRIMARY_BG)
        self.calendar_frame.pack(expand=True, fill="both", padx=10, pady=10)

    def on_show(self):
        """Este método se llama cuando el frame se hace visible."""
        self.render_calendar()

    def render_calendar(self):
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()

        year, month = self.current_date.year, self.current_date.month
        self.month_year_label.config(text=f"{datetime(year, month, 1).strftime('%B %Y').capitalize()}")
        
        # Lógica de eventos simplificada (solo pastillas)
        self.events = {}
        pill_schedule = self.controller.pill_manager.load_schedule()
        day_map_es = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
        num_days_in_month = (date(year, month + 1, 1) - date(year, month, 1)).days if month < 12 else 31

        for day_num in range(1, num_days_in_month + 1):
            day_name_es = day_map_es[date(year, month, day_num).weekday()]
            day_str = str(day_num)
            if day_name_es in pill_schedule.get('pastillas', {}):
                day_pills = pill_schedule['pastillas'][day_name_es]
                for time_slot, pills in day_pills.items():
                    if pills:
                        self.events.setdefault(day_str, []).append(f"💊 {time_slot} - {', '.join(pills)}")

        days_of_week = ["L", "M", "X", "J", "V", "S", "D"]
        for i, day in enumerate(days_of_week):
            tk.Label(self.calendar_frame, text=day, font=("Helvetica", 12, "bold"), bg=COLOR_SECONDARY_BG, fg=COLOR_TEXT_DARK).grid(row=0, column=i, sticky="nsew", ipadx=10, ipady=5)
        
        today = date.today()
        first_day_of_month = date(year, month, 1).weekday()
        current_day = 1
        for r in range(1, 7):
            for c in range(7):
                if not (r == 1 and c < first_day_of_month) and current_day <= num_days_in_month:
                    day_frame = tk.Frame(self.calendar_frame, bg="white", highlightbackground=COLOR_SECONDARY_BG, highlightthickness=1)
                    day_frame.grid(row=r, column=c, sticky="nsew")
                    
                    is_today = (year == today.year and month == today.month and current_day == today.day)
                    day_bg = COLOR_BUTTON_NORMAL if is_today else "white"
                    day_fg = "white" if is_today else COLOR_TEXT_DARK
                    
                    day_label = tk.Label(day_frame, text=str(current_day), font=("Helvetica", 14, "bold" if is_today else "normal"), bg=day_bg, fg=day_fg)
                    day_label.pack(pady=5, expand=True)
                    
                    if str(current_day) in self.events:
                        tk.Label(day_frame, text="💊", font=("Helvetica", 10), bg=day_bg, fg=day_fg).pack(pady=(0,5))
                        day_frame.bind("<Button-1>", lambda e, d=current_day: self.show_day_events(d))
                        day_label.bind("<Button-1>", lambda e, d=current_day: self.show_day_events(d))
                    
                    current_day += 1

        for i in range(7): self.calendar_frame.grid_columnconfigure(i, weight=1)
        for i in range(7): self.calendar_frame.grid_rowconfigure(i, weight=1)

    def show_day_events(self, day):
        events_str = "\n".join(self.events.get(str(day), ["No hay eventos."]))
        messagebox.showinfo(f"Eventos del día {day}", events_str)

    def prev_month(self):
        year, month = self.current_date.year, self.current_date.month
        self.current_date = date(year - 1, 12, 1) if month == 1 else date(year, month - 1, 1)
        self.render_calendar()

    def next_month(self):
        year, month = self.current_date.year, self.current_date.month
        self.current_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        self.render_calendar()

class PillboxView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("MainView"))
        back_button.pack(side="left", padx=10)

        title_label = tk.Label(header, text="Pastillero Semanal", font=("Helvetica", 18, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)

        # Frame para los botones de acción
        action_frame = tk.Frame(header, bg=COLOR_HEADER_BG)
        action_frame.pack(side="right", padx=10)

        delete_button = ttk.Button(action_frame, text="Eliminar Pastilla", command=self.delete_pill_popup)
        delete_button.pack(side="right", padx=(5, 0))

        add_button = ttk.Button(action_frame, text="Añadir Pastilla", command=self.add_pill_popup)
        add_button.pack(side="left")
        
        # --- Estilo para Treeview ---
        style = ttk.Style()
        # Quitar bordes y aumentar altura de fila y tamaño de fuente
        style.configure("Custom.Treeview", background=COLOR_TEXT_LIGHT, fieldbackground=COLOR_TEXT_LIGHT, foreground=COLOR_TEXT_DARK, rowheight=45, font=('Helvetica', 12), borderwidth=0)
        style.configure("Custom.Treeview.Heading", background=COLOR_SECONDARY_BG, foreground=COLOR_TEXT_DARK, font=('Helvetica', 12, 'bold'))
        # Eliminar bordes del Treeview en sí
        style.layout("Custom.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})]) 

        # --- Tabla del Pastillero ---
        self.tree = ttk.Treeview(self, style="Custom.Treeview")
        # Usamos un frame para poder centrar la tabla si no ocupa todo el ancho
        tree_container = tk.Frame(self, bg=COLOR_PRIMARY_BG)
        tree_container.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        self.selected_cell = None # Para guardar la celda seleccionada (item_id, column_id)
        self.tree.bind("<Button-1>", self.on_tree_click)

        self.tree.pack(expand=True, fill='both') # La tabla se expande en ambas direcciones

    def render_pillbox(self):
        """Carga los datos del pastillero y los muestra en la tabla."""
        # Este método se llama desde on_show para asegurar que los datos están actualizados.

        # Limpiar tabla anterior
        for i in self.tree.get_children():
            self.tree.delete(i)

        schedule = self.controller.pill_manager.load_schedule()
        horarios = sorted(schedule.get('horarios', []))
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        pill_colors = schedule.get('colores', {})
        
        # --- Resaltar día actual ---
        today_name = date.today().strftime('%A').capitalize()
        day_map_es = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
        today_es = day_map_es.get(today_name)

        self.tree["columns"] = ["Hora"] + dias
        self.tree.heading("#0", text="", anchor="w")
        self.tree.column("#0", width=0, stretch=tk.NO)
        self.tree.heading("Hora", text="Hora", anchor="center")
        self.tree.column("Hora", anchor="center", width=100, stretch=tk.NO)

        # --- Configurar columnas y etiquetas de colores ---
        for dia in dias:
            self.tree.heading(dia, text=dia, anchor="center")
            self.tree.column(dia, anchor="center", width=120, stretch=tk.YES)
            # Resaltar la columna del día actual
            if dia == today_es:
                self.tree.tag_configure(f'col_{dia}', background=COLOR_PRIMARY_BG)
            else:
                self.tree.tag_configure(f'col_{dia}', background=COLOR_TEXT_LIGHT)

        # Crear un tag para cada pastilla con su color de fondo
        for pill_name, color in pill_colors.items():
            tag_name = f"pill_{pill_name.replace(' ', '_')}"
            self.tree.tag_configure(tag_name, background=color, foreground='white', font=('Helvetica', 11, 'bold'))

        # --- Llenar la tabla con los datos ---
        for hora in horarios:
            row_data = [hora]
            tags_for_row = []
            for dia in dias:
                pills = schedule.get('pastillas', {}).get(dia, {}).get(hora, [])
                row_data.append(", ".join(pills))
                
                # Aplicar tags: uno para el color de la columna y otro para la pastilla si solo hay una
                column_tag = f'col_{dia}'
                pill_tag = ''
                if len(pills) == 1:
                    pill_tag = f"pill_{pills[0].replace(' ', '_')}"
                tags_for_row.append((column_tag, pill_tag))

            item_id = self.tree.insert("", "end", values=row_data, tags=('row',)) # Tag base para la fila
            self.tree.item(item_id, tags=tags_for_row)

    def on_show(self):
        """Se llama cuando el frame se hace visible para recargar los datos."""
        self.render_pillbox()

    def on_tree_click(self, event):
        """Guarda la celda seleccionada por el usuario."""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column_id = self.tree.identify_column(event.x)
            item_id = self.tree.identify_row(event.y)
            self.selected_cell = (item_id, column_id)
            app_logger.info(f"Celda seleccionada: Fila={item_id}, Columna={column_id}")

    def delete_pill_popup(self):
        """Gestiona la eliminación de una pastilla de la celda seleccionada."""
        if not self.selected_cell:
            messagebox.showinfo("Acción Requerida", "Por favor, haz clic en la casilla de la pastilla que deseas eliminar primero.", parent=self)
            return

        item_id, column_id = self.selected_cell
        if not item_id or not column_id:
            return

        # Obtener datos de la celda
        try:
            column_index = int(column_id.replace('#', '')) - 1
            day = self.tree.heading(column_id)['text']
            time_slot = self.tree.item(item_id)['values'][0]
            pills_str = self.tree.item(item_id)['values'][column_index]
            pills = [p.strip() for p in pills_str.split(',') if p.strip()]
        except (IndexError, KeyError):
            messagebox.showerror("Error", "No se pudo identificar la celda seleccionada.", parent=self)
            return

        if not pills:
            messagebox.showinfo("Nada que hacer", "La casilla seleccionada está vacía.", parent=self)
            return

        pill_to_delete = None
        if len(pills) == 1:
            # Si solo hay una, preguntar directamente
            if messagebox.askyesno("Confirmar Eliminación", f"¿Seguro que quieres eliminar '{pills[0]}' del {day} a las {time_slot}?", parent=self):
                pill_to_delete = pills[0]
        else:
            # Si hay varias, mostrar un popup para elegir
            pill_to_delete = self.ask_which_pill_to_delete(pills)

        if pill_to_delete:
            if self.controller.pill_manager.delete_pill(pill_to_delete, day, time_slot):
                messagebox.showinfo("Éxito", f"'{pill_to_delete}' ha sido eliminada.", parent=self)
                self.render_pillbox() # Refrescar la vista
            else:
                messagebox.showerror("Error", "No se pudo eliminar la pastilla.", parent=self)
        
        self.selected_cell = None # Limpiar selección

    def ask_which_pill_to_delete(self, pills):
        """Abre un popup para que el usuario elija qué pastilla eliminar de una lista."""
        dialog = tk.Toplevel(self)
        dialog.title("Seleccionar Pastilla")
        dialog.geometry("350x250")
        dialog.configure(bg=COLOR_PRIMARY_BG)
        dialog.transient(self)
        dialog.grab_set()

        main_frame = tk.Frame(dialog, bg=COLOR_PRIMARY_BG, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text="Hay varias pastillas en esta casilla.", style="Popup.TLabel").pack(pady=(0, 5))
        ttk.Label(main_frame, text="¿Cuál quieres eliminar?", style="Popup.TLabel", font=("Helvetica", 12, "bold")).pack(pady=(0, 15))

        # Variable para guardar la selección
        selected_pill = tk.StringVar()

        # Crear un Radiobutton por cada pastilla
        for pill in pills:
            rb = ttk.Radiobutton(main_frame, text=pill, value=pill, variable=selected_pill, style="TRadiobutton")
            rb.pack(anchor="w", padx=20)

        result = {"pill": None}

        def on_confirm():
            if selected_pill.get():
                result["pill"] = selected_pill.get()
                dialog.destroy()
            else:
                messagebox.showwarning("Selección Requerida", "Debes seleccionar una pastilla.", parent=dialog)

        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))
        
        confirm_button = ttk.Button(button_frame, text="Eliminar", command=on_confirm, style="Grid.TButton")
        confirm_button.pack(side="right")
        cancel_button = ttk.Button(button_frame, text="Cancelar", command=dialog.destroy, style="Grid.TButton")
        cancel_button.pack(side="right", padx=(0, 10))

        self.wait_window(dialog) # Esperar a que el diálogo se cierre
        return result["pill"]

    def add_pill_popup(self):
        """Abre una ventana emergente (Toplevel) para añadir una nueva pastilla."""
        popup = tk.Toplevel(self)
        popup.title("Añadir Pastilla")
        popup.geometry("450x350")
        popup.configure(bg=COLOR_PRIMARY_BG)
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        style = ttk.Style(popup)
        style.configure("Popup.TLabel", background=COLOR_PRIMARY_BG, foreground=COLOR_TEXT_DARK, font=("Helvetica", 12))
        style.configure("Popup.TEntry", fieldbackground="white", font=("Helvetica", 12))
        style.configure("Popup.TMenubutton", font=("Helvetica", 12), background="white", padding=5)

        main_frame = tk.Frame(popup, bg=COLOR_PRIMARY_BG, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text="Añadir Nueva Pastilla", font=("Helvetica", 16, "bold"), style="Popup.TLabel").pack(pady=(0, 20))

        ttk.Label(main_frame, text="Nombre de la pastilla:", style="Popup.TLabel").pack(anchor="w")
        pill_name_entry = ttk.Entry(main_frame, style="Popup.TEntry")
        pill_name_entry.pack(fill="x", pady=(0, 10))
        pill_name_entry.focus_set()

        ttk.Label(main_frame, text="Día de la semana:", style="Popup.TLabel").pack(anchor="w")
        days_of_week = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        day_var = tk.StringVar(main_frame)
        day_var.set(days_of_week[0])
        day_menu = ttk.OptionMenu(main_frame, day_var, days_of_week[0], *days_of_week, style="Popup.TMenubutton")
        day_menu.pack(fill="x", pady=(0, 10))

        ttk.Label(main_frame, text="Hora (formato HH:MM):", style="Popup.TLabel").pack(anchor="w")
        time_slot_entry = ttk.Entry(main_frame, style="Popup.TEntry")
        time_slot_entry.pack(fill="x", pady=(0, 20))

        def on_submit():
            # ... (La lógica interna de on_submit no necesita cambios)
            pill_name = pill_name_entry.get().strip()
            day = day_var.get()
            time_slot = time_slot_entry.get().strip()

            if not pill_name or not day or not time_slot:
                messagebox.showerror("Error", "Todos los campos son obligatorios.", parent=popup)
                return
            
            try:
                datetime.strptime(time_slot, "%H:%M")
            except ValueError:
                messagebox.showerror("Error de Formato", "La hora debe tener el formato HH:MM (ej: 08:00).", parent=popup)
                return

            if self.controller.pill_manager.add_pill(pill_name, day, time_slot):
                messagebox.showinfo("Éxito", "Pastilla añadida correctamente.", parent=popup)
                self.render_pillbox()
                popup.destroy()
            else:
                messagebox.showerror("Error", "No se pudo añadir la pastilla.", parent=popup)

        # --- CORRECCIÓN AQUÍ ---
        # Usamos un tk.Frame normal y le damos el color de fondo correcto
        button_frame = tk.Frame(main_frame, bg=COLOR_PRIMARY_BG)
        button_frame.pack(fill="x", side="bottom")

        submit_button = ttk.Button(button_frame, text="Guardar", command=on_submit)
        submit_button.pack(side="right", padx=(10, 0))

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=popup.destroy)
        cancel_button.pack(side="right")

class LogView(tk.Frame):
    """Vista para mostrar los logs de la aplicación en tiempo real."""
    def __init__(self, parent, controller, log_queue):
        super().__init__(parent, bg=COLOR_LOG_BG)
        self.controller = controller
        self.log_queue = log_queue

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_LOG_HEADER, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("MainView"))
        back_button.pack(side="left", padx=10)

        title_label = tk.Label(header, text="Registro de Actividad", font=("Helvetica", 18, "bold"), bg=COLOR_LOG_HEADER, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)

        # --- Área de texto para los logs ---
        self.log_text = tk.Text(self, height=15, state='disabled', bg=COLOR_LOG_BG, fg=COLOR_LOG_TEXT, font=("Monospace", 10), wrap=tk.WORD)
        self.log_text.pack(expand=True, fill="both", padx=10, pady=10)

        # Iniciar el chequeo de la cola de logs
        self.after(100, self.check_log_queue)

    def check_log_queue(self):
        """Comprueba la cola de logs y actualiza el widget de texto."""
        while not self.log_queue.empty():
            record = self.log_queue.get_nowait()
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, record + '\n')
            self.log_text.see(tk.END) # Auto-scroll al final
            self.log_text.config(state='disabled')
        self.after(100, self.check_log_queue)


class SettingsView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("MainView"))
        back_button.pack(side="left", padx=10)

        title_label = tk.Label(header, text="Ajustes", font=("Helvetica", 18, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)

        # --- Contenedor de Ajustes ---
        settings_container = tk.Frame(self, bg=COLOR_PRIMARY_BG, padx=20, pady=20)
        settings_container.pack(fill="both", expand=True)

        # --- Ajuste de Velocidad de Voz ---
        rate_label = tk.Label(settings_container, text="Velocidad de la voz:", font=("Helvetica", 14), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
        rate_label.pack(pady=(10, 5), anchor="w")

        self.rate_scale = tk.Scale(
            settings_container,
            from_=80,
            to=220,
            orient=tk.HORIZONTAL,
            length=400,
            command=self.on_rate_change,
            bg=COLOR_PRIMARY_BG,
            troughcolor=COLOR_SECONDARY_BG, # Color de la pista
            fg=COLOR_TEXT_DARK # Color del texto del valor
        )
        self.rate_scale.pack(pady=10, fill="x")
        self.rate_scale.set(self.controller.speaker.get_rate())
        
        # --- Botón para ver el estado del sistema ---
        status_button = ttk.Button(settings_container, text="Ver Estado del Sistema", command=lambda: self.controller.show_frame("SystemStatusView"))
        status_button.pack(pady=20, fill="x", ipady=10)

        # --- Botón para modificar datos de salud ---
        health_data_button = ttk.Button(settings_container, text="Modificar Datos de Salud", command=lambda: self.controller.show_frame("HealthDataView"))
        health_data_button.pack(pady=5, fill="x", ipady=10)

        # --- Checkbox para activar/desactivar detección de caídas ---
        self.fall_detection_var = tk.BooleanVar()
        if self.controller.video_sensor:
            # Establecer el valor inicial del checkbox según el estado del sensor
            self.fall_detection_var.set(self.controller.video_sensor.fall_detection_enabled)

        fall_detection_check = ttk.Checkbutton(
            settings_container,
            text="Activar Detección de Caídas",
            variable=self.fall_detection_var,
            command=lambda: self.controller.action_toggle_fall_detection(self.fall_detection_var.get())
        )
        fall_detection_check.pack(pady=10, anchor="w")

    def on_rate_change(self, rate_value):
        self.controller.speaker.set_rate(rate_value)
        self.controller.speaker.speak("Esta es la nueva velocidad de voz.")
class EmergencyView(tk.Toplevel):
    """
    Ventana emergente que muestra datos de emergencia y es difícil de cerrar.
    """

    def __init__(self, parent, data):
        super().__init__(parent) # El 'parent' es el controlador de la app (KompaiApp)
        self.controller = parent # Guardamos una referencia al controlador
        self.title("!!! INFORMACIÓN DE EMERGENCIA !!!")
        self.attributes('-fullscreen', True)
        self.configure(bg="#8B0000") # Fondo rojo oscuro
        self.resizable(True, True)
        self.lift()  # Asegura que la ventana esté encima
        self.overrideredirect(True) # Elimina la barra de título para que no se pueda cerrar por ahí
        self.focus_force()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)


        main_frame = tk.Frame(self, bg="#8B0000", padx=60, pady=60)
        main_frame.pack(expand=True, fill="both")

        header_label = tk.Label(main_frame, text="INFORMACIÓN DE EMERGENCIA", font=("Helvetica", 32, "bold"), bg="#8B0000", fg="white")
        header_label.pack(pady=(0, 40))

        def create_data_row(parent, label, value):
            row_frame = tk.Frame(parent, bg="#8B0000")
            row_frame.pack(fill="x", pady=10)
            label_widget = tk.Label(row_frame, text=f"{label}:", font=("Helvetica", 20, "bold"), bg="#8B0000", fg="white", anchor="w")
            label_widget.pack(side="left", fill="x", expand=False, ipadx=20)
            if isinstance(value, list):
                value_text = ", ".join(str(v) for v in value) if value else "Ninguna conocida"
            elif value is None:
                value_text = "N/D"
            else:
                value_text = str(value)
            value_widget = tk.Label(row_frame, text=value_text, font=("Helvetica", 20), bg="white", fg="black", wraplength=900, justify="left", anchor="w", padx=20, pady=10)
            value_widget.pack(side="left", fill="x", expand=True)

        # Calcular edad
        try:
            birth_date = date.fromisoformat(data.get('fecha_nacimiento', ''))
            age = date.today().year - birth_date.year - ((date.today().month, date.today().day) < (birth_date.month, birth_date.day))
        except Exception:
            age = "N/D"

        create_data_row(main_frame, "Nombre", data.get("nombre_completo", "N/D"))
        create_data_row(main_frame, "Edad", str(age))
        create_data_row(main_frame, "Grupo Sanguíneo", data.get("grupo_sanguineo", "N/D"))
        create_data_row(main_frame, "Alergias Conocidas", data.get("alergias", []))
        create_data_row(main_frame, "Enfermedades", data.get("enfermedades_conocidas", []))
        create_data_row(main_frame, "Medicación Principal", data.get("medicacion_actual", "Ninguna"))
        contactos = data.get("contactos_emergencia", [])
        if contactos:
            contactos_str = "\n".join([f"{c.get('nombre', 'N/D')}: {c.get('telefono', 'N/D')}" for c in contactos])
        else:
            contactos_str = "Ninguno registrado"
        create_data_row(main_frame, "Contactos", contactos_str)

        # --- Mecanismo de Cierre Seguro con Doble Confirmación ---
        self.cierre_seguro_frame = tk.Frame(main_frame, bg="#8B0000", pady=40)
        self.cierre_seguro_frame.pack(side="bottom", fill="x")
        info_cierre_label = tk.Label(self.cierre_seguro_frame, text="Pulsa el botón para cerrar la ventana de emergencia", font=("Helvetica", 20, "bold"), bg="#8B0000", fg="yellow")
        info_cierre_label.pack(pady=(0, 20))
        self.cerrar_button = tk.Button(self.cierre_seguro_frame, text="CERRAR VENTANA (ESTOY BIEN)", font=("Helvetica", 18, "bold"), bg="white", fg="black", command=self.confirmar_cierre)
        self.cerrar_button.pack(pady=20)

    def confirmar_cierre(self):
        """Solicita doble confirmación antes de cerrar la ventana de emergencia."""
        if messagebox.askyesno("Confirmar Cierre", "¿Estás seguro de que quieres cerrar la alerta de emergencia?", parent=self):
            self.safe_close()

    def safe_close(self):
        """Método seguro para cerrar la ventana y notificar al controlador."""
        self.controller.emergency_view_instance = None # Informa al controlador que la ventana se ha cerrado
        self.destroy()

# --- VISTA DE LA CÁMARA ---
class CameraView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("MainView"))
        back_button.pack(side="left", padx=10)

        title_label = tk.Label(header, text="Visor de Cámara", font=("Helvetica", 18, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)

        # --- Contenedor del Vídeo ---
        self.video_label = tk.Label(self, bg=COLOR_LOG_BG)
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)

    def update_frame(self, pil_image):
        """Actualiza el frame de vídeo en la etiqueta."""
        try:
            # CORRECCIÓN: No usar winfo_width/height() en el primer renderizado, ya que es 1.
            # Usamos un tamaño fijo y dejamos que el widget se ajuste.
            # 800x600 es un buen tamaño de referencia para la pantalla.
            pil_image.thumbnail((800, 600), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image=pil_image)
            self.video_label.config(image=photo)
            # CORRECCIÓN: Guardar la referencia de la imagen en el propio widget
            # para evitar que el recolector de basura la elimine.
            self.video_label.image = photo
        except Exception as e:
            logging.debug(f"Error al actualizar el frame de la cámara en la UI: {e}")

# --- VISTA DE ESTADO DEL SISTEMA ---
class SystemStatusView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("SettingsView"))
        back_button.pack(side="left", padx=10)

        title_label = tk.Label(header, text="Estado del Sistema", font=("Helvetica", 18, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)

        # --- Contenedor de Estados ---
        status_container = tk.Frame(self, bg=COLOR_PRIMARY_BG, padx=30, pady=20)
        status_container.pack(fill="both", expand=True)
        status_container.grid_columnconfigure(1, weight=1)

        self.status_labels = {}
        metrics = [
            "Dirección IP", "Motor de Voz (Piper)", "Reconocimiento de Voz (Vosk)", "Cámara",
            "Conexión a Internet", "Temperatura CPU", "Uso de CPU", "Uso de RAM"
        ]
        for i, metric in enumerate(metrics):
            label = tk.Label(status_container, text=f"{metric}:", font=("Helvetica", 14, "bold"), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK, anchor="w")
            label.grid(row=i, column=0, sticky="w", pady=8)
            value_label = tk.Label(status_container, text="Cargando...", font=("Helvetica", 14), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK, anchor="w")
            value_label.grid(row=i, column=1, sticky="ew", padx=(10, 0))
            self.status_labels[metric] = value_label

    def on_show(self):
        """Se llama cuando el frame se hace visible para iniciar la actualización."""
        self.update_status()

    def update_status(self):
        """Recopila y muestra el estado actual del sistema."""
        # Dirección IP
        self.status_labels["Dirección IP"].config(text=self.controller.get_ip_address())
        
        # Motor de Voz
        piper_status = "✅ Operativo" if self.controller.speaker.is_available else "❌ No disponible"
        self.status_labels["Motor de Voz (Piper)"].config(text=piper_status, fg="green" if self.controller.speaker.is_available else "red")
        # Reconocimiento de Voz
        vosk_status = "✅ Operativo" if self.controller.vosk_model else "❌ No disponible"
        self.status_labels["Reconocimiento de Voz (Vosk)"].config(text=vosk_status, fg="green" if self.controller.vosk_model else "red")
        # Cámara
        cam_status = self.controller.camera_status.capitalize()
        self.status_labels["Cámara"].config(text=cam_status, fg="green" if cam_status == "Connected" else "red")
        # Internet
        internet_status = "✅ Conectado" if self.controller.check_internet_connection() else "❌ Desconectado"
        self.status_labels["Conexión a Internet"].config(text=internet_status, fg="green" if "Conectado" in internet_status else "red")
        # Métricas del sistema
        self.status_labels["Temperatura CPU"].config(text=self.controller.get_cpu_temperature())
        cpu, ram = self.controller.get_system_usage()
        self.status_labels["Uso de CPU"].config(text=cpu)
        self.status_labels["Uso de RAM"].config(text=ram)
        # Programar la próxima actualización
        self.after(3000, self.update_status)

# --- VISTA PARA EDITAR DATOS DE SALUD ---
class HealthDataView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller
        self.widgets = {}

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("SettingsView"))
        back_button.pack(side="left", padx=10)

        title_label = tk.Label(header, text="Editar Datos de Salud", font=("Helvetica", 18, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)

        # --- Contenedor de Campos ---
        form_container = tk.Frame(self, bg=COLOR_PRIMARY_BG, padx=30, pady=20)
        form_container.pack(fill="both", expand=True)

        fields = {
            "nombre_completo": "Nombre Completo",
            "fecha_nacimiento": "Fecha Nacimiento (AAAA-MM-DD)",
            "grupo_sanguineo": "Grupo Sanguíneo",
            "alergias": "Alergias (una por línea)",
            "enfermedades_conocidas": "Enfermedades (una por línea)",
            "medicacion_actual": "Medicación Principal"
        }

        for i, (key, label_text) in enumerate(fields.items()):
            label = tk.Label(form_container, text=label_text, font=("Helvetica", 12, "bold"), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
            label.grid(row=i, column=0, sticky="w", pady=(10, 2))
            
            if key in ["alergias", "enfermedades_conocidas"]:
                widget = tk.Text(form_container, height=3, width=50, font=("Helvetica", 12), relief="solid", borderwidth=1)
            else:
                widget = tk.Entry(form_container, font=("Helvetica", 12), relief="solid", borderwidth=1)
            
            widget.grid(row=i+1, column=0, sticky="ew", pady=(0, 10))
            self.widgets[key] = widget

        form_container.grid_columnconfigure(0, weight=1)

        # --- Botón de Guardar ---
        save_button = ttk.Button(self, text="Guardar Cambios", command=self.save_data)
        save_button.pack(pady=20)

    def on_show(self):
        """Carga los datos actuales en los campos del formulario."""
        data = self.controller.datos_emergencia
        for key, widget in self.widgets.items():
            value = data.get(key, "")
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                if isinstance(value, list):
                    widget.insert("1.0", "\n".join(value))
            else: # Es un Entry
                widget.delete(0, tk.END)
                widget.insert(0, str(value))

    def save_data(self):
        """Recopila los datos de los campos y los guarda en el fichero JSON."""
        new_data = self.controller.datos_emergencia.copy() # Copiar para mantener campos no editables

        for key, widget in self.widgets.items():
            if isinstance(widget, tk.Text):
                # Obtener texto, dividir por líneas y quitar las vacías
                value = [line.strip() for line in widget.get("1.0", tk.END).strip().split("\n") if line.strip()]
            else: # Es un Entry
                value = widget.get().strip()
            
            new_data[key] = value

        # Guardar los contactos de emergencia que no se editan aquí
        new_data['contactos_emergencia'] = self.controller.datos_emergencia.get('contactos_emergencia', [])

        if self.controller.save_health_data(new_data):
            messagebox.showinfo("Éxito", "Los datos de salud se han guardado correctamente.", parent=self)
            self.controller.show_frame("SettingsView")
        else:
            messagebox.showerror("Error", "No se pudieron guardar los datos de salud. Revisa los logs.", parent=self)

# --- VISTA DE ALARMAS ---
class AlarmView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLOR_PRIMARY_BG)
        self.controller = controller

        # --- Header ---
        header = tk.Frame(self, bg=COLOR_HEADER_BG, pady=10)
        header.pack(fill="x")
        
        back_button = ttk.Button(header, text="Volver", command=lambda: controller.show_frame("MainView"))
        back_button.pack(side="left", padx=10)

        title_label = tk.Label(header, text="Gestión de Alarmas", font=("Helvetica", 18, "bold"), bg=COLOR_HEADER_BG, fg=COLOR_TEXT_LIGHT)
        title_label.pack(side="left", expand=True)

        add_button = ttk.Button(header, text="Añadir Alarma", command=self.add_alarm_popup)
        add_button.pack(side="right", padx=10)

        # --- Contenedor de la lista de alarmas ---
        self.alarms_list_frame = tk.Frame(self, bg=COLOR_PRIMARY_BG, padx=20, pady=10)
        self.alarms_list_frame.pack(fill="both", expand=True)

    def on_show(self):
        self.render_alarms()

    def render_alarms(self):
        # Limpiar vista anterior
        for widget in self.alarms_list_frame.winfo_children():
            widget.destroy()

        alarms = self.controller.alarm_manager.get_all_alarms()
        days_map = {0: "L", 1: "M", 2: "X", 3: "J", 4: "V", 5: "S", 6: "D"}

        if not alarms:
            no_alarms_label = tk.Label(self.alarms_list_frame, text="No hay alarmas programadas.", font=("Helvetica", 14, "italic"), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
            no_alarms_label.pack(pady=50)
            return

        for alarm in alarms:
            alarm_frame = tk.Frame(self.alarms_list_frame, bg=COLOR_SECONDARY_BG, relief="solid", borderwidth=1, padx=10, pady=10)
            alarm_frame.pack(fill="x", pady=5)

            time_label = tk.Label(alarm_frame, text=alarm['time'], font=("Helvetica", 24, "bold"), bg=COLOR_SECONDARY_BG, fg=COLOR_TEXT_DARK)
            time_label.pack(side="left", padx=(0, 20))

            details_frame = tk.Frame(alarm_frame, bg=COLOR_SECONDARY_BG)
            details_frame.pack(side="left", expand=True, fill="x")

            label_label = tk.Label(details_frame, text=alarm['label'], font=("Helvetica", 14, "bold"), bg=COLOR_SECONDARY_BG, fg=COLOR_TEXT_DARK, anchor="w")
            label_label.pack(fill="x")

            days_str = ", ".join([days_map[d] for d in sorted(alarm['days_of_week'])]) if alarm['days_of_week'] else "Nunca"
            if len(alarm['days_of_week']) == 7: days_str = "Todos los días"
            days_label = tk.Label(details_frame, text=days_str, font=("Helvetica", 12), bg=COLOR_SECONDARY_BG, fg=COLOR_TEXT_DARK, anchor="w")
            days_label.pack(fill="x")

            delete_button = ttk.Button(alarm_frame, text="Eliminar", command=lambda a=alarm: self.delete_alarm(a))
            delete_button.pack(side="right")

    def delete_alarm(self, alarm):
        if messagebox.askyesno("Confirmar", f"¿Seguro que quieres eliminar la alarma '{alarm['label']}' de las {alarm['time']}?", parent=self):
            self.controller.alarm_manager.delete_alarm(alarm)
            self.render_alarms() # Refrescar la lista

    def add_alarm_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Añadir Alarma")
        popup.geometry("400x400")
        popup.configure(bg=COLOR_PRIMARY_BG)
        popup.transient(self)
        popup.grab_set()

        form_frame = tk.Frame(popup, bg=COLOR_PRIMARY_BG, padx=20, pady=20)
        form_frame.pack(expand=True, fill="both")

        # --- MEJORA: Selector de hora sin teclado ---
        tk.Label(form_frame, text="Hora:", font=("Helvetica", 12, "bold"), bg=COLOR_PRIMARY_BG).pack(anchor="w")
        
        time_selector_frame = tk.Frame(form_frame, bg=COLOR_PRIMARY_BG)
        time_selector_frame.pack(fill="x", pady=5)

        # Variables para la hora y los minutos
        self.hour_var = tk.IntVar(value=datetime.now().hour)
        self.minute_var = tk.IntVar(value=datetime.now().minute)

        # --- Selector de Horas ---
        hour_frame = tk.Frame(time_selector_frame, bg=COLOR_PRIMARY_BG)
        hour_frame.pack(side="left", expand=True, padx=10)
        
        up_hour_button = ttk.Button(hour_frame, text="▲", command=lambda: self.change_time(self.hour_var, 1, 23), style="Grid.TButton")
        up_hour_button.pack()
        self.hour_label = tk.Label(hour_frame, textvariable=self.hour_var, font=("Helvetica", 48, "bold"), bg=COLOR_SECONDARY_BG, width=3)
        self.hour_label.pack(pady=5)
        down_hour_button = ttk.Button(hour_frame, text="▼", command=lambda: self.change_time(self.hour_var, -1, 23), style="Grid.TButton")
        down_hour_button.pack()

        # Separador
        tk.Label(time_selector_frame, text=":", font=("Helvetica", 48, "bold"), bg=COLOR_PRIMARY_BG).pack(side="left")

        # --- Selector de Minutos ---
        minute_frame = tk.Frame(time_selector_frame, bg=COLOR_PRIMARY_BG)
        minute_frame.pack(side="left", expand=True, padx=10)

        up_minute_button = ttk.Button(minute_frame, text="▲", command=lambda: self.change_time(self.minute_var, 1, 59), style="Grid.TButton")
        up_minute_button.pack()
        self.minute_label = tk.Label(minute_frame, textvariable=self.minute_var, font=("Helvetica", 48, "bold"), bg=COLOR_SECONDARY_BG, width=3)
        self.minute_label.pack(pady=5)
        down_minute_button = ttk.Button(minute_frame, text="▼", command=lambda: self.change_time(self.minute_var, -1, 59), style="Grid.TButton")
        down_minute_button.pack()

        # Formatear los números iniciales a dos dígitos
        self.hour_var.trace_add("write", lambda *args: self.format_time_label(self.hour_label, self.hour_var))
        self.minute_var.trace_add("write", lambda *args: self.format_time_label(self.minute_label, self.minute_var))
        self.format_time_label(self.hour_label, self.hour_var)
        self.format_time_label(self.minute_label, self.minute_var)

        tk.Label(form_frame, text="Etiqueta:", font=("Helvetica", 12), bg=COLOR_PRIMARY_BG).pack(anchor="w")
        label_entry = tk.Entry(form_frame, font=("Helvetica", 12))
        label_entry.pack(fill="x", pady=(0, 10))
        label_entry.insert(0, "Alarma")

        tk.Label(form_frame, text="Días:", font=("Helvetica", 12, "bold"), bg=COLOR_PRIMARY_BG).pack(anchor="w", pady=(10,0))
        days_vars = {day: tk.BooleanVar() for day in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]}
        days_frame = tk.Frame(form_frame, bg=COLOR_PRIMARY_BG)
        days_frame.pack(fill="x", pady=(0, 20))
        for day, var in days_vars.items():
            tk.Checkbutton(days_frame, text=day[:1], variable=var, bg=COLOR_PRIMARY_BG).pack(side="left", expand=True)

        def on_save():
            try:
                hour = self.hour_var.get()
                minute = self.minute_var.get()
                selected_days = [i for i, day in enumerate(days_vars) if days_vars[day].get()]
                self.controller.alarm_manager.add_alarm(hour, minute, selected_days, label_entry.get())
                self.render_alarms()
                popup.destroy()
            except Exception:
                messagebox.showerror("Error", "Ocurrió un error al guardar la alarma.", parent=popup)

        save_button = ttk.Button(form_frame, text="Guardar Alarma", command=on_save)
        save_button.pack()

    def change_time(self, time_var, amount, max_val):
        """Función para incrementar/decrementar la hora/minuto con efecto 'wrap-around'."""
        current_val = time_var.get()
        new_val = current_val + amount
        if new_val > max_val: new_val = 0
        if new_val < 0: new_val = max_val
        time_var.set(new_val)

    def format_time_label(self, label_widget, time_var):
        """Asegura que el número en la etiqueta siempre tenga dos dígitos."""
        label_widget.config(text=f"{time_var.get():02d}")

# --- VISTA DE RELOJ Y TEMPORIZADOR ---
class ClockTimerView(tk.Toplevel):
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        self.title("Reloj y Temporizador")
        self.geometry("700x450")
        self.configure(bg=COLOR_PRIMARY_BG)
        self.transient(controller)
        self.grab_set()

        # --- Notebook para las pestañas ---
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # --- Pestaña 1: Reloj Grande ---
        clock_tab = tk.Frame(notebook, bg=COLOR_PRIMARY_BG)
        notebook.add(clock_tab, text="Reloj Grande")
        self.create_big_clock(clock_tab)

        # --- Pestaña 2: Temporizador ---
        timer_tab = tk.Frame(notebook, bg=COLOR_PRIMARY_BG)
        notebook.add(timer_tab, text="Temporizador")
        self.create_timer(timer_tab)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        # Detener bucles de actualización al cerrar
        self.timer_running = False
        self.big_clock_running = False
        self.destroy()

    def create_big_clock(self, parent):
        self.big_clock_label = tk.Label(parent, font=("Helvetica", 110, "bold"), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
        self.big_clock_label.pack(expand=True)
        self.big_clock_running = True
        self.update_big_clock()

    def update_big_clock(self):
        if not self.big_clock_running: return
        time_str = time.strftime("%H:%M:%S")
        self.big_clock_label.config(text=time_str)
        self.after(1000, self.update_big_clock)

    def create_timer(self, parent):
        self.timer_seconds = 0
        self.timer_running = False

        # Frame para la entrada de tiempo
        entry_frame = tk.Frame(parent, bg=COLOR_PRIMARY_BG)
        entry_frame.pack(pady=20)
        tk.Label(entry_frame, text="Minutos:", font=("Helvetica", 14), bg=COLOR_PRIMARY_BG).pack(side="left")
        self.timer_entry = tk.Entry(entry_frame, font=("Helvetica", 14), width=5)
        self.timer_entry.pack(side="left", padx=10)
        set_button = ttk.Button(entry_frame, text="Establecer", command=self.set_timer)
        set_button.pack(side="left")

        # Label para mostrar el tiempo restante
        self.timer_label = tk.Label(parent, text="00:00", font=("Helvetica", 96, "bold"), bg=COLOR_PRIMARY_BG, fg=COLOR_TEXT_DARK)
        self.timer_label.pack(expand=True)

        # Frame para los botones de control
        controls_frame = tk.Frame(parent, bg=COLOR_PRIMARY_BG)
        controls_frame.pack(pady=20)
        self.start_button = ttk.Button(controls_frame, text="Iniciar", command=self.start_timer)
        self.start_button.pack(side="left", padx=10)
        self.pause_button = ttk.Button(controls_frame, text="Pausar", command=self.pause_timer, state="disabled")
        self.pause_button.pack(side="left", padx=10)
        reset_button = ttk.Button(controls_frame, text="Reiniciar", command=self.reset_timer)
        reset_button.pack(side="left", padx=10)

    def set_timer(self):
        try:
            minutes = int(self.timer_entry.get())
            self.timer_seconds = minutes * 60
            self.update_timer_display()
        except ValueError:
            messagebox.showerror("Error", "Por favor, introduce un número válido de minutos.", parent=self)

    def start_timer(self):
        if self.timer_seconds > 0 and not self.timer_running:
            self.timer_running = True
            self.start_button.config(state="disabled")
            self.pause_button.config(state="normal")
            self.countdown()

    def pause_timer(self):
        self.timer_running = False
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")

    def reset_timer(self):
        self.pause_timer()
        self.set_timer()

    def countdown(self):
        if self.timer_running and self.timer_seconds > 0:
            self.timer_seconds -= 1
            self.update_timer_display()
            self.after(1000, self.countdown)
        elif self.timer_running and self.timer_seconds == 0:
            self.timer_running = False
            self.controller.speaker.speak("¡El tiempo ha terminado!")
            messagebox.showinfo("Temporizador", "¡El tiempo ha terminado!", parent=self)
            self.start_button.config(state="normal")
            self.pause_button.config(state="disabled")

    def update_timer_display(self):
        mins, secs = divmod(self.timer_seconds, 60)
        self.timer_label.config(text=f"{mins:02d}:{secs:02d}")

if __name__ == "__main__":
    app = KompaiApp()
    app.mainloop()
