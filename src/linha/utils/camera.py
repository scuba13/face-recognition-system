import cv2
import logging

logger = logging.getLogger(__name__)

def setup_camera(camera_config):
    """
    Configura uma câmera baseada nas configurações.
    A taxa de captura é controlada pelo CAPTURE_INTERVAL nas configurações.
    """
    try:
        cap = cv2.VideoCapture(camera_config['id'])
        
        # Configurar resolução
        if 'resolution' in camera_config:
            width, height = camera_config['resolution']
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Não definir FPS para usar o máximo nativo da câmera
        
        if not cap.isOpened():
            raise Exception(f"Não foi possível abrir a câmera {camera_config['id']}")
            
        logger.info(f"Câmera inicializada: {camera_config['name']}")
        return cap
        
    except Exception as e:
        logger.error(f"Erro ao configurar câmera: {str(e)}")
        return None 