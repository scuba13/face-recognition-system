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
from linha.core.instance import set_image_capture, set_face_processor
from linha.api.server import start_api_server

def main():
    try:
        # Configurar logging colorido
        setup_colored_logging(logging.INFO)
        logger = logging.getLogger(__name__)
        
        print("\n=== Iniciando Sistema ===")
        
        # Inicializar conexão com banco
        db_handler = MongoDBHandler()
        
        # Criar instâncias
        image_capture = ImageCapture(
            production_lines=PRODUCTION_LINES,
            interval=CAPTURE_INTERVAL
        )
        face_processor = FaceProcessor(db_handler)
        
        # Salvar globalmente
        set_image_capture(image_capture)
        set_face_processor(face_processor)
        
        # Iniciar captura primeiro
        print("▶ Iniciando captura de imagens...")
        image_capture.set_db_handler(db_handler)
        image_capture.start_capture()
        print(f"✓ Captura iniciada com {len(image_capture.cameras)} câmeras")
        
        # Depois iniciar API
        api_thread = Thread(target=start_api_server)
        api_thread.daemon = True
        api_thread.start()
        print("✓ Servidor API iniciado na porta 8000")
        
        # Inicializar processador de faces
        processor_thread = Thread(target=face_processor.start_processing)
        processor_thread.daemon = True
        processor_thread.start()
        print("✓ Processador de faces iniciado")
        
        # Loop principal
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹ Encerrando aplicação...")
    except Exception as e:
        print(f"\n✗ Erro na execução principal: {str(e)}")
    finally:
        if 'face_processor' in locals():
            face_processor.stop_processing()
        if 'image_capture' in locals():
            image_capture.stop_capture()

if __name__ == "__main__":
    main() 