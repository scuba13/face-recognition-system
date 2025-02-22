import face_recognition
import os
import logging
import numpy as np
from datetime import datetime
import time
from threading import Thread
from linha.config.settings import FACE_RECOGNITION_TOLERANCE, PRODUCTION_LINES, ENABLE_PREPROCESSING
from linha.db.models import BatchDetection  # Importar o modelo
import shutil  # Adicionar import
import cv2  # Adicionar import para cv2
from concurrent.futures import ThreadPoolExecutor
import gc  # Para garbage collection
from linha.utils.image_preprocessing import ImagePreprocessor

logger = logging.getLogger(__name__)

class FaceProcessor:
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self.running = True
        self.tolerance = FACE_RECOGNITION_TOLERANCE
        self.max_workers = 4  # Número de threads para processamento paralelo

    def start_processing(self):
        """Inicia o processamento de lotes"""
        logger.info("Iniciando processamento de lotes")
        
        while self.running:
            try:
                for line_id in PRODUCTION_LINES.keys():
                    pending_batches = self.db_handler.get_pending_batches(line_id)
                    
                    if pending_batches:
                        logger.info(f"Processando {len(pending_batches)} lotes da {line_id}")
                        for batch in pending_batches:
                            self.process_batch(batch)
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Erro no loop de processamento: {str(e)}")
                time.sleep(5)

    def process_image(self, image_path):
        """Processa uma única imagem"""
        try:
            # Carregar imagem
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            # Redimensionar se necessário
            height, width = image.shape[:2]
            max_dimension = 800
            if height > max_dimension or width > max_dimension:
                scale = max_dimension / max(height, width)
                image = cv2.resize(image, (0, 0), fx=scale, fy=scale)
            
            # Aplicar pré-processamento se habilitado
            if ENABLE_PREPROCESSING:
                image = ImagePreprocessor.enhance_image(image)
            
            # Converter para RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detectar e processar faces
            face_locations = face_recognition.face_locations(image, model="hog")
            
            if not face_locations:
                return None
                
            face_encodings = face_recognition.face_encodings(
                image, 
                face_locations,
                num_jitters=1
            )
            
            results = []
            for face_encoding in face_encodings:
                match = self.db_handler.find_matching_face(
                    face_encoding, 
                    tolerance=self.tolerance
                )
                if match:
                    results.append(match)
            
            # Liberar memória
            del image
            gc.collect()
            
            return results
            
        except Exception as e:
            logger.error(f"Erro ao processar imagem {image_path}: {str(e)}")
            return None

    def process_batch(self, batch):
        """Processa um lote de imagens em paralelo"""
        batch_path = batch['batch_path']
        line_id = batch_path.split('captured_images/')[1].split('/')[0]
        
        try:
            total_images = 0
            total_faces_detected = 0
            total_faces_unknown = 0
            detections = {}
            start_time = datetime.now()
            
            image_files = [f for f in os.listdir(batch_path) 
                          if f.endswith(('.jpg', '.jpeg', '.png'))]
            
            # Processar imagens em paralelo
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for image_file in image_files:
                    image_path = os.path.join(batch_path, image_file)
                    futures.append(executor.submit(self.process_image, image_path))
                
                total_images = len(image_files)
                
                # Coletar resultados
                for future in futures:
                    results = future.result()
                    if results:
                        for result in results:
                            total_faces_detected += 1
                            if result:
                                employee_id = result['employee_id']
                                name = result['name']
                                
                                if employee_id not in detections:
                                    detections[employee_id] = {
                                        'name': name,
                                        'count': 0,
                                        'confidence_sum': 0
                                    }
                                
                                detections[employee_id]['count'] += 1
                                detections[employee_id]['confidence_sum'] += result['confidence']
                            else:
                                total_faces_unknown += 1
            
            # Criar BatchDetection e registrar
            timestamp_str = batch_path.split('/')[-1]
            capture_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M")
            
            batch_detection = BatchDetection(
                line_id=line_id,
                batch_path=batch_path,
                timestamp=datetime.now(),
                capture_datetime=capture_datetime,
                processed_at=datetime.now(),
                processor_id=batch['processor_id'],
                total_images=total_images,
                processing_time=(datetime.now() - start_time).total_seconds(),
                total_faces_detected=total_faces_detected,
                total_faces_recognized=sum(d['count'] for d in detections.values()),
                total_faces_unknown=total_faces_unknown,
                unique_people_recognized=len([d for d in detections.values() if d['count'] > 0]),
                unique_people_unknown=total_faces_unknown,
                preprocessing_enabled=ENABLE_PREPROCESSING,
                detections=[
                    {
                        'employee_id': emp_id,
                        'name': data['name'],
                        'detection_count': data['count'],
                        'average_confidence': data['confidence_sum'] / data['count']
                    }
                    for emp_id, data in detections.items()
                ]
            )
            
            # Registrar e limpar
            self.db_handler.register_batch_detection(batch_detection)
            self.db_handler.update_batch_status(batch_path, 'completed')
            
            # Log do resumo
            logger.info(f"Resumo do lote {batch_path}:")
            logger.info(f"- Total de imagens: {total_images}")
            logger.info(f"- Faces detectadas: {total_faces_detected}")
            logger.info(f"- Faces reconhecidas: {batch_detection.total_faces_recognized}")
            
            # Limpar arquivos e memória
            try:
                shutil.rmtree(batch_path)
                logger.info(f"✨ Lote removido: {batch_path}")
            except Exception as e:
                logger.warning(f"Não foi possível remover o lote {batch_path}: {str(e)}")
            
            gc.collect()  # Forçar garbage collection
            
        except Exception as e:
            logger.error(f"Erro ao processar lote {batch_path}: {str(e)}")
            self.db_handler.update_batch_status(batch_path, 'error', str(e))

    def stop_processing(self):
        """Para o processamento"""
        self.running = False 