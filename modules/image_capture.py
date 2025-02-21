import cv2
import time
import os
from datetime import datetime
import logging
from threading import Thread
from config import (
    BASE_IMAGE_DIR, 
    CAPTURE_INTERVAL, 
    IP_CAMERAS_CONFIG,
    MIN_BLUR_THRESHOLD
)
from modules.cameras import create_camera
from modules.image_validator import ImageValidator

logger = logging.getLogger(__name__)

class ImageCapture:
    def __init__(self, production_lines, interval=CAPTURE_INTERVAL):
        self.production_lines = production_lines
        self.interval = interval
        self.running = False
        self.capture_threads = []
        self.current_minute = None
        self.cameras = {}  # {camera_key: camera_instance}
        self.db_handler = None
        self.monitor_thread = None

    def set_db_handler(self, db_handler):
        self.db_handler = db_handler

    def start_capture(self):
        """Inicia a captura de imagens"""
        try:
            logger.info("Iniciando captura de imagens...")
            self.running = True
            
            # Iniciar thread de monitoramento
            self.monitor_thread = Thread(target=self._monitor_batches)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            # Iniciar threads de captura
            for line_id, cameras in self.production_lines.items():
                for camera_config in cameras:
                    camera_key = f"{line_id}_{camera_config['type']}_{camera_config.get('id', 0)}"
                    try:
                        camera = cv2.VideoCapture(camera_config['id'])
                        if camera.isOpened():
                            self.cameras[camera_key] = camera
                            thread = Thread(
                                target=self._capture_loop,
                                args=(camera_key, line_id, camera_config)
                            )
                            thread.daemon = True
                            thread.start()
                            self.capture_threads.append(thread)
                    except Exception as e:
                        logger.error(f"Erro ao inicializar câmera {camera_key}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Erro ao iniciar captura: {str(e)}")
            self.running = False

    def _capture_loop(self, camera_key, line_id, camera_config):
        """Loop de captura para uma câmera"""
        try:
            logger.info(f"Iniciando captura para câmera {camera_key}")
            
            # Inicializar câmera
            camera = cv2.VideoCapture(camera_config['id'])
            if not camera.isOpened():
                logger.error(f"Não foi possível abrir a câmera {camera_key}")
                return
            
            # Configurar câmera
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config['resolution'][0])
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config['resolution'][1])
            camera.set(cv2.CAP_PROP_FPS, camera_config['fps'])
            
            current_minute = None
            batch_dir = None
            
            while self.running:
                try:
                    now = datetime.now()
                    minute_key = now.strftime("%Y%m%d_%H%M")
                    
                    # Verificar se começou novo minuto
                    if minute_key != current_minute:
                        current_minute = minute_key
                        
                        # Criar diretório do lote (apenas linha/minuto)
                        batch_dir = os.path.join(
                            BASE_IMAGE_DIR,
                            line_id,
                            minute_key
                        )
                        os.makedirs(batch_dir, exist_ok=True)
                        logger.info(f"Novo lote iniciado: {line_id} - {minute_key}")
                    
                    # Capturar frame
                    ret, frame = camera.read()
                    if not ret:
                        logger.error(f"Erro ao capturar frame da câmera {camera_key}")
                        time.sleep(1)
                        continue
                    
                    # Salvar frame com posição no nome
                    position = camera_config.get('position', 'default')
                    filename = f"{position}_frame_{now.strftime('%H%M%S')}.jpg"
                    filepath = os.path.join(batch_dir, filename)
                    cv2.imwrite(filepath, frame)

                    # Esperar intervalo
                    time.sleep(self.interval)
                    
                except Exception as e:
                    logger.error(f"Erro no loop de captura: {str(e)}")
                    time.sleep(1)
                
        except Exception as e:
            logger.error(f"Erro fatal no loop de captura: {str(e)}")
        
        finally:
            if 'camera' in locals():
                camera.release()
            logger.info(f"Captura finalizada para câmera {camera_key}")

    def _create_batch_directory(self, line_id, camera_config, timestamp):
        base_dir = BASE_IMAGE_DIR
        date_str = timestamp.strftime("%Y_%m_%d")
        hour_minute = timestamp.strftime("%H_%M")
        
        # Estrutura: captured_images/linha_X/camera_tipo_id/YYYY_MM_DD/HH_MM/
        camera_folder = (f"camera_{camera_config['type']}_{camera_config.get('id', '')}" 
                        if camera_config['type'] == 'usb' 
                        else f"camera_ip_{camera_config['url'].split('/')[-1]}")
        
        batch_dir = os.path.join(
            base_dir,
            line_id,
            camera_folder,
            date_str,
            hour_minute
        )
        
        os.makedirs(batch_dir, exist_ok=True)
        return batch_dir

    def _get_batch_folder(self, line_id, minute):
        """Retorna o diretório base do lote para uma linha/minuto"""
        base_dir = BASE_IMAGE_DIR
        date_str = datetime.now().strftime("%Y_%m_%d")
        return os.path.join(base_dir, line_id, date_str, minute)

    def stop_capture(self):
        self.running = False
        for thread in self.capture_threads:
            thread.join()
        for camera in self.cameras.values():
            camera.release()

    def check_cameras_status(self):
        """Verifica o status atual das câmeras"""
        status = {}
        for camera_key, camera in self.cameras.items():
            try:
                info = camera.get_info()
                info['last_check'] = datetime.now().isoformat()
                status[camera_key] = info
            except Exception as e:
                status[camera_key] = {
                    'status': f'Erro: {str(e)}',
                    'last_check': datetime.now().isoformat()
                }
        return status 

    def _monitor_batches(self):
        """Monitora e registra lotes completos"""
        last_registered_minute = None
        
        while self.running:
            try:
                current_minute = datetime.now().strftime("%Y%m%d_%H%M")
                
                # Se mudou o minuto, registrar lotes do minuto anterior
                if current_minute != last_registered_minute and last_registered_minute:
                    for line_id in self.production_lines.keys():
                        batch_path = os.path.join(BASE_IMAGE_DIR, line_id, last_registered_minute)
                        
                        # Verificar se diretório existe e tem imagens
                        if os.path.exists(batch_path):
                            images = [f for f in os.listdir(batch_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
                            if images:
                                self.db_handler.register_new_batch(
                                    line_id=line_id,
                                    batch_path=batch_path
                                )
                                logger.info(f"Lote registrado: {line_id} - {last_registered_minute} - {len(images)} imagens")
                
                last_registered_minute = current_minute
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro no monitor de lotes: {str(e)}")
                time.sleep(5) 