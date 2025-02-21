import face_recognition
import os
import logging
import numpy as np
from datetime import datetime
import time
from threading import Thread
from linha.config.settings import FACE_RECOGNITION_TOLERANCE, PRODUCTION_LINES
from linha.db.models import BatchDetection  # Importar o modelo

logger = logging.getLogger(__name__)

class FaceProcessor:
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self.running = True
        self.tolerance = FACE_RECOGNITION_TOLERANCE

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

    def process_batch(self, batch):
        """Processa um lote de imagens"""
        batch_path = batch['batch_path']
        line_id = batch_path.split('/')[1]
        
        try:
            self.db_handler.update_batch_status(batch_path, 'processing')
            
            total_images = 0
            total_faces_detected = 0
            total_faces_unknown = 0
            detections = {}
            start_time = datetime.now()
            
            image_files = [f for f in os.listdir(batch_path) 
                          if f.endswith(('.jpg', '.jpeg', '.png'))]
            
            for image_file in image_files:
                image_path = os.path.join(batch_path, image_file)
                total_images += 1
                
                try:
                    image = face_recognition.load_image_file(image_path)
                    face_locations = face_recognition.face_locations(image)
                    total_faces_detected += len(face_locations)
                    
                    if face_locations:
                        face_encodings = face_recognition.face_encodings(image, face_locations)
                        
                        for face_encoding in face_encodings:
                            result = self.db_handler.find_matching_face(
                                face_encoding, 
                                tolerance=self.tolerance
                            )
                            
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
                
                except Exception as e:
                    logger.error(f"Erro ao processar imagem {image_path}: {str(e)}")
                    continue
            
            timestamp_str = batch_path.split('/')[-1]
            capture_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M")

            # Criar objeto BatchDetection ao invés de dict
            batch_detection = BatchDetection(
                line_id=line_id,
                batch_path=batch_path,
                timestamp=datetime.now(),
                capture_datetime=capture_datetime,
                processed_at=datetime.now(),
                processor_id=os.getenv('PROCESSOR_ID'),
                total_images=total_images,
                processing_time=(datetime.now() - start_time).total_seconds(),
                total_faces_detected=total_faces_detected,
                total_faces_recognized=sum(d['count'] for d in detections.values()),
                total_faces_unknown=total_faces_unknown,
                unique_people_recognized=len([d for d in detections.values() if d['count'] > 0]),
                unique_people_unknown=total_faces_unknown,
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
            
            self.db_handler.register_batch_detection(batch_detection)
            self.db_handler.update_batch_status(batch_path, 'completed')
            
            logger.info(f"Resumo do lote {batch_path}:")
            logger.info(f"- Total de imagens: {total_images}")
            logger.info(f"- Faces detectadas: {total_faces_detected}")
            logger.info(f"- Faces reconhecidas: {batch_detection.total_faces_recognized}")
            
        except Exception as e:
            logger.error(f"Erro ao processar lote {batch_path}: {str(e)}")
            self.db_handler.update_batch_status(batch_path, 'error', str(e))

    def stop_processing(self):
        """Para o processamento"""
        self.running = False 