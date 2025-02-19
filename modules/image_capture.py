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
        self.running = True
        for line_id, cameras in self.production_lines.items():
            for camera_config in cameras:
                camera_key = f"{line_id}_{camera_config['type']}_{camera_config.get('id', camera_config.get('url'))}"
                
                # Criar instância da câmera
                if camera_config['type'] == 'ip':
                    camera_config.update(IP_CAMERAS_CONFIG.get(camera_key, IP_CAMERAS_CONFIG['default']))
                
                try:
                    camera = create_camera(camera_config)
                    self.cameras[camera_key] = camera
                except Exception as e:
                    logger.error(f"Erro ao criar câmera {camera_key}: {str(e)}")
                    continue
                
                thread = Thread(
                    target=self._capture_loop, 
                    args=(camera_key, line_id, camera_config)
                )
                thread.daemon = True
                thread.start()
                self.capture_threads.append(thread)

    def _capture_loop(self, camera_key, line_id, camera_config):
        camera = self.cameras[camera_key]
        current_minute = None
        
        while self.running:
            try:
                current_time = datetime.now()
                new_minute = current_time.strftime("%H_%M")
                
                # Verificar se mudou o minuto
                if current_minute != new_minute:
                    # Se tinha um minuto anterior, registrar lote
                    if current_minute and self.db_handler:
                        previous_batch = self._get_batch_folder(line_id, current_minute)
                        self.db_handler.register_new_batch(line_id, previous_batch)

                    current_minute = new_minute
                    self.current_batch_folders[camera_key] = self._create_batch_directory(
                        line_id,
                        camera_config,
                        current_time
                    )
                
                # Capturar frame
                ret, frame = camera.read()
                if ret:
                    # Verificar qualidade do frame
                    blur = cv2.Laplacian(frame, cv2.CV_64F).var()
                    if blur < MIN_BLUR_THRESHOLD:
                        logger.warning(f"Frame borrado descartado: {blur}")
                        continue
                    filename = f"frame_{current_time.strftime('%H_%M_%S')}.jpg"
                    filepath = os.path.join(self.current_batch_folders[camera_key], filename)
                    cv2.imwrite(filepath, frame)
                    logger.info(f"Imagem capturada: {filepath}")
                
                time.sleep(self.interval)

            except Exception as e:
                logger.error(f"Erro na captura da câmera {camera_key}: {str(e)}")
                # Tentar reconectar câmera IP
                if camera_config['type'] == 'ip':
                    try:
                        camera.open()
                    except:
                        pass

            camera.release()

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