import logging
from datetime import datetime
from modules.image_capture import ImageCapture
from modules.face_processor import FaceProcessor
from modules.db_handler import MongoDBHandler
from config import (
    PRODUCTION_LINES,
    CAPTURE_INTERVAL,
    MONGODB_URI,
)
import os
import time
import uuid
from threading import Thread

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Gerar ID único para esta instância
        instance_id = str(uuid.uuid4())
        os.environ['PROCESSOR_ID'] = instance_id
        logger.info(f"Iniciando processador com ID: {instance_id}")

        # Inicializar conexão com banco
        db_handler = MongoDBHandler(connection_string=MONGODB_URI)
        logger.info("Conexão com MongoDB estabelecida")
        
        # Inicializar processador de faces
        face_processor = FaceProcessor(db_handler)
        
        # Iniciar thread do processador
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

    except Exception as e:
        logger.error(f"Erro na execução principal: {str(e)}")
        raise
    finally:
        if 'face_processor' in locals():
            face_processor.stop_processing()
        if 'image_capture' in locals():
            image_capture.stop_capture()

if __name__ == "__main__":
    main()