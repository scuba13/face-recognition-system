import cv2
import numpy as np
import logging
from linha.config.settings import MIN_BLUR_THRESHOLD

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    @staticmethod
    def enhance_image(image):
        """
        Aplica técnicas de pré-processamento para melhorar a qualidade da imagem
        """
        try:
            # 1. Normalização de iluminação
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl,a,b))
            enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            # 2. Redução de ruído
            denoised = cv2.fastNlMeansDenoisingColored(
                enhanced,
                None,
                h=10,
                hColor=10,
                templateWindowSize=7,
                searchWindowSize=21
            )
            
            # 3. Ajuste de contraste
            gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            contrast_enhanced = clahe.apply(gray)
            
            # 4. Sharpening
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # 5. Blend final
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