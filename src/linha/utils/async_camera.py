"""
Módulo para captura de vídeo assíncrona de câmeras IP ou webcams.
Implementa captura assíncrona com buffer de frames otimizado para baixa latência.
"""
import cv2
import os
import time
import threading
from queue import Queue
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AsyncVideoCapture:
    """Classe para captura de vídeo assíncrona otimizada para baixa latência"""
    
    def __init__(self, source, buffer_size=3, resize_width=None):
        """
        Inicializa o capturador de vídeo
        
        Args:
            source: URL RTSP ou índice da câmera
            buffer_size: Tamanho máximo do buffer de frames (menor = menor latência)
            resize_width: Largura para redimensionar frames (None = sem redimensionamento)
        """
        self.source = source
        self.buffer_size = buffer_size
        self.resize_width = resize_width
        self.frame_queue = Queue(maxsize=self.buffer_size)
        self.stopped = False
        self.cap = None
        self.thread = None
        self.last_frame = None
        self.frame_count = 0
        self.fps = 0
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 2  # segundos
        self.drop_count = 0  # Contador de frames descartados
        self.last_frame_hash = None  # Para detectar frames duplicados
    
    def start(self):
        """Inicia a captura de vídeo em uma thread separada"""
        logger.info(f"Iniciando captura de vídeo assíncrona: {self.source}")
        
        # Configurar captura
        self._setup_capture()
        
        if not self.cap.isOpened():
            logger.warning("Erro ao abrir o stream de vídeo. Tentando novamente...")
            time.sleep(2)
            self._setup_capture()
            if not self.cap.isOpened():
                logger.error("Falha ao iniciar captura de vídeo após segunda tentativa.")
                return False
        
        # Iniciar thread de captura
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        logger.info("Thread de captura iniciada com sucesso")
        return True
    
    def _setup_capture(self):
        """Configura a captura de vídeo com otimizações para baixa latência"""
        logger.info(f"Configurando captura de vídeo: {self.source}")
        
        # Liberar recursos anteriores se existirem
        if self.cap is not None:
            self.cap.release()
        
        # Configurações avançadas para o OpenCV - otimizadas para RTSP
        if isinstance(self.source, str) and self.source.startswith("rtsp"):
            # Configurações mais robustas para RTSP com foco em baixa latência
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            
            # Se falhar, tentar com mais opções
            if not self.cap.isOpened():
                logger.warning("Falha ao abrir com configuração básica, tentando com mais opções...")
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;1024000|max_delay;500000"
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            
            # Se ainda falhar, tentar com URL modificada
            if not self.cap.isOpened():
                logger.warning("Falha ao abrir com variáveis de ambiente, tentando com URL modificada...")
                self.cap = cv2.VideoCapture(f"{self.source}?rtsp_transport=tcp", cv2.CAP_FFMPEG)
            
            # Configurações específicas para RTSP para reduzir latência
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduzir buffer para menor latência
        else:
            self.cap = cv2.VideoCapture(self.source)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Buffer pequeno para câmeras locais
        
        # Tentar configurar para usar hardware acceleration se disponível
        try:
            self.cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
        except:
            pass  # Ignorar se não suportado
        
        if self.cap.isOpened():
            # Verificar resolução real obtida
            largura_real = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            altura_real = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Stream de vídeo aberto com resolução: {largura_real}x{altura_real}")
            # Resetar contador de tentativas de reconexão
            self.reconnect_attempts = 0
    
    def _check_frame_corruption(self, frame):
        """
        Verifica se um frame está corrompido (faixas verdes ou outros artefatos)
        Retorna True se o frame parece estar corrompido
        """
        try:
            # Converter para HSV para detectar áreas verdes
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Definir faixa de cor verde
            lower_green = (40, 100, 100)
            upper_green = (80, 255, 255)
            
            # Criar máscara para pixels verdes
            mask = cv2.inRange(hsv, lower_green, upper_green)
            
            # Calcular porcentagem de pixels verdes
            green_pixels = cv2.countNonZero(mask)
            total_pixels = frame.shape[0] * frame.shape[1]
            green_percentage = (green_pixels / total_pixels) * 100
            
            # Se mais de 10% dos pixels são verde brilhante, provavelmente está corrompido
            return green_percentage > 10
        except Exception as e:
            logger.error(f"Erro ao verificar corrupção do frame: {str(e)}")
            return False
    
    def _is_duplicate_frame(self, frame):
        """Verifica se o frame é duplicado do anterior"""
        try:
            current_hash = hash(frame.tobytes())
            
            if self.last_frame_hash is not None and current_hash == self.last_frame_hash:
                return True
                
            self.last_frame_hash = current_hash
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar duplicação de frame: {str(e)}")
            return False
    
    def _update(self):
        """Atualiza continuamente o buffer de frames com otimizações para desempenho"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        last_drop_log = 0
        frame_interval = 1.0 / 30  # Limitar a taxa de FPS (30 por padrão)
        last_frame_time = time.time()
        
        # Descartar os primeiros frames (podem estar corrompidos)
        for _ in range(5):
            self.cap.grab()
            time.sleep(0.1)
        
        while not self.stopped:
            try:
                current_time = time.time()
                elapsed = current_time - last_frame_time
                
                # Limitar taxa de captura para não sobrecarregar o sistema
                if elapsed < frame_interval:
                    time.sleep(0.001)  # Pequena pausa
                    continue
                
                # Atualizar timestamp
                last_frame_time = current_time
                
                if not self.cap.isOpened():
                    logger.warning("Conexão perdida. Tentando reconectar...")
                    self._setup_capture()
                    if not self.cap.isOpened():
                        self.reconnect_attempts += 1
                        if self.reconnect_attempts > self.max_reconnect_attempts:
                            logger.error(f"Falha após {self.max_reconnect_attempts} tentativas. Aguardando mais tempo...")
                            time.sleep(5)
                            self.reconnect_attempts = 0
                        else:
                            time.sleep(self.reconnect_delay)
                        continue
            
                # Ler o próximo frame
                ret, frame = self.cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.warning(f"Múltiplos erros consecutivos ({consecutive_errors}). Reiniciando conexão...")
                        self.cap.release()
                        time.sleep(2)
                        self._setup_capture()
                        consecutive_errors = 0
                    else:
                        logger.warning(f"Erro ao ler frame ({consecutive_errors}/{max_consecutive_errors}). Aguardando...")
                        time.sleep(0.5)
                    continue
                else:
                    consecutive_errors = 0  # Resetar contador de erros consecutivos
                
                # Verificar se o frame está corrompido
                if self._check_frame_corruption(frame):
                    logger.warning("Frame corrompido detectado, descartando...")
                    continue
                
                # Verificar se o frame é duplicado
                if self._is_duplicate_frame(frame):
                    logger.warning("Frame duplicado detectado, descartando...")
                    continue
                
                # Redimensionar frame se necessário para melhorar desempenho
                if self.resize_width is not None and frame.shape[1] > self.resize_width:
                    # Calcular nova altura mantendo a proporção
                    aspect_ratio = frame.shape[0] / frame.shape[1]
                    new_height = int(self.resize_width * aspect_ratio)
                    frame = cv2.resize(frame, (self.resize_width, new_height), interpolation=cv2.INTER_AREA)
                
                # Calcular FPS
                self.fps_counter += 1
                if (time.time() - self.fps_start_time) > 1:
                    self.fps = self.fps_counter / (time.time() - self.fps_start_time)
                    self.fps_counter = 0
                    self.fps_start_time = time.time()
                
                # Incrementar contador de frames
                self.frame_count += 1
                
                # Se o buffer estiver cheio, remover o frame mais antigo e contar como descartado
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                        self.drop_count += 1
                        
                        # Logar a cada 100 frames descartados
                        if self.drop_count - last_drop_log >= 100:
                            logger.info(f"Buffer cheio: {self.drop_count} frames descartados até agora")
                            last_drop_log = self.drop_count
                    except:
                        pass
                
                # Adicionar o novo frame ao buffer
                try:
                    self.frame_queue.put_nowait(frame.copy())  # Usar cópia para evitar problemas de referência
                    self.last_frame = frame.copy()
                except:
                    pass
            except Exception as e:
                logger.error(f"Erro ao atualizar buffer de frames: {str(e)}")
                time.sleep(2)
    
    def read(self):
        """Lê o próximo frame do buffer com verificações de validade"""
        if self.stopped:
            return False, None
            
        if self.frame_queue.empty():
            if self.last_frame is not None:
                return True, self.last_frame.copy()  # Retornar o último frame válido se o buffer estiver vazio
            return False, None
        
        # Obter o próximo frame do buffer
        try:
            frame = self.frame_queue.get()
            if frame is None or frame.size == 0:
                # Frame inválido, retornar o último frame válido
                if self.last_frame is not None:
                    return True, self.last_frame.copy()
                return False, None
            return True, frame
        except:
            # Em caso de erro, retornar o último frame válido
            if self.last_frame is not None:
                return True, self.last_frame.copy()
            return False, None
    
    def get_fps(self):
        """Retorna o FPS atual"""
        return self.fps
    
    def get_frame_count(self):
        """Retorna o número total de frames capturados"""
        return self.frame_count
    
    def get_drop_count(self):
        """Retorna o número de frames descartados devido ao buffer cheio"""
        return self.drop_count
    
    def get_queue_size(self):
        """Retorna o tamanho atual da fila de frames"""
        return self.frame_queue.qsize()
    
    def stop(self):
        """Para a captura de vídeo com timeout reduzido para evitar bloqueio"""
        self.stopped = True
        try:
            if self.thread is not None:
                self.thread.join(timeout=0.5)  # Timeout reduzido para evitar bloqueio
            if self.cap is not None:
                self.cap.release()
            logger.info("Captura de vídeo encerrada")
        except Exception as e:
            logger.error(f"Erro ao encerrar captura de vídeo: {str(e)}") 