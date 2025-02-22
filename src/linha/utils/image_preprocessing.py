import cv2
import numpy as np
import logging
from linha.config.settings import (
    MIN_BLUR_THRESHOLD,
    ENABLE_PREPROCESSING
)

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    # Constantes de pré-processamento
    IMAGE_MAX_SIZE = 800
    JPEG_QUALITY = 85
    
    @staticmethod
    def enhance_image(image):
        """
        Aplica técnicas de pré-processamento para melhorar a qualidade da imagem
        """
        try:
            if not ENABLE_PREPROCESSING:
                return image
                
            # 1. Redimensionar se maior que o limite
            if max(image.shape[:2]) > ImagePreprocessor.IMAGE_MAX_SIZE:
                image = ImagePreprocessor._resize_image(image)
            
            # 2. Normalização de iluminação
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl,a,b))
            enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            # 3. Redução de ruído
            denoised = cv2.fastNlMeansDenoisingColored(
                enhanced,
                None,
                h=10,
                hColor=10,
                templateWindowSize=7,
                searchWindowSize=21
            )
            
            # 4. Ajuste de contraste
            gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            contrast_enhanced = clahe.apply(gray)
            
            # 5. Sharpening
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # 6. Blend final
            result = cv2.addWeighted(
                sharpened, 0.7,
                denoised, 0.3,
                0
            )
            
            # Verificar qualidade
            if cv2.Laplacian(result, cv2.CV_64F).var() < MIN_BLUR_THRESHOLD:
                logger.warning("Baixa qualidade após pré-processamento, usando original")
                return image
                
            return result
            
        except Exception as e:
            logger.error(f"Erro no pré-processamento: {str(e)}")
            return image

    @staticmethod
    def check_image_quality(image):
        """Verifica qualidade da imagem"""
        try:
            # Verificar nitidez
            laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
            
            # Verificar contraste
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            contrast = gray.std()
            
            # Verificar brilho
            brightness = np.mean(gray)
            
            return {
                'sharpness': laplacian_var,
                'contrast': contrast,
                'brightness': brightness,
                'is_good': laplacian_var > MIN_BLUR_THRESHOLD
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar qualidade: {str(e)}")
            return None

    @staticmethod
    def _resize_image(image: np.ndarray) -> np.ndarray:
        """Redimensiona imagem mantendo proporção"""
        height, width = image.shape[:2]
        max_size = ImagePreprocessor.IMAGE_MAX_SIZE
        
        if height > width:
            new_height = max_size
            new_width = int(width * (max_size/height))
        else:
            new_width = max_size
            new_height = int(height * (max_size/width))
            
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Otimiza imagem para processamento facial
    Args:
        image: Imagem em formato numpy array (BGR)
    Returns:
        Imagem pré-processada
    """
    try:
        if not ENABLE_PREPROCESSING:
            return image
            
        # 1. Redimensionar se maior que o limite
        if max(image.shape[:2]) > ImagePreprocessor.IMAGE_MAX_SIZE:
            image = ImagePreprocessor._resize_image(image)
            
        # 2. Comprimir usando JPEG
        if ImagePreprocessor.JPEG_QUALITY < 100:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), ImagePreprocessor.JPEG_QUALITY]
            _, buffer = cv2.imencode('.jpg', image, encode_param)
            image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            
        return image
        
    except Exception as e:
        print(f"✗ Erro no pré-processamento: {str(e)}")
        return image