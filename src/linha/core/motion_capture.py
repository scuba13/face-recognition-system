"""
Módulo para captura de imagens baseada em detecção de movimento.
"""
import cv2
import time
import os
from datetime import datetime, timedelta
import logging
from threading import Thread, Lock
import numpy as np
from collections import deque

from linha.config.settings import (
    BASE_IMAGE_DIR,
    CAPTURE_INTERVAL,
    MOTION_THRESHOLD,
    MOTION_MIN_AREA,
    MOTION_DRAW_CONTOURS,
    MOTION_CAPTURE_FRAMES,
    MOTION_CAPTURE_INTERVAL
)
from linha.utils.camera import setup_camera
from linha.utils.validators import check_image_quality
from linha.utils.motion_detector import MotionDetector

logger = logging.getLogger(__name__)

class MotionCapture:
    """
    Classe para captura de imagens baseada em detecção de movimento.
    Captura múltiplos frames quando detecta movimento.
    """
    def __init__(self, production_lines, interval=CAPTURE_INTERVAL):
        self.production_lines = production_lines
        self.interval = interval  # Intervalo para verificação de movimento
        self.running = True
        self.capture_threads = {}  # {camera_key: thread}
        self.cameras = {}  # {camera_key: camera_instance}
        self.db_handler = None
        self.batch_dirs = {}  # {line_id: (dir, minute, image_count, start_time)}
        self.lock = Lock()
        self.last_capture_times = {}  # Dicionário para armazenar último tempo de captura por câmera
        self.previous_frames = {}  # Armazenar frames anteriores para detecção de movimento
        
        # Configurações de detecção de movimento
        self.motion_threshold = MOTION_THRESHOLD
        self.motion_min_area = MOTION_MIN_AREA
        self.motion_draw_contours = MOTION_DRAW_CONTOURS
        self.motion_capture_frames = MOTION_CAPTURE_FRAMES
        self.motion_capture_interval = MOTION_CAPTURE_INTERVAL
        
        # Inicializar detector de movimento
        self.motion_detector = MotionDetector(
            threshold=self.motion_threshold,
            area_minima=self.motion_min_area,
            desenhar_contornos=self.motion_draw_contours
        )
        
        logger.info(f"MotionCapture inicializado: threshold={self.motion_threshold}, "
                   f"min_area={self.motion_min_area}, frames={self.motion_capture_frames}, "
                   f"interval={self.motion_capture_interval}s")

    def set_db_handler(self, db_handler):
        """Define o manipulador de banco de dados"""
        self.db_handler = db_handler

    def start_capture(self):
        """Inicia captura em todas as câmeras"""
        logger.info("▶ Iniciando sistema de captura baseada em movimento...")
        logger.info(f"Linhas configuradas: {self.production_lines}")
        
        self.running = True
        
        # Inicializar todas as câmeras primeiro
        for line_id, cameras in self.production_lines.items():
            for camera_config in cameras:
                camera_key = f"{line_id}_{camera_config['type']}_{camera_config['id']}"
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
                        thread.start()
                        self.capture_threads[camera_key] = thread
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
                    'fps_start_time': datetime.now(),
                    'type': camera_config['type'],
                    'last_motion_time': None,
                    'motion_frames_buffer': deque(maxlen=2),  # Buffer para os últimos frames
                    'last_frame_hash': None  # Adicionado para detecção de frames duplicados
                }
                self.cameras[camera_id] = camera_data
                self.last_capture_times[camera_id] = None
                self.previous_frames[camera_id] = None
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
            last_check_time = time.time()
            
            while self.running:
                try:
                    camera = self.cameras.get(camera_key)
                    if not camera:
                        logger.error(f"Câmera {camera_key} não inicializada")
                        time.sleep(1)
                        continue

                    # Verificar se câmera ainda está ok
                    cap = camera['cap']
                    
                    # Verificar se é uma câmera assíncrona
                    is_async_camera = hasattr(cap, 'read') and hasattr(cap, 'stop') and hasattr(cap, 'get_fps')
                    
                    if not is_async_camera and not cap.isOpened():
                        logger.error(f"Câmera {camera_key} desconectada, tentando reconectar...")
                        if not self.init_camera(line_id, camera_config):
                            time.sleep(5)
                            continue

                    # Verificar se é hora de capturar um frame para verificação de movimento
                    current_time = time.time()
                    if current_time - last_check_time >= self.interval:
                        # Capturar frame para verificação
                        if is_async_camera:
                            # Para câmeras assíncronas, usar método read diretamente
                            ret, frame = cap.read()
                        else:
                            # Limpar buffer de frames antigos (para câmeras IP)
                            if camera_config.get('type') == 'ip':
                                # Descartar frames em buffer para garantir que capturamos o mais recente
                                for _ in range(5):  # Aumentado para 5 frames
                                    cap.grab()
                                
                            # Capturar frame
                            ret, frame = cap.read()
                        
                        # Para arquivos de vídeo, reiniciar quando chegar ao fim
                        if not ret and camera_config.get('type') == 'video':
                            logger.info(f"Fim do vídeo {camera_key}, reiniciando...")
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, frame = cap.read()
                        
                        if not ret or frame is None or frame.size == 0:
                            logger.error(f"Erro ao capturar frame da câmera {camera_key}")
                            camera['can_capture'] = False
                            time.sleep(1)
                            continue
                        
                        # Verificar se o frame está corrompido (faixas verdes)
                        try:
                            from linha.utils.camera import _check_frame_corruption
                            if _check_frame_corruption(frame):
                                logger.warning(f"Frame corrompido detectado na câmera {camera_key}, descartando...")
                                time.sleep(0.5)
                                continue
                        except Exception as e:
                            logger.error(f"Erro ao verificar corrupção do frame: {str(e)}")
                        
                        camera['can_capture'] = True
                        
                        # Verificar se o frame é diferente do anterior (para evitar duplicatas)
                        if 'last_frame_hash' in camera:
                            # Calcular hash simples do frame atual
                            current_hash = hash(frame.tobytes())
                            
                            if current_hash == camera['last_frame_hash']:
                                logger.warning(f"Frame duplicado detectado na câmera {camera_key}, tentando novamente...")
                                time.sleep(0.5)  # Pequena pausa
                                continue
                            
                            camera['last_frame_hash'] = current_hash
                        else:
                            # Primeira vez, apenas armazenar o hash
                            camera['last_frame_hash'] = hash(frame.tobytes())
                        
                        # Atualizar buffer de frames
                        camera['motion_frames_buffer'].append(frame.copy())
                        
                        # Verificar movimento se tiver pelo menos 2 frames
                        if len(camera['motion_frames_buffer']) >= 2:
                            frame_atual = camera['motion_frames_buffer'][-1]
                            frame_anterior = camera['motion_frames_buffer'][-2]
                            
                            # Detectar movimento
                            movimento_detectado, movimento_area, frame_marcado = self.motion_detector.detectar(
                                frame_atual, frame_anterior
                            )
                            
                            # Se detectou movimento, capturar sequência de frames
                            if movimento_detectado:
                                logger.info(f"Movimento detectado na câmera {camera_key}: área={movimento_area:.0f}")
                                camera['last_motion_time'] = datetime.now()
                                
                                # Capturar sequência de frames
                                self._capture_motion_sequence(camera_key, line_id, camera_config, frame_marcado, movimento_area)
                        
                        # Atualizar tempo da última verificação
                        last_check_time = current_time
                    
                    # Pequena pausa para não sobrecarregar CPU
                    time.sleep(0.01)

                except Exception as e:
                    logger.error(f"Erro no loop de captura: {str(e)}")
                    time.sleep(1)
                
        except Exception as e:
            logger.error(f"Erro fatal no loop de captura: {str(e)}")
        finally:
            if camera_key in self.cameras:
                try:
                    cap = self.cameras[camera_key]['cap']
                    # Verificar se é uma câmera assíncrona
                    if hasattr(cap, 'stop'):
                        cap.stop()
                    else:
                        cap.release()
                except:
                    pass
                del self.cameras[camera_key]

    def _capture_motion_sequence(self, camera_key, line_id, camera_config, first_frame, movimento_area):
        """
        Captura uma sequência de frames após detectar movimento
        
        Args:
            camera_key: Identificador da câmera
            line_id: Identificador da linha
            camera_config: Configuração da câmera
            first_frame: Primeiro frame com movimento (já capturado)
            movimento_area: Área do movimento detectado
        """
        try:
            camera = self.cameras.get(camera_key)
            if not camera or not camera['can_capture']:
                return
                
            now = datetime.now()
            minute_str = now.strftime("%Y%m%d_%H%M")
            
            # Obter diretório do lote atual
            current_batch_dir = self._get_or_create_batch_dir(line_id, minute_str)
            
            # Verificar se o primeiro frame está corrompido
            try:
                from linha.utils.camera import _check_frame_corruption
                if _check_frame_corruption(first_frame):
                    logger.warning(f"Primeiro frame corrompido na sequência de movimento, descartando...")
                    return
            except Exception as e:
                logger.error(f"Erro ao verificar corrupção do primeiro frame: {str(e)}")
            
            # Salvar o primeiro frame (já capturado)
            position = camera_config.get('position', 'default')
            timestamp = now.strftime("%H%M%S_%f")[:-3]  # Milissegundos
            filename = f"{position}_motion_{movimento_area:.0f}_{timestamp}_1.jpg"
            filepath = os.path.join(current_batch_dir, filename)
            cv2.imwrite(filepath, first_frame)
            
            # Incrementar contador do lote
            self._increment_batch_count(line_id)
            
            # Atualizar contadores e tempo
            camera['frames_count'] += 1
            self.last_capture_times[camera_key] = now.isoformat()
            
            logger.info(f"Frame 1/{self.motion_capture_frames} capturado: {filename}")
            
            # Armazenar hash do último frame para evitar duplicatas
            last_frame_hash = hash(first_frame.tobytes())
            
            # Verificar se é uma câmera assíncrona
            cap = camera['cap']
            is_async_camera = hasattr(cap, 'read') and hasattr(cap, 'stop') and hasattr(cap, 'get_fps')
            
            # Capturar frames adicionais
            for i in range(2, self.motion_capture_frames + 1):
                # Pequena pausa entre capturas
                time.sleep(self.motion_capture_interval)
                
                # Capturar próximo frame
                if is_async_camera:
                    # Para câmeras assíncronas, usar método read diretamente
                    ret, frame = cap.read()
                else:
                    # Limpar buffer para câmeras IP
                    if camera_config.get('type') == 'ip':
                        # Descartar frames em buffer para garantir que capturamos o mais recente
                        for _ in range(3):
                            cap.grab()
                    
                    # Capturar frame
                    ret, frame = cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    logger.error(f"Erro ao capturar frame {i}/{self.motion_capture_frames}")
                    break
                
                # Verificar se o frame está corrompido
                try:
                    from linha.utils.camera import _check_frame_corruption
                    if _check_frame_corruption(frame):
                        logger.warning(f"Frame corrompido na sequência de movimento, tentando novamente...")
                        # Tentar mais uma vez após uma pausa
                        time.sleep(self.motion_capture_interval * 2)
                        ret, frame = cap.read()
                        if not ret or frame is None or frame.size == 0:
                            logger.error(f"Erro ao capturar frame alternativo {i}/{self.motion_capture_frames}")
                            break
                        
                        if _check_frame_corruption(frame):
                            logger.error(f"Frame alternativo ainda corrompido, pulando frame {i}")
                            continue
                except Exception as e:
                    logger.error(f"Erro ao verificar corrupção do frame: {str(e)}")
                
                # Verificar se o frame é diferente do anterior
                current_hash = hash(frame.tobytes())
                if current_hash == last_frame_hash:
                    logger.warning(f"Frame duplicado detectado na sequência de movimento, tentando novamente...")
                    # Tentar mais uma vez após uma pausa maior
                    time.sleep(self.motion_capture_interval * 2)
                    ret, frame = cap.read()
                    if not ret or frame is None or frame.size == 0:
                        logger.error(f"Erro ao capturar frame alternativo {i}/{self.motion_capture_frames}")
                        break
                    
                    current_hash = hash(frame.tobytes())
                    if current_hash == last_frame_hash:
                        logger.error(f"Frame ainda duplicado, pulando frame {i}")
                        continue
                
                # Atualizar hash do último frame
                last_frame_hash = current_hash
                
                # Salvar frame
                now = datetime.now()
                timestamp = now.strftime("%H%M%S_%f")[:-3]  # Milissegundos
                filename = f"{position}_motion_{movimento_area:.0f}_{timestamp}_{i}.jpg"
                filepath = os.path.join(current_batch_dir, filename)
                cv2.imwrite(filepath, frame)
                
                # Incrementar contador do lote
                self._increment_batch_count(line_id)
                
                # Atualizar contadores e tempo
                camera['frames_count'] += 1
                self.last_capture_times[camera_key] = now.isoformat()
                
                logger.info(f"Frame {i}/{self.motion_capture_frames} capturado: {filename}")
                
        except Exception as e:
            logger.error(f"Erro ao capturar sequência de movimento: {str(e)}")

    @property
    def is_capturing(self) -> bool:
        """Verifica se o sistema está capturando imagens"""
        return self.running and len(self.cameras) > 0

    def stop_capture(self):
        """Para a captura em todas as câmeras"""
        logger.info("Parando sistema de captura...")
        self.running = False
        
        # Aguardar threads terminarem
        for camera_key, thread in self.capture_threads.items():
            if thread.is_alive():
                thread.join(timeout=2)
                
        # Liberar recursos das câmeras
        for camera_key, camera in list(self.cameras.items()):
            try:
                camera['cap'].release()
            except:
                pass
            
        self.cameras.clear()
        self.capture_threads.clear()
        logger.info("Sistema de captura parado")

    def is_camera_active(self, line_id: str, camera_id: str) -> bool:
        """Verifica se uma câmera específica está ativa e capturando"""
        try:
            camera_key = f"{line_id}_ip_{camera_id}"
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
                'last_motion_time': None,
                'fps': 0
            }
        
        return {
            'name': camera['name'],
            'position': camera.get('position', 'unknown'),
            'is_configured': camera['is_configured'],
            'is_opened': camera['cap'].isOpened(),
            'can_capture': camera['can_capture'],
            'last_image_time': self.last_capture_times.get(camera_id),
            'last_motion_time': camera['last_motion_time'].isoformat() if camera['last_motion_time'] else None,
            'fps': self.calculate_fps(camera_id),
            'capture_type': 'motion'
        }

    def get_status(self):
        """Retorna status completo no formato esperado pelo frontend"""
        try:
            logger.debug("Gerando status do sistema")
            status = {
                'system_running': self.running,
                'cameras_configured': len(self.cameras) > 0,
                'is_capturing': self.is_capturing,
                'capture_type': 'motion',
                'cameras': {}
            }
            
            # Status por câmera no formato esperado
            for line_id, cameras in self.production_lines.items():
                for cam in cameras:
                    camera_id = f"{line_id}_{cam['type']}_{cam['id']}"
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
                'capture_type': 'motion',
                'cameras': {}
            } 