import cv2
import logging

logger = logging.getLogger(__name__)

def init_camera(config):
    """Inicializa uma câmera"""
    try:
        cap = cv2.VideoCapture(config['id'])
        if not cap.isOpened():
            raise Exception("Câmera não pôde ser aberta")
            
        # Configurar
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['resolution'][0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['resolution'][1])
        cap.set(cv2.CAP_PROP_FPS, config['fps'])
        
        logger.info(f"Câmera inicializada: {config['name']}")
        return cap
        
    except Exception as e:
        logger.error(f"Erro ao inicializar câmera {config['name']}: {str(e)}")
        return None 