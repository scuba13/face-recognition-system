import logging
import os
import time
import uuid
from threading import Thread, Event
from fastapi import FastAPI
import threading

from linha.core.face_processor import FaceProcessor
from linha.core.image_capture import ImageCapture
from linha.db.handler import MongoDBHandler
from linha.config.settings import (
    PRODUCTION_LINES,
    CAPTURE_INTERVAL
)
from linha.utils.logger import setup_colored_logging
from linha.core.instance import set_image_capture, set_face_processor, set_db_handler
from linha.api.server import start_api_server
from linha.api.routes import router  # Importar rotas
import uvicorn

def main():
    try:
        # Configurar logging colorido
        setup_colored_logging(logging.INFO)
        logger = logging.getLogger(__name__)
        
        print("\n=== Iniciando Sistema ===")
        
        # 1. Inicializar conexão com banco primeiro
        print("▶ Iniciando conexão com banco...")
        db_handler = MongoDBHandler()
        print("✓ Banco conectado")
        
        # 2. Iniciar API em thread separada
        print("▶ Iniciando servidor API...")
        api_ready = Event()
        api_thread = Thread(target=start_api_server, args=(api_ready,))
        api_thread.daemon = True
        api_thread.start()
        
        # Esperar API estar pronta
        print("⌛ Aguardando API inicializar...")
        api_ready.wait(timeout=10)  # Timeout de 10 segundos
        if not api_ready.is_set():
            raise Exception("Timeout ao iniciar API")
        print("✓ Servidor API iniciado na porta 8000")
        
        # Comentado temporariamente para testes
        # # 3. Criar instâncias após banco e API estarem prontos
        # image_capture = ImageCapture(
        #     production_lines=PRODUCTION_LINES,
        #     interval=CAPTURE_INTERVAL
        # )
        # face_processor = FaceProcessor(db_handler)
        
        # # 4. Salvar globalmente
        set_db_handler(db_handler)
        # set_image_capture(image_capture)
        # set_face_processor(face_processor)
        
        # # 5. Iniciar captura
        # print("▶ Iniciando captura de imagens...")
        # image_capture.set_db_handler(db_handler)
        # image_capture.start_capture()
        # print(f"✓ Captura iniciada com {len(image_capture.cameras)} câmeras")
        
        # # 6. Inicializar processador de faces por último
        # processor_thread = Thread(target=face_processor.start_processing)
        # processor_thread.daemon = True
        # processor_thread.start()
        # print("✓ Processador de faces iniciado")
        
        # Loop principal
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹ Encerrando aplicação...")
    except Exception as e:
        print(f"\n✗ Erro na execução principal: {str(e)}")
    finally:
        # if 'face_processor' in locals():
        #     face_processor.stop_processing()
        # if 'image_capture' in locals():
        #     image_capture.stop_capture()
        pass

if __name__ == "__main__":
    main() 