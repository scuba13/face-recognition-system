import cv2
import logging
from linha.config.settings import MIN_BLUR_THRESHOLD

logger = logging.getLogger(__name__)

def check_image_quality(image):
    """
    Verifica se a imagem tem qualidade suficiente para processamento
    Args:
        image: Imagem OpenCV (numpy array)
    Returns:
        bool: True se a imagem tem qualidade suficiente
    """
    try:
        if image is None:
            return False
            
        # Verificar dimensões mínimas
        height, width = image.shape[:2]
        if width < 640 or height < 480:
            return False
            
        # Verificar nitidez
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        return blur_value > MIN_BLUR_THRESHOLD
        
    except Exception as e:
        logger.error(f"Erro ao verificar qualidade da imagem: {str(e)}")
        return False 