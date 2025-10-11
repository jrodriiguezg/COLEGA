# video_sensor.py

import cv2
from PIL import Image
import mediapipe as mp
import time
import logging
from datetime import datetime, timedelta

# Obtener el logger específico para el vídeo
video_logger = logging.getLogger('video')

class VideoSensor:
    def __init__(self, stream_url, ui_queue):
        self.stream_url = stream_url
        self.ui_queue = ui_queue
        self.cap = None
        self.is_running = True
        self.models_loaded = False
        
        # --- Carga de Modelos de Visión ---
        try:
            # Modelo rápido para detectar caras (presencia y mirada)
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            # Modelo avanzado para analizar la postura del cuerpo (caídas)
            self.mp_pose = mp.solutions.pose
            self.mp_drawing = mp.solutions.drawing_utils
            self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
            self.models_loaded = True
            video_logger.info("Modelos de visión (OpenCV/MediaPipe) cargados correctamente.")
        except Exception as e:
            video_logger.error(f"Error crítico al cargar los modelos de visión: {e}")

        # --- Variables de Estado ---
        self.last_presence_time = datetime.now()
        self.is_user_present = False
        self.fall_cooldown = timedelta(seconds=10) # Evita falsas alarmas repetidas
        self.last_fall_time = datetime.min
        self.fall_detection_enabled = True # Interruptor para activar/desactivar la detección

        # --- NUEVO: Variables para la detección de velocidad en caídas ---
        self.last_hips_y = None
        self.last_pose_time = None
        self.FALL_VELOCITY_THRESHOLD = 0.5 # Umbral de velocidad vertical (coords. normalizadas / segundo)

        # --- NUEVO: Variables para recordatorio de movimiento ---
        self.last_significant_movement_time = datetime.now()
        self.last_movement_reminder_time = datetime.min
        self.MOVEMENT_THRESHOLD = 0.05 # Pequeño cambio en la posición Y de la cadera
        self.INACTIVITY_DURATION_FOR_REMINDER = timedelta(hours=1)

    def connect(self):
        """Intenta (re)conectar al stream de vídeo de la ESP32-CAM."""
        video_logger.info(f"Intentando conectar a la cámara: {self.stream_url}")
        # Usamos cv2.CAP_FFMPEG para mejorar la compatibilidad con streams de red
        self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            video_logger.error("No se pudo abrir el stream de vídeo. Reintentando en 10s...")
            self.cap = None
            self.ui_queue.put({'type': 'camera_status', 'status': 'disconnected'})
            return False
        video_logger.info("Conexión con la cámara establecida.")
        self.ui_queue.put({'type': 'camera_status', 'status': 'connected'})
        return True

    def run(self):
        """Bucle principal que se ejecuta en un hilo para procesar el vídeo."""
        if not self.models_loaded:
            video_logger.error("El hilo del sensor de vídeo no se iniciará porque los modelos no se cargaron.")
            return

        while self.is_running:
            try:
                # Si no hay conexión, intenta reconectar
                if self.cap is None:
                    if not self.connect():
                        time.sleep(10)
                        continue

                # Si hay conexión, intenta leer un frame
                ret, frame = self.cap.read()

                # Si la lectura falla, la conexión se ha perdido
                if not ret:
                    video_logger.warning("Se perdió el frame de la cámara. Reintentando conexión...")
                    self.ui_queue.put({'type': 'camera_status', 'status': 'disconnected'})
                    if self.cap: self.cap.release()
                    self.cap = None
                    time.sleep(5)
                    continue

                # Si todo va bien, procesa el frame
                frame_resized = cv2.resize(frame, (640, 480))
                # Hacemos una copia para dibujar sobre ella sin afectar los cálculos
                display_frame = frame_resized.copy()
                self.detect_presence_and_gaze(frame_resized, display_frame)
                self.detect_fall(frame_resized, display_frame)
                self.check_movement_inactivity()
                self.check_absence()
                self.ui_queue.put({'type': 'video_frame', 'frame': display_frame})
                
                # Limita a ~10 FPS para no sobrecargar la CPU de la Raspberry Pi
                time.sleep(0.1) 
            except Exception as e:
                video_logger.error(f"Error inesperado en el bucle del sensor de vídeo: {e}")
                time.sleep(5)

    def stop(self):
        """Detiene el bucle del hilo de forma segura."""
        self.is_running = False
        if self.cap:
            self.cap.release()

    def detect_presence_and_gaze(self, frame, display_frame):
        """Detecta si hay un usuario y si está mirando (enciende la pantalla)."""
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray_frame, 1.1, 5)

        # Dibuja un rectángulo alrededor de cada cara detectada
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        user_is_now_present = len(faces) > 0

        if user_is_now_present:
            self.last_presence_time = datetime.now()
            if not self.is_user_present:
                self.is_user_present = True
                video_logger.info("Usuario detectado cerca del dispositivo.")
                self.ui_queue.put({'type': 'user_present', 'status': True})
            
            # Si se detecta una cara, asumimos que el usuario está mirando
            self.ui_queue.put({'type': 'user_gazing'})
        else:
            if self.is_user_present:
                self.is_user_present = False
                video_logger.info("El usuario ya no está cerca del dispositivo (apaga la pantalla).")
                self.ui_queue.put({'type': 'user_present', 'status': False})

    def detect_fall(self, frame, display_frame):
        """Detecta una posible caída analizando la pose del cuerpo."""
        # Si la detección está desactivada, no hacer nada.
        if not self.fall_detection_enabled:
            return
        if datetime.now() - self.last_fall_time < self.fall_cooldown:
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Para mejorar el rendimiento, hacemos el frame no escribible
        rgb_frame.flags.writeable = False
        results = self.pose.process(rgb_frame)
        rgb_frame.flags.writeable = True

        now = datetime.now()
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            
            try:
                # Obtener coordenadas Y de caderas y hombros
                hips_y = (landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y + landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value].y) / 2
                shoulders_y = (landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y + landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y) / 2
                
                # --- NUEVO: Cálculo de velocidad vertical ---
                vertical_velocity = 0
                if self.last_hips_y is not None and self.last_pose_time is not None:
                    time_delta = (now - self.last_pose_time).total_seconds()
                    if time_delta > 0:
                        # Velocidad = (posición_actual - posición_anterior) / tiempo
                        vertical_velocity = (hips_y - self.last_hips_y) / time_delta

                        # Si hay un cambio de posición significativo, registrarlo como movimiento
                        if abs(hips_y - self.last_hips_y) > self.MOVEMENT_THRESHOLD:
                            self.last_significant_movement_time = now
                
                # Actualizar estado para el próximo frame
                self.last_hips_y = hips_y
                self.last_pose_time = now

                # Criterio 1: La persona está en posición horizontal (poca diferencia vertical)
                vertical_diff = abs(hips_y - shoulders_y)
                is_horizontal = vertical_diff < 0.15 # Umbral ajustable
                video_logger.info(f"[FallCheck] Horizontalidad: diff={vertical_diff:.2f}, umbral<0.15, resultado={is_horizontal}")

                # Criterio 2: El centro del cuerpo está en la mitad inferior de la pantalla
                is_on_floor = hips_y > 0.65 # Umbral ajustable
                video_logger.info(f"[FallCheck] Posición en suelo: hips_y={hips_y:.2f}, umbral>0.65, resultado={is_on_floor}")
                
                # Criterio 3: Hubo un movimiento descendente rápido (velocidad positiva alta)
                is_moving_down_fast = vertical_velocity > self.FALL_VELOCITY_THRESHOLD
                video_logger.info(f"[FallCheck] Velocidad vertical: {vertical_velocity:.2f}, umbral>{self.FALL_VELOCITY_THRESHOLD}, resultado={is_moving_down_fast}")

                if is_horizontal and is_on_floor and is_moving_down_fast:
                    video_logger.warning("¡POSIBLE CAÍDA DETECTADA!")
                    self.ui_queue.put({'type': 'fall_detected'})
                    self.last_fall_time = datetime.now()
            except Exception as e:
                # Si alguna landmark no es visible o hay un error, lo registramos y continuamos
                video_logger.debug(f"No se pudieron procesar las landmarks para detección de caída: {e}")
                # Reseteamos el estado de velocidad para evitar usar datos viejos
                self.last_hips_y = None
                self.last_pose_time = None
            
            # Dibujar el esqueleto de la pose sobre el frame de visualización
            # Asegurarse de que el frame es escribible
            display_frame.flags.writeable = True
            self.mp_drawing.draw_landmarks(
                display_frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
            )
        else:
            # Si no se detecta a nadie, reseteamos el estado de velocidad
            self.last_hips_y = None
            self.last_pose_time = None

    def check_movement_inactivity(self):
        """Comprueba si el usuario ha estado inactivo (sin moverse mucho) durante demasiado tiempo."""
        # Solo comprobar si el usuario está presente
        if not self.is_user_present:
            return

        time_since_movement = datetime.now() - self.last_significant_movement_time
        time_since_reminder = datetime.now() - self.last_movement_reminder_time

        # Si ha pasado más de 1 hora desde el último movimiento y desde el último recordatorio
        if time_since_movement > self.INACTIVITY_DURATION_FOR_REMINDER and time_since_reminder > self.INACTIVITY_DURATION_FOR_REMINDER:
            video_logger.info("Detectada inactividad por movimiento. Enviando recordatorio.")
            self.ui_queue.put({'type': 'speak', 'text': "Llevas un rato sin moverte mucho. ¿Qué tal si estiramos un poco las piernas?"})
            self.last_movement_reminder_time = datetime.now() # Resetear temporizador del recordatorio
    def check_absence(self):
        """Función adicional: Detecta si el usuario lleva mucho tiempo ausente."""
        # Solo comprobar durante el día (ej: de 8 AM a 8 PM)
        if self.last_presence_time and not self.is_user_present and 8 <= datetime.now().hour < 20:
            time_since_last_seen = datetime.now() - self.last_presence_time
            
            # Umbral de alerta: 4 horas
            if time_since_last_seen > timedelta(hours=4):
                 video_logger.warning(f"Alerta de inactividad: Usuario ausente por más de 4 horas.")
                 self.ui_queue.put({'type': 'user_absent_long_time'})
                 # Resetear el tiempo para no enviar la alerta continuamente
                 self.last_presence_time = datetime.now()

    def toggle_fall_detection(self, enabled: bool):
        """Activa o desactiva la detección de caídas."""
        self.fall_detection_enabled = enabled
        status = "activada" if enabled else "desactivada"
        video_logger.info(f"La detección de caídas ha sido {status}.")