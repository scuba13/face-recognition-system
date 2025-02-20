import cv2
import logging
import os
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