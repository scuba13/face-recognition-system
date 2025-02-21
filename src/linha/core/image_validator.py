import cv2
import logging
import numpy as np
from linha.config.settings import MIN_BLUR_THRESHOLD

logger = logging.getLogger(__name__)

class ImageValidator:
    def __init__(self, min_blur=MIN_BLUR_THRESHOLD):
        self.min_blur = min_blur

    def is_valid(self, image):
        """Verifica se a imagem tem qualidade suficiente"""
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
            
            return blur_value > self.min_blur
            
        except Exception as e:
            logger.error(f"Erro ao validar imagem: {str(e)}")
            return False

    def _check_blur(self, image):
        """Verifica se a imagem não está muito borrada"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
            return blur_value > self.min_blur
        except Exception:
            return False

    def _check_contrast(self, image):
        """Verifica se a imagem tem contraste suficiente"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            std_dev = np.std(gray)
            return std_dev > 30  # Valor arbitrário para contraste mínimo
        except Exception:
            return False 