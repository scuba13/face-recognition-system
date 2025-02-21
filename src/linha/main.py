import logging
import os
import time
import uuid
from threading import Thread

from linha.core.face_processor import FaceProcessor
from linha.core.image_capture import ImageCapture
from linha.db.handler import MongoDBHandler
from linha.config.settings import (
    PRODUCTION_LINES,
    CAPTURE_INTERVAL
)
from linha.utils.logger import setup_colored_logging

# Configurar logging colorido
setup_colored_logging(logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # Gerar ID único para esta instância
        instance_id = str(uuid.uuid4())
        os.environ['PROCESSOR_ID'] = instance_id
        logger.info(f"Iniciando processador com ID: {instance_id}")

        # Inicializar conexão com banco
        db_handler = MongoDBHandler()
        
        # Inicializar processador de faces
        face_processor = FaceProcessor(db_handler)
        processor_thread = Thread(target=face_processor.start_processing)
        processor_thread.daemon = True
        processor_thread.start()
        logger.info("Processador de faces iniciado")
        
        # Inicializar captura de imagens
        image_capture = ImageCapture(
            production_lines=PRODUCTION_LINES,
            interval=CAPTURE_INTERVAL
        )
        image_capture.set_db_handler(db_handler)
        
        # Iniciar captura
        logger.info("Iniciando captura de imagens...")
        image_capture.start_capture()

        # Loop principal
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Encerrando aplicação...")
    except Exception as e:
        logger.error(f"Erro na execução principal: {str(e)}")
    finally:
        if 'face_processor' in locals():
            face_processor.stop_processing()
        if 'image_capture' in locals():
            image_capture.stop_capture()

if __name__ == "__main__":
    main() 