import logging
import os
import time
import uuid
from threading import Thread, Event
from fastapi import FastAPI
import threading

from linha.core.face_processor import FaceProcessor
from linha.core.capture_factory import CaptureFactory
from linha.db.handler import MongoDBHandler
from linha.config.settings import (
    PRODUCTION_LINES,
    CAPTURE_TYPE,
    ENABLE_CAPTURE,
    ENABLE_PROCESSING
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
        
       
        # 3. Criar instâncias após banco e API estarem prontos
        # Usar a fábrica para criar o tipo apropriado de captura
        print(f"▶ Criando sistema de captura do tipo: {CAPTURE_TYPE}...")
        image_capture = CaptureFactory.create_capture(
            production_lines=PRODUCTION_LINES
        )
        face_processor = FaceProcessor(db_handler)
        
        # 4. Salvar globalmente
        set_db_handler(db_handler)
        set_image_capture(image_capture)
        set_face_processor(face_processor)
        
        # 5. Iniciar captura (apenas se ENABLE_CAPTURE for True)
        if ENABLE_CAPTURE:
            print("▶ Iniciando captura de imagens...")
            image_capture.set_db_handler(db_handler)
            image_capture.start_capture()
            print(f"✓ Captura iniciada com {len(image_capture.cameras)} câmeras")
        else:
            print("ℹ Captura de imagens desabilitada por configuração")
        
        # 6. Inicializar processador de faces (apenas se ENABLE_PROCESSING for True)
        if ENABLE_PROCESSING:
            processor_thread = Thread(target=face_processor.start_processing)
            processor_thread.daemon = True
            processor_thread.start()
            print("✓ Processador de faces iniciado")
        else:
            print("ℹ Processamento de faces desabilitado por configuração")
        
        # Loop principal
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹ Encerrando aplicação...")
    except Exception as e:
        print(f"\n✗ Erro na execução principal: {str(e)}")
    finally:
        if 'face_processor' in locals() and ENABLE_PROCESSING:
            face_processor.stop_processing()
        if 'image_capture' in locals() and ENABLE_CAPTURE:
            image_capture.stop_capture()

if __name__ == "__main__":
    main() 