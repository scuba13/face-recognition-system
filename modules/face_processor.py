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
        self.running = True
        self.tolerance = FACE_RECOGNITION_TOLERANCE
        self.backup_handler = BackupHandler()
        self.image_validator = ImageValidator()
        self._load_known_faces()

    def _load_known_faces(self):
        """Carrega encodings conhecidos do banco de dados"""
        logger.info("Carregando encodings do banco de dados...")
        try:
            encodings, names, ids = self.db_handler.get_all_encodings()
            self.known_face_encodings = encodings
            self.known_face_names = names
            self.known_face_ids = ids
            logger.info(f"Carregados {len(encodings)} encodings")
        except Exception as e:
            logger.error(f"Erro ao carregar encodings: {str(e)}")
            # Inicializar com listas vazias em caso de erro
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_face_ids = []

    def start_processing(self):
        """Inicia o processamento de lotes"""
        logger.info("Iniciando processamento de lotes")
        
        while self.running:
            try:
                # Buscar lotes pendentes
                logger.info("Buscando lotes pendentes...")
                pending_batches = self.db_handler.get_pending_batches("linha_1")
                logger.info(f"Encontrados {len(pending_batches)} lotes pendentes")
                
                if pending_batches:
                    for batch in pending_batches:
                        batch_path = batch['batch_path']
                        logger.info(f"Iniciando processamento do lote: {batch_path}")
                        
                        try:
                            # Verificar se pasta existe
                            if not os.path.exists(batch_path):
                                logger.error(f"Pasta do lote não encontrada: {batch_path}")
                                continue
                                
                            # Listar imagens no lote
                            images = [f for f in os.listdir(batch_path) 
                                    if f.endswith(('.jpg', '.jpeg', '.png'))]
                            logger.info(f"Encontradas {len(images)} imagens para processar")
                            
                            # Atualizar status para 'processing'
                            self.db_handler.update_batch_status(batch_path, 'processing')
                            
                            # Processar imagens do lote
                            self.process_batch(batch_path)
                            
                            # Marcar como completo
                            self.db_handler.update_batch_status(batch_path, 'completed')
                            logger.info(f"Lote processado com sucesso: {batch_path}")
                            
                        except Exception as e:
                            logger.error(f"Erro ao processar lote {batch_path}: {str(e)}")
                            self.db_handler.update_batch_status(
                                batch_path, 
                                'error',
                                error_message=str(e)
                            )
                
                # Aguardar antes de verificar novamente
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Erro no loop de processamento: {str(e)}")
                time.sleep(5)

    def process_batch(self, batch_path):
        """Processa um lote de imagens"""
        if not os.path.exists(batch_path):
            raise ValueError(f"Pasta do lote não encontrada: {batch_path}")
        
        # Dicionário para acumular detecções por pessoa
        detections = {}  # { employee_id: { 'name': name, 'count': 0, 'confidence_sum': 0 } }
        total_images = 0
        start_time = datetime.now()
        
        # Processar cada imagem do lote
        image_files = [f for f in os.listdir(batch_path) 
                      if f.endswith(('.jpg', '.jpeg', '.png'))]
        
        for image_file in image_files:
            image_path = os.path.join(batch_path, image_file)
            total_images += 1
            
            try:
                # Carregar e processar imagem
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                
                if face_locations:
                    # Processar cada face encontrada
                    face_encodings = face_recognition.face_encodings(image, face_locations)
                    
                    for face_encoding in face_encodings:
                        # Comparar com faces conhecidas
                        matches = face_recognition.compare_faces(
                            self.known_face_encodings, 
                            face_encoding,
                            tolerance=self.tolerance
                        )
                        
                        if True in matches:
                            # Encontrou match
                            match_index = matches.index(True)
                            name = self.known_face_names[match_index]
                            employee_id = self.known_face_ids[match_index]
                            
                            # Calcular confiança
                            face_distances = face_recognition.face_distance([self.known_face_encodings[match_index]], face_encoding)
                            confidence = 1 - face_distances[0]
                            
                            # Acumular detecção
                            if employee_id not in detections:
                                detections[employee_id] = {
                                    'name': name,
                                    'count': 0,
                                    'confidence_sum': 0
                                }
                            
                            detections[employee_id]['count'] += 1
                            detections[employee_id]['confidence_sum'] += confidence
            
            except Exception as e:
                logger.error(f"Erro ao processar imagem {image_path}: {str(e)}")
                continue
        
        # Preparar resumo do lote
        batch_summary = {
            'timestamp': start_time,
            'batch_path': batch_path,
            'total_images': total_images,
            'processing_time': (datetime.now() - start_time).total_seconds(),
            'detections': [
                {
                    'employee_id': emp_id,
                    'name': data['name'],
                    'detection_count': data['count'],
                    'average_confidence': data['confidence_sum'] / data['count']
                }
                for emp_id, data in detections.items()
            ]
        }
        
        # Registrar resumo do lote
        logger.info(f"Resumo do lote {batch_path}:")
        logger.info(f"Total de imagens: {total_images}")
        logger.info(f"Pessoas detectadas: {len(detections)}")
        for det in batch_summary['detections']:
            logger.info(f"- {det['name']}: {det['detection_count']} detecções (confiança média: {det['average_confidence']:.2f})")
        
        # Registrar no banco
        self.db_handler.register_batch_detection(batch_summary)

    def stop_processing(self):
        """Para o processamento"""
        self.running = False

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