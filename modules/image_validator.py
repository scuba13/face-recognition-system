import cv2
import numpy as np
import logging
from config import MIN_IMAGE_SIZE, MAX_IMAGE_SIZE

logger = logging.getLogger(__name__)

class ImageValidator:
    @staticmethod
    def validate_image(image_path):
        """Valida uma imagem antes do processamento"""
        try:
            # Tentar ler a imagem
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Imagem corrompida ou formato não suportado: {image_path}")
                return False, "Imagem corrompida ou formato não suportado"

            # Verificar dimensões
            height, width = img.shape[:2]
            if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
                return False, f"Imagem muito pequena: {width}x{height}"
            if width > MAX_IMAGE_SIZE or height > MAX_IMAGE_SIZE:
                return False, f"Imagem muito grande: {width}x{height}"

            # Verificar se não é uma imagem toda preta ou branca
            if np.mean(img) < 5 or np.mean(img) > 250:
                return False, "Imagem muito escura ou clara"

            # Verificar blur
            laplacian_var = cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            if laplacian_var < 100:  # Valor ajustável
                return False, "Imagem muito borrada"

            return True, "OK"

        except Exception as e:
            logger.error(f"Erro ao validar imagem {image_path}: {str(e)}")
            return False, str(e) 