import logging
from datetime import datetime
from modules.image_capture import ImageCapture
from modules.face_processor import FaceProcessor
from modules.db_handler import MongoDBHandler
from modules.batch_processor import BatchProcessor
from config import (
    PRODUCTION_LINES,
    CAPTURE_INTERVAL,
    DELETE_AFTER_PROCESS,
    MONGODB_URI,
    BASE_IMAGE_DIR,
    ENABLE_METRICS
)
import os
import time
import uuid
from modules.metrics import MetricsCollector

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        # Gerar ID único para esta instância
        instance_id = str(uuid.uuid4())
        os.environ['PROCESSOR_ID'] = instance_id
        logger.info(f"Iniciando processador com ID: {instance_id}")

        db_handler = MongoDBHandler(connection_string=MONGODB_URI)
        face_processor = FaceProcessor(db_handler)
        batch_processor = BatchProcessor(face_processor)
        image_capture = ImageCapture(production_lines=PRODUCTION_LINES, interval=CAPTURE_INTERVAL)
        
        # Conectar image_capture ao db_handler
        image_capture.set_db_handler(db_handler)

        # Configurar variável de ambiente para controle de limpeza
        os.environ['DELETE_AFTER_PROCESS'] = str(DELETE_AFTER_PROCESS)
        os.environ['BASE_IMAGE_DIR'] = BASE_IMAGE_DIR

        # Inicializar coletor de métricas
        if ENABLE_METRICS:
            metrics_collector = MetricsCollector(db_handler)
            metrics_collector.start()
            logger.info("Coletor de métricas iniciado")

        # Iniciar processadores de lote
        batch_processor.start(PRODUCTION_LINES.keys())
        
        # Iniciar captura
        logger.info("Iniciando captura de imagens...")
        image_capture.start_capture()

        while True:
            time.sleep(1)  # Apenas para manter o programa rodando

    except Exception as e:
        logger.error(f"Erro na execução principal: {str(e)}")
        raise
    finally:
        if 'batch_processor' in locals():
            batch_processor.stop()
        if 'image_capture' in locals():
            image_capture.stop_capture()
        if 'metrics_collector' in locals() and ENABLE_METRICS:
            metrics_collector.stop()

if __name__ == "__main__":
    main() 