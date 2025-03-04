import cv2
import logging
import time
import os

logger = logging.getLogger(__name__)

def setup_camera(camera_config):
    """
    Configura uma câmera baseada nas configurações.
    Suporta câmeras USB e câmeras IP (RTSP, HTTP).
    """
    try:
        camera_type = camera_config['type']
        camera_id = camera_config['id']
        
        logger.info(f"Configurando câmera: {camera_type} - {camera_id}")
        
        if camera_type == 'ip':
            # Para câmeras IP, configurar parâmetros específicos do RTSP
            logger.info(f"Configurando câmera IP: {camera_id}")
            
            # Configurar parâmetros do OpenCV para RTSP
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            
            # Criar objeto de captura com parâmetros específicos para RTSP
            cap = cv2.VideoCapture(camera_id, cv2.CAP_FFMPEG)
            
            # Configurar buffer pequeno para reduzir latência
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Tentar configurar timeout (nem todas as versões do OpenCV suportam)
            try:
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5 segundos
            except:
                logger.warning("Não foi possível configurar timeout para a câmera RTSP")
        else:
            # Para câmeras USB
            cap = cv2.VideoCapture(camera_id)
        
        # Configurar resolução
        if 'resolution' in camera_config:
            width, height = camera_config['resolution']
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Verificar se a câmera foi aberta com sucesso
        if not cap.isOpened():
            raise Exception(f"Não foi possível abrir a câmera {camera_id}")
        
        # Para câmeras IP, tentar ler um frame para verificar conexão
        if camera_type == 'ip':
            # Tentar ler com timeout
            start_time = time.time()
            timeout = 10  # 10 segundos para RTSP
            
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if ret:
                    logger.info(f"Frame capturado com sucesso da câmera {camera_id}")
                    break
                time.sleep(0.5)
                logger.info("Tentando ler frame...")
            
            if time.time() - start_time >= timeout:
                raise Exception(f"Timeout ao tentar capturar frame da câmera {camera_id}")
            
        logger.info(f"Câmera inicializada: {camera_config['name']}")
        return cap
        
    except Exception as e:
        logger.error(f"Erro ao configurar câmera: {str(e)}")
        return None 