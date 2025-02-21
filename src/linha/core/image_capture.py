import cv2
import time
import os
from datetime import datetime
import logging
from threading import Thread, Lock

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
        self.cameras = {}  # {camera_key: camera_instance}
        self.db_handler = None
        self.batch_dirs = {}  # {line_id: (dir, minute, image_count, start_time)}
        self.lock = Lock()

    def set_db_handler(self, db_handler):
        self.db_handler = db_handler

    def start_capture(self):
        """Inicia captura em todas as câmeras"""
        logger.info("Iniciando sistema de captura...")
        self.running = True
        
        # Inicializar todas as câmeras primeiro
        for line_id, cameras in self.production_lines.items():
            for camera_config in cameras:
                camera_key = f"{line_id}_usb_{camera_config['id']}"
                
                # Inicializar câmera apenas se não existir
                if camera_key not in self.cameras:
                    camera = init_camera(camera_config)
                    if camera:
                        self.cameras[camera_key] = camera
                        logger.info(f"Câmera {camera_config['name']} inicializada para linha {line_id}")
                        
                        # Criar e iniciar thread de captura
                        thread = Thread(
                            target=self._capture_loop,
                            args=(camera_key, line_id, camera_config)
                        )
                        thread.daemon = True
                        self.capture_threads.append(thread)
                        thread.start()

    def _get_or_create_batch_dir(self, line_id, minute_str):
        """Obtém ou cria diretório do lote de forma thread-safe"""
        with self.lock:
            if (line_id not in self.batch_dirs or 
                minute_str != self.batch_dirs[line_id][1]):  # [1] é current_minute
                
                # Se mudou o minuto ou é primeira vez
                if line_id in self.batch_dirs:
                    # Finalizar lote anterior
                    old_dir, _, image_count, start_time = self.batch_dirs[line_id]
                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"Finalizando lote: {old_dir}")
                    logger.info(f"Total de imagens capturadas: {image_count}")
                    logger.info(f"Tempo de captura: {elapsed:.2f}s")
                    
                    # Registrar lote no banco de dados
                    if image_count > 0 and self.db_handler:
                        self.db_handler.register_new_batch(line_id, old_dir)
                        logger.info(f"Lote registrado: {line_id} - {old_dir} - {image_count} imagens")
                
                # Criar novo diretório
                new_dir = os.path.join(BASE_IMAGE_DIR, line_id, minute_str)
                os.makedirs(new_dir, exist_ok=True)
                # Tupla com (diretório, minuto, contagem de imagens, tempo início)
                self.batch_dirs[line_id] = (new_dir, minute_str, 0, datetime.now())
                logger.info(f"Iniciando novo lote: {new_dir}")
                
            return self.batch_dirs[line_id][0]  # [0] é o diretório

    def _increment_batch_count(self, line_id):
        """Incrementa contador de imagens do lote"""
        with self.lock:
            if line_id in self.batch_dirs:
                dir_path, minute, count, start_time = self.batch_dirs[line_id]
                self.batch_dirs[line_id] = (dir_path, minute, count + 1, start_time)

    def _capture_loop(self, camera_key, line_id, camera_config):
        """Loop de captura para uma câmera"""
        try:
            camera = self.cameras[camera_key]
            if not camera:
                logger.error(f"Câmera {camera_key} não inicializada")
                return

            while self.running:
                try:
                    # Verificar se câmera ainda está ok
                    if not camera.isOpened():
                        logger.error(f"Câmera {camera_key} desconectada, tentando reconectar...")
                        camera = init_camera(camera_config)
                        if not camera:
                            time.sleep(5)
                            continue
                        self.cameras[camera_key] = camera

                    now = datetime.now()
                    minute_str = now.strftime("%Y%m%d_%H%M")
                    
                    # Obter diretório do lote atual
                    current_batch_dir = self._get_or_create_batch_dir(line_id, minute_str)
                    
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
                    
                    # Incrementar contador do lote
                    self._increment_batch_count(line_id)

                    time.sleep(self.interval)
                    
                except Exception as e:
                    logger.error(f"Erro no loop de captura: {str(e)}")
                    time.sleep(1)
                
        except Exception as e:
            logger.error(f"Erro fatal no loop de captura: {str(e)}")
        finally:
            if camera_key in self.cameras:
                try:
                    self.cameras[camera_key].release()
                except:
                    pass
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
        """Para a captura em todas as câmeras"""
        self.running = False
        
        # Esperar threads terminarem
        for thread in self.capture_threads:
            try:
                thread.join(timeout=5)  # Timeout de 5 segundos
            except Exception as e:
                logger.error(f"Erro ao finalizar thread: {str(e)}")
        
        # Liberar câmeras
        for camera_key, camera in self.cameras.items():
            try:
                camera.release()
            except Exception as e:
                logger.error(f"Erro ao liberar câmera {camera_key}: {str(e)}")
        
        self.cameras.clear()
        self.capture_threads.clear()
        logger.info("Captura finalizada") 