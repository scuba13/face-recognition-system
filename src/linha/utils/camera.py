import cv2
import logging
import time
import os
import subprocess
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_camera(camera_config):
    """
    Configura uma câmera baseada nas configurações.
    Suporta câmeras USB e câmeras IP (RTSP, HTTP).
    
    Args:
        camera_config: Dicionário com configurações da câmera
        
    Returns:
        Objeto VideoCapture ou AsyncVideoCapture
    """
    try:
        camera_type = camera_config['type']
        
        logger.info(f"Configurando câmera: {camera_type}")
        
        if camera_type == 'ip':
            # Para câmeras IP, configurar parâmetros específicos do RTSP
            url = camera_config.get('url')
            if not url:
                # Tentar obter a URL do campo 'id' (compatibilidade)
                url = camera_config.get('id')
                if not url:
                    raise Exception("URL não fornecida para câmera IP")
                
            logger.info(f"Configurando câmera IP: {url}")
            
            # Obter protocolo de transporte (tcp ou udp)
            rtsp_transport = camera_config.get('rtsp_transport', 'tcp')
            logger.info(f"Usando protocolo de transporte RTSP: {rtsp_transport}")
            
            # Verificar se a URL é RTSP
            is_rtsp = url.lower().startswith('rtsp://')
            
            # Tentar usar AsyncVideoCapture para RTSP se disponível
            if is_rtsp:
                try:
                    from linha.utils.async_camera import AsyncVideoCapture
                    logger.info("Usando captura assíncrona para câmera RTSP")
                    
                    # Criar capturador assíncrono
                    cap = AsyncVideoCapture(url, buffer_size=3)
                    
                    # Iniciar captura
                    if cap.start():
                        logger.info("Captura assíncrona iniciada com sucesso")
                        return cap
                    else:
                        logger.warning("Falha ao iniciar captura assíncrona, usando método padrão")
                except ImportError:
                    logger.warning("AsyncVideoCapture não disponível, usando método padrão")
                except Exception as e:
                    logger.warning(f"Erro ao usar captura assíncrona: {str(e)}, usando método padrão")
            
            # Configurar parâmetros do OpenCV para RTSP
            if rtsp_transport == 'tcp':
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            else:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
            
            # Tentar diferentes abordagens para abrir a câmera RTSP
            # Abordagem 1: Usar VideoCapture diretamente
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            
            if not cap.isOpened():
                logger.warning(f"Falha ao abrir câmera com abordagem padrão, tentando abordagem alternativa...")
                
                # Abordagem 2: Tentar com parâmetros adicionais para TCP
                if rtsp_transport == 'tcp':
                    cap = cv2.VideoCapture(f"{url}?rtsp_transport=tcp", cv2.CAP_FFMPEG)
                else:
                    cap = cv2.VideoCapture(f"{url}?rtsp_transport=udp", cv2.CAP_FFMPEG)
            
            if not cap.isOpened():
                logger.warning(f"Falha ao abrir câmera com abordagem alternativa, tentando última abordagem...")
                
                # Abordagem 3: Tentar com parâmetros de baixa latência
                if rtsp_transport == 'tcp':
                    cap = cv2.VideoCapture(f"{url}?rtsp_transport=tcp&buffer_size=0&drop_frame_if_late=1", cv2.CAP_FFMPEG)
                else:
                    cap = cv2.VideoCapture(f"{url}?rtsp_transport=udp&buffer_size=0&drop_frame_if_late=1", cv2.CAP_FFMPEG)
            
            # Configurar buffer pequeno para reduzir latência
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Tentar configurar timeout (nem todas as versões do OpenCV suportam)
            try:
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5 segundos
            except:
                pass
                
            # Verificar se a câmera foi aberta com sucesso
            if not cap.isOpened():
                # Última tentativa: abordagem mais simples possível
                logger.warning("Todas as abordagens falharam, tentando método mais simples...")
                try:
                    # Limpar variáveis de ambiente que podem estar causando problemas
                    if "OPENCV_FFMPEG_CAPTURE_OPTIONS" in os.environ:
                        del os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"]
                    
                    # Tentar abrir a câmera sem opções especiais
                    cap = cv2.VideoCapture(url)
                    
                    if not cap.isOpened():
                        raise Exception(f"Não foi possível abrir a câmera {url} com nenhuma abordagem")
                except Exception as e:
                    logger.error(f"Erro na última tentativa: {str(e)}")
                    raise Exception(f"Não foi possível abrir a câmera {camera_config}")
            
            # Verificar se conseguimos ler um frame
            ret, frame = cap.read()
            if not ret or frame is None or frame.size == 0:
                logger.error(f"Câmera aberta, mas não foi possível ler um frame: {url}")
                cap.release()
                raise Exception(f"Câmera aberta, mas não foi possível ler um frame: {url}")
                
            logger.info(f"Câmera IP configurada com sucesso: {url}")
            return cap
        
        elif camera_type == 'video':
            # Para arquivos de vídeo
            video_path = camera_config.get('path')
            if not video_path:
                raise Exception("Caminho do vídeo não fornecido")
                
            logger.info(f"Configurando arquivo de vídeo: {video_path}")
            cap = cv2.VideoCapture(video_path)
            
        else:
            # Para câmeras USB
            camera_id = camera_config.get('id', 0)  # Default para câmera 0 se não especificado
            logger.info(f"Configurando câmera USB: {camera_id}")
            cap = cv2.VideoCapture(camera_id)
        
        # Configurar resolução
        if 'resolution' in camera_config:
            width, height = camera_config['resolution']
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Verificar se a câmera foi aberta com sucesso
        if not cap.isOpened():
            raise Exception(f"Não foi possível abrir a câmera {camera_config}")
        
        # Para câmeras IP, tentar ler um frame para verificar conexão
        if camera_type == 'ip':
            # Tentar ler com timeout
            start_time = time.time()
            timeout = 10  # 10 segundos para RTSP
            
            # Descartar os primeiros frames (podem estar corrompidos)
            for _ in range(10):
                cap.grab()
            
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    # Verificar se o frame está corrompido (faixas verdes)
                    if _check_frame_corruption(frame):
                        logger.warning("Frame capturado com possível corrupção, tentando novamente...")
                        time.sleep(0.5)
                        continue
                    
                    logger.info(f"Frame capturado com sucesso da câmera {url}")
                    # Descartar este frame para garantir que o próximo seja novo
                    break
                time.sleep(0.5)
                logger.info("Tentando ler frame...")
            
            if time.time() - start_time >= timeout:
                raise Exception(f"Timeout ao tentar capturar frame da câmera {url}")
            
        logger.info(f"Câmera inicializada: {camera_config.get('name', 'Sem nome')}")
        return cap
        
    except Exception as e:
        logger.error(f"Erro ao configurar câmera: {str(e)}")
        return None

def _check_frame_corruption(frame):
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