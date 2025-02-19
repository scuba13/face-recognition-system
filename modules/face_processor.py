import face_recognition
import os
import logging
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from datetime import datetime
import shutil
from config import FACE_RECOGNITION_TOLERANCE, MAX_PROCESSING_WORKERS, FACE_DETECTION_MODEL, MIN_IMAGES_PER_BATCH
from modules.circuit_breaker import CircuitBreaker
from modules.backup_handler import BackupHandler
from modules.image_validator import ImageValidator
import time

logger = logging.getLogger(__name__)

class FaceProcessor:
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.tolerance = FACE_RECOGNITION_TOLERANCE
        self.backup_handler = BackupHandler()
        self.image_validator = ImageValidator()
        self._load_known_faces()

    def _load_known_faces(self):
        """Carrega as faces conhecidas do banco de dados"""
        logger.info("Carregando encodings do banco de dados...")
        self.known_face_encodings, self.known_face_names, self.known_face_ids = self.db_handler.get_all_encodings()
        logger.info(f"Carregados {len(self.known_face_names)} encodings")

    @CircuitBreaker(failure_threshold=5, reset_timeout=60)
    def process_batch(self, batch_folder, production_line):
        """Processa um lote de imagens e gera um único registro"""
        # Contadores para métricas
        metrics = {
            'total_frames': 0,
            'faces_detected': 0,
            'faces_recognized': 0,
            'processing_time': 0
        }

        start_time = time.time()
        try:
            # Usar ThreadPoolExecutor para processar imagens em paralelo
            with ThreadPoolExecutor(max_workers=MAX_PROCESSING_WORKERS) as executor:
                image_files = [
                    f for f in os.listdir(batch_folder) 
                    if f.endswith(('.jpg', '.jpeg', '.png'))
                ]
                
                if len(image_files) < MIN_IMAGES_PER_BATCH:
                    raise ValueError(f"Lote com poucas imagens: {len(image_files)}")

                futures = []
                for img in image_files:
                    img_path = os.path.join(batch_folder, img)
                    # Validar imagem antes de processar
                    is_valid, message = self.image_validator.validate_image(img_path)
                    if is_valid:
                        futures.append(
                            executor.submit(self._process_single_image, img_path)
                        )
                    else:
                        logger.warning(f"Imagem inválida {img_path}: {message}")

                results = [f.result() for f in futures]

            # Agregar resultados
            detections_count = {}
            total_images = len(image_files)
            
            # Preparar dados para registro
            detections = []
            for emp_id, data in detections_count.items():
                avg_confidence = data['confidence_sum'] / data['count']
                detections.append({
                    'employee_id': emp_id,
                    'name': data['name'],
                    'confidence': avg_confidence,
                    'detection_count': data['count']
                })

            # Registrar lote
            batch_data = {
                'timestamp': datetime.now(),
                'production_line': production_line,
                'detections': detections,
                'total_images': total_images,
                'batch_folder': batch_folder
            }
            
            self.db_handler.register_batch_detection(batch_data)
            
            logger.info(f"Lote processado: {len(detections)} funcionários detectados em {total_images} imagens")
            
            # Limpar pasta após processamento
            if os.getenv('DELETE_AFTER_PROCESS', 'True').lower() == 'true':
                shutil.rmtree(batch_folder)
                logger.info(f"Pasta removida: {batch_folder}")
            
        except Exception as e:
            logger.error(f"Erro processando lote {batch_folder}: {str(e)}")
            self.backup_handler.backup_failed_batch(batch_folder, str(e))
            raise

    def process_image(self, image_path, production_line):
        """Processa uma única imagem"""
        try:
            # Carregar imagem
            image = face_recognition.load_image_file(image_path)
            
            # Encontrar faces na imagem
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)

            for face_encoding in face_encodings:
                # Calcular distância com todas as faces conhecidas
                face_distances = face_recognition.face_distance(
                    self.known_face_encodings,
                    face_encoding
                )
                
                # Encontrar a menor distância
                best_match_index = np.argmin(face_distances)
                min_distance = face_distances[best_match_index]

                if min_distance <= self.tolerance:
                    name = self.known_face_names[best_match_index]
                    confidence = (1 - min_distance) * 100
                    
                    # Registrar no banco de dados
                    self.db_handler.register_detection({
                        'employee_id': name,
                        'timestamp': os.path.getmtime(image_path),
                        'production_line': production_line,
                        'image_path': image_path,
                        'confidence': confidence
                    })
                    
                    logger.info(f"Funcionário {name} detectado na linha {production_line} (confiança: {confidence:.2f}%)")
                else:
                    logger.warning(f"Face detectada mas não reconhecida (distância: {min_distance:.2f})")

        except Exception as e:
            logger.error(f"Erro ao processar imagem {image_path}: {str(e)}") 

    def register_new_employee(self, image_path, name, employee_id):
        """
        Registra um novo funcionário no banco de dados
        """
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            encodings = face_recognition.face_encodings(image, face_locations)

            if len(encodings) > 0:
                # Converter o numpy array para lista para armazenar no MongoDB
                encoding_list = encodings[0].tolist()
                
                employee_data = {
                    'employee_id': employee_id,
                    'name': name,
                    'face_encoding': encoding_list,
                    'created_at': datetime.now()
                }
                
                self.db_handler.store_employee_encoding(employee_data)
                logger.info(f"Funcionário {name} registrado com sucesso")
                
                # Atualizar listas locais
                self.known_face_encodings.append(encodings[0])
                self.known_face_names.append(name)
                
                return True
            else:
                logger.error(f"Nenhuma face encontrada na imagem: {image_path}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao registrar funcionário: {str(e)}")
            return False 