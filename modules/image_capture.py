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
        self.current_batch_folders = {}  # {camera_key: current_folder}
        self.cameras = {}  # {camera_key: camera_instance}
        self.db_handler = None

    def set_db_handler(self, db_handler):
        self.db_handler = db_handler

    def start_capture(self):
        """Inicia a captura de imagens"""
        try:
            logger.info("Iniciando captura de imagens...")
            self.running = True
            
            for line_id, cameras in self.production_lines.items():
                for camera_config in cameras:
                    camera_key = f"{line_id}_{camera_config['type']}_{camera_config.get('id', 0)}"
                    
                    try:
                        camera = create_camera(camera_config)
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
                        continue
                    
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
            frames_in_batch = 0
            batch_dir = None
            
            while self.running:
                try:
                    now = datetime.now()
                    minute_key = now.strftime("%Y%m%d_%H%M")
                    
                    # Verificar se começou novo minuto
                    if minute_key != current_minute:
                        # Se tinha um lote anterior, registrar no banco
                        if current_minute and batch_dir:
                            self.db_handler.register_new_batch(
                                line_id=line_id,
                                batch_path=batch_dir
                            )
                            logger.info(f"Lote {current_minute} registrado no banco")
                        
                        current_minute = minute_key
                        frames_in_batch = 0
                        
                        # Criar novo diretório para o lote
                        batch_dir = os.path.join(
                            BASE_IMAGE_DIR,
                            line_id,
                            f"camera_{camera_config['type']}_{camera_config['id']}",
                            minute_key
                        )
                        os.makedirs(batch_dir, exist_ok=True)
                        logger.info(f"Novo lote iniciado: {batch_dir}")
                    
                    # Capturar frame
                    ret, frame = camera.read()
                    if not ret:
                        logger.error(f"Erro ao capturar frame da câmera {camera_key}")
                        time.sleep(1)
                        continue
                    
                    # Salvar frame
                    filename = f"frame_{now.strftime('%H%M%S')}.jpg"
                    filepath = os.path.join(batch_dir, filename)
                    cv2.imwrite(filepath, frame)
                    
                    frames_in_batch += 1
                    logger.info(f"Frame {frames_in_batch}/12 capturado para o lote {current_minute}")
                    
                    # Se completou 12 frames, registrar lote
                    if frames_in_batch >= 12:
                        self.db_handler.register_new_batch(
                            line_id=line_id,
                            batch_path=batch_dir
                        )
                        logger.info(f"Lote {current_minute} completo e registrado no banco")
                    
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