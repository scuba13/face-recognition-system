import cv2
import time
import os
from datetime import datetime
import logging
from threading import Thread

from linha.config.settings import (
    BASE_IMAGE_DIR, 
    CAPTURE_INTERVAL
)
from linha.utils.camera import init_camera
from linha.utils.validators import check_image_quality

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
            logger.info("Iniciando sistema de captura...")
            self.running = True
            
            # Iniciar thread de monitoramento
            self.monitor_thread = Thread(target=self._monitor_batches)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            # Iniciar threads de captura (uma por câmera)
            for line_id, cameras in self.production_lines.items():
                for camera_config in cameras:
                    camera_key = f"{line_id}_{camera_config['type']}_{camera_config.get('id', 0)}"
                    try:
                        camera = init_camera(camera_config)
                        if camera:
                            self.cameras[camera_key] = camera
                            thread = Thread(
                                target=self._capture_loop,
                                args=(camera_key, line_id, camera_config)
                            )
                            thread.daemon = True
                            thread.start()
                            self.capture_threads.append(thread)
                            
                            logger.info(f"Câmera {camera_config['name']} inicializada para linha {line_id}")
                    except Exception as e:
                        logger.error(f"Erro ao inicializar câmera {camera_key}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Erro ao iniciar captura: {str(e)}")
            self.running = False

    def _capture_loop(self, camera_key, line_id, camera_config):
        """Loop de captura para uma câmera"""
        try:
            camera = self.cameras[camera_key]
            current_batch_dir = None
            images_in_batch = 0
            batch_start_time = None
            
            while self.running:
                try:
                    # Verificar minuto atual
                    now = datetime.now()
                    minute_str = now.strftime("%Y%m%d_%H%M")
                    
                    # Se mudou o minuto, criar novo diretório
                    if minute_str != self.current_minute:
                        # Registrar fim do lote anterior se existir
                        if current_batch_dir and images_in_batch > 0:
                            logger.info(f"Finalizando lote: {current_batch_dir}")
                            logger.info(f"Total de imagens capturadas: {images_in_batch}")
                            logger.info(f"Tempo de captura: {(datetime.now() - batch_start_time).total_seconds():.2f}s")
                        
                        # Iniciar novo lote
                        self.current_minute = minute_str
                        current_batch_dir = os.path.join(BASE_IMAGE_DIR, line_id, minute_str)
                        os.makedirs(current_batch_dir, exist_ok=True)
                        images_in_batch = 0
                        batch_start_time = datetime.now()
                        logger.info(f"Iniciando novo lote: {current_batch_dir}")
                    
                    # Capturar frame
                    ret, frame = camera.read()
                    if not ret:
                        logger.error(f"Erro ao capturar frame da câmera {camera_key}")
                        time.sleep(1)
                        continue
                    
                    # Salvar frame
                    position = camera_config.get('position', 'default')
                    filename = f"{position}_frame_{now.strftime('%H%M%S')}.jpg"
                    filepath = os.path.join(current_batch_dir, filename)
                    cv2.imwrite(filepath, frame)
                    images_in_batch += 1

                    # Esperar intervalo
                    time.sleep(self.interval)
                    
                except Exception as e:
                    logger.error(f"Erro no loop de captura: {str(e)}")
                    time.sleep(1)
                
        except Exception as e:
            logger.error(f"Erro fatal no loop de captura: {str(e)}")
        finally:
            if camera_key in self.cameras:
                self.cameras[camera_key].release()
                del self.cameras[camera_key]

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
                                self.db_handler.register_new_batch(line_id, batch_path)
                                logger.info(f"Lote registrado: {line_id} - {last_registered_minute} - {len(images)} imagens")
                
                last_registered_minute = current_minute
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro no monitor de lotes: {str(e)}")
                time.sleep(5)

    def stop_capture(self):
        """Para a captura e libera recursos"""
        self.running = False
        
        # Aguardar threads finalizarem
        for thread in self.capture_threads:
            thread.join()
            
        # Liberar câmeras
        for camera in self.cameras.values():
            camera.release()
        self.cameras.clear()
        
        logger.info("Captura finalizada") 