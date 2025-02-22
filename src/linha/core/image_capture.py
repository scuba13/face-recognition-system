import cv2
import time
import os
from datetime import datetime, timedelta
import logging
from threading import Thread, Lock

from linha.config.settings import (
    BASE_IMAGE_DIR, 
    CAPTURE_INTERVAL
)
from linha.utils.camera import setup_camera
from linha.utils.validators import check_image_quality

logger = logging.getLogger(__name__)

class ImageCapture:
    def __init__(self, production_lines, interval=CAPTURE_INTERVAL):
        self.production_lines = production_lines
        self.interval = interval  # Intervalo desejado entre capturas
        self.running = True
        self.capture_threads = []
        self.cameras = {}  # {camera_key: camera_instance}
        self.db_handler = None
        self.batch_dirs = {}  # {line_id: (dir, minute, image_count, start_time)}
        self.lock = Lock()
        self.last_capture_times = {}  # Dicionário para armazenar último tempo de captura por câmera

    def set_db_handler(self, db_handler):
        self.db_handler = db_handler

    def start_capture(self):
        """Inicia captura em todas as câmeras"""
        logger.info("Iniciando sistema de captura...")
        logger.info(f"Linhas configuradas: {self.production_lines}")
        
        self.running = True
        
        # Inicializar todas as câmeras primeiro
        for line_id, cameras in self.production_lines.items():
            for camera_config in cameras:
                camera_key = f"{line_id}_usb_{camera_config['id']}"
                logger.info(f"Tentando inicializar câmera: {camera_key}")
                
                # Inicializar câmera apenas se não existir
                if camera_key not in self.cameras:
                    camera_data = self.init_camera(line_id, camera_config)
                    if camera_data:  # Verificar se retornou dados da câmera
                        # Criar e iniciar thread de captura
                        thread = Thread(
                            target=self._capture_loop,
                            args=(camera_key, line_id, camera_config)
                        )
                        thread.daemon = True
                        self.capture_threads.append(thread)
                        thread.start()
                        logger.info(f"Thread de captura iniciada para câmera {camera_key}")
                    else:
                        logger.error(f"Falha ao inicializar câmera {camera_key}")

    def init_camera(self, line_id, camera_config):
        """Inicializa uma câmera"""
        try:
            camera_id = f"{line_id}_{camera_config['type']}_{camera_config['id']}"
            logger.info(f"Tentando inicializar câmera: {camera_id}")
            
            cap = setup_camera(camera_config)
            if cap:
                camera_data = {
                    'cap': cap,
                    'name': camera_config['name'],
                    'position': camera_config.get('position', 'unknown'),
                    'is_configured': True,
                    'is_opened': True,
                    'can_capture': True,
                    'frames_count': 0,
                    'fps_start_time': datetime.now()
                }
                self.cameras[camera_id] = camera_data
                self.last_capture_times[camera_id] = None  # Inicializar no dicionário
                logger.info(f"Câmera {camera_config['name']} inicializada para linha {line_id}")
                return camera_data
            return None
        except Exception as e:
            logger.error(f"Erro ao inicializar câmera: {str(e)}")
            return None

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
            while self.running:
                try:
                    camera = self.cameras.get(camera_key)
                    if not camera:
                        logger.error(f"Câmera {camera_key} não inicializada")
                        time.sleep(1)
                        continue

                    # Verificar se câmera ainda está ok
                    if not camera['cap'].isOpened():
                        logger.error(f"Câmera {camera_key} desconectada, tentando reconectar...")
                        if not self.init_camera(line_id, camera_config):
                            time.sleep(5)
                            continue

                    now = datetime.now()
                    minute_str = now.strftime("%Y%m%d_%H%M")
                    
                    # Obter diretório do lote atual
                    current_batch_dir = self._get_or_create_batch_dir(line_id, minute_str)
                    
                    # Capturar frame
                    ret, frame = camera['cap'].read()
                    if not ret:
                        logger.error(f"Erro ao capturar frame da câmera {camera_key}")
                        camera['can_capture'] = False
                        time.sleep(1)
                        continue
                    
                    camera['can_capture'] = True
                    
                    # Salvar frame
                    position = camera_config.get('position', 'default')
                    filename = f"{position}_frame_{now.strftime('%H%M%S')}.jpg"
                    filepath = os.path.join(current_batch_dir, filename)
                    cv2.imwrite(filepath, frame)
                    
                    # Incrementar contador do lote
                    self._increment_batch_count(line_id)

                    # Atualizar contadores e tempo
                    camera['frames_count'] += 1
                    self.last_capture_times[camera_key] = now.isoformat()  # Usar last_capture_times
                    
                    # Usar o intervalo definido para controlar capturas por minuto
                    time.sleep(self.interval)

                except Exception as e:
                    logger.error(f"Erro no loop de captura: {str(e)}")
                    time.sleep(1)
                
        except Exception as e:
            logger.error(f"Erro fatal no loop de captura: {str(e)}")
        finally:
            if camera_key in self.cameras:
                try:
                    self.cameras[camera_key]['cap'].release()
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
                camera['cap'].release()
            except Exception as e:
                logger.error(f"Erro ao liberar câmera {camera_key}: {str(e)}")
        
        self.cameras.clear()
        self.capture_threads.clear()
        logger.info("Captura finalizada")

    @property
    def is_capturing(self) -> bool:
        """Verifica se o sistema está capturando imagens"""
        try:
            # Sistema precisa estar rodando
            if not self.running:
                logger.info("Sistema não está rodando (self.running=False)")
                return False
            
            # Verificar se tem câmeras configuradas
            if not self.cameras:
                logger.info("Nenhuma câmera configurada (self.cameras vazio)")
                return False
            
            # Log das câmeras ativas
            logger.info(f"Câmeras configuradas: {list(self.cameras.keys())}")
            
            # Verificar se pelo menos uma câmera está ativa
            active_cameras = False
            for line_id, cameras in self.production_lines.items():
                for cam in cameras:
                    is_active = self.is_camera_active(line_id, cam['id'])
                    logger.info(f"Status câmera {line_id}_{cam['id']}: {'Ativa' if is_active else 'Inativa'}")
                    if is_active:
                        active_cameras = True
                        break
                if active_cameras:
                    break
            
            if not active_cameras:
                logger.info("Nenhuma câmera ativa encontrada")
                return False
            
            # Verificar se está gerando imagens
            now = datetime.now()
            current_minute = now.strftime("%Y%m%d_%H%M")
            dir_path = os.path.join(BASE_IMAGE_DIR, line_id, current_minute)
            
            logger.info(f"Verificando diretório: {dir_path}")
            
            if not os.path.exists(dir_path):
                logger.info(f"Diretório não existe: {dir_path}")
                return False
            
            # Verificar se tem imagens recentes
            files = [f for f in os.listdir(dir_path) if f.endswith('.jpg')]
            logger.info(f"Total de imagens encontradas: {len(files)}")
            
            if not files:
                logger.info("Nenhuma imagem encontrada")
                return False
            
            latest_file = max(files, key=lambda x: os.path.getmtime(os.path.join(dir_path, x)))
            latest_time = os.path.getmtime(os.path.join(dir_path, latest_file))
            time_diff = time.time() - latest_time
            
            logger.info(f"Última imagem: {latest_file}")
            logger.info(f"Tempo desde última imagem: {time_diff:.1f} segundos")
            
            return time_diff < 10
            
        except Exception as e:
            logger.error(f"Erro ao verificar status de captura: {str(e)}")
            return False

    def is_camera_active(self, line_id: str, camera_id: str) -> bool:
        """Verifica se uma câmera específica está ativa e capturando"""
        try:
            camera_key = f"{line_id}_usb_{camera_id}"
            logger.info(f"\nVerificando câmera {camera_key}:")
            
            if camera_key not in self.cameras:
                logger.info(f"Câmera {camera_key} não encontrada em self.cameras")
                return False
            
            camera = self.cameras[camera_key]
            
            # Verificar se câmera está aberta
            is_opened = camera['cap'].isOpened()
            logger.info(f"Câmera aberta: {is_opened}")
            if not is_opened:
                return False
            
            # Tentar capturar um frame
            ret, _ = camera['cap'].read()
            logger.info(f"Captura de frame: {'Sucesso' if ret else 'Falha'}")
            
            return ret and camera['can_capture']
            
        except Exception as e:
            logger.error(f"Erro ao verificar status da câmera {line_id}_{camera_id}: {str(e)}")
            return False

    def calculate_fps(self, camera_id):
        """Calcula FPS atual da câmera (apenas para monitoramento)"""
        camera = self.cameras.get(camera_id)
        if camera:
            elapsed = (datetime.now() - camera['fps_start_time']).total_seconds()
            if elapsed > 0:
                fps = camera['frames_count'] / elapsed
                # Resetar contagem a cada 5 segundos
                if elapsed > 5:
                    camera['frames_count'] = 0
                    camera['fps_start_time'] = datetime.now()
                return fps
        return 0

    def get_camera_status(self, camera_id):
        """Retorna status de uma câmera no formato esperado pelo frontend"""
        camera = self.cameras.get(camera_id)
        if not camera:
            return {
                'name': 'N/A',
                'position': 'unknown',
                'is_configured': False,
                'is_opened': False,
                'can_capture': False,
                'last_image_time': None,
                'fps': 0
            }
        
        return {
            'name': camera['name'],
            'position': camera.get('position', 'unknown'),
            'is_configured': camera['is_configured'],
            'is_opened': camera['cap'].isOpened(),
            'can_capture': camera['can_capture'],
            'last_image_time': self.last_capture_times.get(camera_id),
            'fps': self.calculate_fps(camera_id)
        }

    def get_status(self):
        """Retorna status completo no formato esperado pelo frontend"""
        try:
            logger.debug("Gerando status do sistema")
            status = {
                'system_running': self.running,
                'cameras_configured': len(self.cameras) > 0,
                'is_capturing': self.running and len(self.cameras) > 0,
                'cameras': {}
            }
            
            # Status por câmera no formato esperado
            for line_id, cameras in self.production_lines.items():
                for cam in cameras:
                    camera_id = f"{line_id}_usb_{cam['id']}"
                    logger.debug(f"Obtendo status da câmera {camera_id}")
                    status['cameras'][camera_id] = self.get_camera_status(camera_id)
            
            logger.debug(f"Status gerado: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Erro ao obter status: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'system_running': False,
                'cameras_configured': False,
                'is_capturing': False,
                'cameras': {}
            }

    def __getattr__(self, name):
        """Handler para atributos não encontrados"""
        if name == 'last_capture_time':
            import traceback
            stack = traceback.extract_stack()
            logger.error("Tentativa de acessar 'last_capture_time' - Stack trace:")
            for filename, line, func, text in stack[:-1]:  # -1 para excluir esta função
                logger.error(f"  File {filename}, line {line}, in {func}")
                logger.error(f"    {text}")
            
            # Retornar o primeiro valor de last_capture_times ou None
            if self.last_capture_times:
                camera_id = next(iter(self.last_capture_times.keys()))
                logger.warning(f"Retornando valor de {camera_id}: {self.last_capture_times[camera_id]}")
                return self.last_capture_times[camera_id]
            logger.warning("Nenhum valor de last_capture_times disponível")
            return None
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'") 