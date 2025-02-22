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
        
        # Adicionar dicionários para controle
        self.last_capture_time = {}  # Última captura por câmera
        self.frames_count = {}       # Contador de frames
        self.fps_stats = {}          # Estatísticas de FPS
        self.last_fps_update = {}    # Última atualização do FPS

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
                        logger.info(f"Thread de captura iniciada para câmera {camera_key}")
                    else:
                        logger.error(f"Falha ao inicializar câmera {camera_key}")

        # Inicializar contadores
        for camera_id in self.cameras:
            self.frames_count[camera_id] = 0
            self.fps_stats[camera_id] = 0
            self.last_fps_update[camera_id] = datetime.now()

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

                    # Atualizar contadores
                    self.last_capture_time[camera_key] = now.isoformat()
                    self.frames_count[camera_key] = self.frames_count.get(camera_key, 0) + 1

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
            is_opened = camera.isOpened()
            logger.info(f"Câmera aberta: {is_opened}")
            if not is_opened:
                return False
            
            # Tentar capturar um frame
            ret, _ = camera.read()
            logger.info(f"Captura de frame: {'Sucesso' if ret else 'Falha'}")
            if not ret:
                return False
            
            # Verificar arquivos recentes
            now = datetime.now()
            current_minute = now.strftime("%Y%m%d_%H%M")
            last_minute = (now - timedelta(minutes=1)).strftime("%Y%m%d_%H%M")
            
            for minute in [current_minute, last_minute]:
                dir_path = os.path.join(BASE_IMAGE_DIR, line_id, minute)
                logger.info(f"Verificando diretório: {dir_path}")
                
                if os.path.exists(dir_path):
                    camera_files = [f for f in os.listdir(dir_path) 
                                  if f.startswith(f"{camera_id}_") and 
                                  f.endswith('.jpg')]
                    logger.info(f"Arquivos encontrados: {len(camera_files)}")
                    
                    if camera_files:
                        latest_file = max(camera_files, 
                            key=lambda x: os.path.getmtime(os.path.join(dir_path, x)))
                        latest_time = os.path.getmtime(os.path.join(dir_path, latest_file))
                        time_diff = time.time() - latest_time
                        
                        logger.info(f"Última imagem: {latest_file}")
                        logger.info(f"Tempo desde última imagem: {time_diff:.1f} segundos")
                        
                        if time_diff < 10:
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar status da câmera {line_id}_{camera_id}: {str(e)}")
            return False

    def get_camera_fps(self, camera_id: str) -> float:
        """Retorna FPS atual da câmera"""
        try:
            if camera_id not in self.cameras:
                return 0.0
                
            now = datetime.now()
            last_update = self.last_fps_update.get(camera_id)
            
            # Atualizar FPS a cada segundo
            if not last_update or (now - last_update).total_seconds() >= 1.0:
                frames = self.frames_count.get(camera_id, 0)
                self.fps_stats[camera_id] = frames
                self.frames_count[camera_id] = 0
                self.last_fps_update[camera_id] = now
                
            return self.fps_stats.get(camera_id, 0)
            
        except Exception as e:
            logger.error(f"Erro ao calcular FPS: {str(e)}")
            return 0.0

    def get_capture_status(self) -> dict:
        """Retorna status detalhado do sistema de captura"""
        print("\n=== BACKEND: Recebida solicitação de status ===")  # Log direto
        try:
            status = {
                'system_running': self.running,
                'cameras_configured': bool(self.cameras),
                'cameras': {},
                'is_capturing': False
            }
            
            print(f"Running: {self.running}")  # Log direto
            print(f"Câmeras: {list(self.cameras.keys())}")  # Log direto
            
            # Status por câmera
            for line_id, cameras in self.production_lines.items():
                for cam in cameras:
                    camera_key = f"{line_id}_usb_{cam['id']}"
                    camera_status = {
                        'name': cam['name'],
                        'position': cam['position'],
                        'is_configured': camera_key in self.cameras,
                        'is_opened': False,
                        'can_capture': False
                    }
                    
                    if camera_key in self.cameras:
                        camera = self.cameras[camera_key]
                        camera_status['is_opened'] = camera.isOpened()
                        if camera_status['is_opened']:
                            ret, _ = camera.read()
                            camera_status['can_capture'] = ret
                    
                    status['cameras'][camera_key] = camera_status
                    print(f"Câmera {camera_key}: {camera_status}")  # Log direto
            
            status['is_capturing'] = any(
                cam['can_capture'] for cam in status['cameras'].values()
            )
            
            print(f"Status final: {status}")  # Log direto
            return status
            
        except Exception as e:
            print(f"Erro ao obter status: {str(e)}")  # Log direto
            return {
                'system_running': False,
                'cameras_configured': False,
                'cameras': {},
                'is_capturing': False,
                'error': str(e)
            } 