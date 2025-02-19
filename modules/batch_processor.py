from queue import Queue
from threading import Thread, Event
import logging
import os
from datetime import datetime
import time
from config import BASE_IMAGE_DIR

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self, face_processor):
        self.face_processor = face_processor
        self.batch_queues = {}  # Uma fila por linha de produção
        self.processing_threads = {}
        self.stop_event = Event()

    def start(self, production_lines):
        """Inicia threads de processamento para cada linha"""
        for line_id in production_lines:
            self.batch_queues[line_id] = Queue()
            thread = Thread(
                target=self._process_line_batches,
                args=(line_id,),
                name=f"processor_{line_id}"
            )
            thread.daemon = True
            thread.start()
            self.processing_threads[line_id] = thread
            logger.info(f"Iniciado processador para {line_id}")

    def _process_line_batches(self, line_id):
        """Thread de processamento para uma linha específica"""
        while not self.stop_event.is_set():
            try:
                pending_batches = self.face_processor.db_handler.get_pending_batches(line_id)
                if not pending_batches:
                    time.sleep(1)
                    continue

                for batch in pending_batches:
                    batch_folder = batch['batch_path']
                    if not os.path.exists(batch_folder):
                        self.face_processor.db_handler.update_batch_status(
                            batch_folder, 'error', 'Pasta não encontrada'
                        )
                        continue

                    image_count = len([f for f in os.listdir(batch_folder) 
                                     if f.endswith(('.jpg', '.jpeg', '.png'))])
                    if image_count < 3:  # Configurável
                        logger.warning(f"Lote {batch_folder} tem poucas imagens: {image_count}")

                    try:
                        self.face_processor.db_handler.update_batch_status(
                            batch_folder, 'processing'
                        )
                        
                        # Processar lote
                        start_time = time.time()
                        self.face_processor.process_batch(batch_folder, line_id)
                        processing_time = time.time() - start_time
                        logger.info(f"Tempo de processamento do lote: {processing_time:.2f}s")
                        
                        # Marcar como completo
                        self.face_processor.db_handler.update_batch_status(
                            batch_folder, 'completed'
                        )
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Erro processando lote {batch_folder}: {error_msg}")
                        self.face_processor.db_handler.update_batch_status(
                            batch_folder, 'error', error_msg
                        )

            except Exception as e:
                logger.error(f"Erro processando lote da {line_id}: {str(e)}")

    def add_batch(self, line_id, batch_folder):
        """Adiciona um lote para processamento"""
        if line_id in self.batch_queues:
            self.batch_queues[line_id].put(batch_folder)
            logger.info(f"Lote adicionado para {line_id}: {batch_folder}")
        else:
            logger.error(f"Linha de produção não encontrada: {line_id}")

    def stop(self):
        """Para todos os processadores"""
        self.stop_event.set()
        for line_id, queue in self.batch_queues.items():
            queue.join()  # Espera processamento dos lotes restantes
        for thread in self.processing_threads.values():
            thread.join() 