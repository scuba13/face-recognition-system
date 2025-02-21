import cv2
import logging
import os
import numpy as np
from config import MIN_IMAGE_SIZE, MAX_IMAGE_SIZE, MIN_BLUR_THRESHOLD

logger = logging.getLogger(__name__)

class ImageValidator:
    def __init__(self):
        self.min_size = MIN_IMAGE_SIZE
        self.max_size = MAX_IMAGE_SIZE
        self.blur_threshold = MIN_BLUR_THRESHOLD

    def validate_image(self, image_path):
        """
        Valida uma imagem verificando:
        - Se o arquivo existe
        - Se pode ser aberto como imagem
        - Se tem tamanho mínimo/máximo adequado
        - Se não está muito borrada
        
        Returns:
            (bool, str): (is_valid, message)
        """
        try:
            # Verificar se arquivo existe
            if not os.path.exists(image_path):
                return False, "Arquivo não existe"
                
            # Tentar abrir imagem
            img = cv2.imread(image_path)
            if img is None:
                return False, "Não foi possível abrir a imagem"
                
            # Verificar dimensões
            height, width = img.shape[:2]
            if width < self.min_size or height < self.min_size:
                return False, f"Imagem muito pequena: {width}x{height}"
            if width > self.max_size or height > self.max_size:
                return False, f"Imagem muito grande: {width}x{height}"
                
            # Verificar nitidez
            blur = cv2.Laplacian(img, cv2.CV_64F).var()
            if blur < self.blur_threshold:
                return False, f"Imagem muito borrada: {blur:.2f}"
                
            return True, "Imagem válida"
            
        except Exception as e:
            logger.error(f"Erro ao validar imagem {image_path}: {str(e)}")
            return False, f"Erro na validação: {str(e)}"

    def is_valid(self, image):
        """
        Valida se a imagem tem qualidade suficiente
        Retorna True se a imagem passar em todas as validações
        """
        try:
            # Verificar dimensões
            height, width = image.shape[:2]
            if width < self.min_size or height < self.min_size:
                return False
            if width > self.max_size or height > self.max_size:
                return False

            # Verificar se não está muito borrada
            if not self._check_blur(image):
                return False

            # Verificar se tem contraste suficiente
            if not self._check_contrast(image):
                return False

            return True

        except Exception as e:
            return False

    def _check_blur(self, image):
        """Verifica se a imagem não está muito borrada"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
        return blur_value > self.blur_threshold

    def _check_contrast(self, image):
        """Verifica se a imagem tem contraste suficiente"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray)
        return std_dev > 30  # Valor arbitrário para contraste mínimo 