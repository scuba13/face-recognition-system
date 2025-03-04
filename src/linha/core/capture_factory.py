"""
Módulo para gerenciar diferentes tipos de captura de imagens.
"""
import logging
from linha.config.settings import CAPTURE_TYPE
from linha.core.image_capture import ImageCapture
from linha.core.motion_capture import MotionCapture

logger = logging.getLogger(__name__)

class CaptureFactory:
    """
    Fábrica para criar o tipo apropriado de captura de imagens
    baseado na configuração.
    """
    
    @staticmethod
    def create_capture(production_lines, capture_type=None):
        """
        Cria e retorna a instância apropriada de captura baseada no tipo especificado.
        
        Args:
            production_lines: Dicionário com configurações das linhas de produção
            capture_type: Tipo de captura ('interval' ou 'motion'). Se None, usa o valor de settings.
            
        Returns:
            Uma instância de ImageCapture ou MotionCapture
        """
        # Se não especificado, usar o valor das configurações
        if capture_type is None:
            capture_type = CAPTURE_TYPE
            
        logger.info(f"Criando sistema de captura do tipo: {capture_type}")
        
        if capture_type.lower() == 'motion':
            logger.info("Usando captura baseada em detecção de movimento")
            return MotionCapture(production_lines)
        else:
            logger.info("Usando captura baseada em intervalo fixo")
            return ImageCapture(production_lines) 