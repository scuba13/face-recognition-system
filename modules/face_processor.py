import face_recognition
import os
import logging
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from datetime import datetime
import time
from config import FACE_RECOGNITION_TOLERANCE, PRODUCTION_LINES

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
                # Buscar lotes pendentes de todas as linhas configuradas
                for line_id in PRODUCTION_LINES.keys():
                    pending_batches = self.db_handler.get_pending_batches(line_id)
                    
                    # Logar apenas se encontrar lotes para processar
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
        batch_path = batch['batch_path']  # Extrair path do documento
        
        if not os.path.exists(batch_path):
            raise ValueError(f"Pasta do lote não encontrada: {batch_path}")
        
        # Extrair line_id do batch_path
        line_id = batch_path.split('/')[1]  # captured_images/linha_1/...
        
        try:
            # Atualizar status para 'processing'
            self.db_handler.update_batch_status(batch_path, 'processing')
            
            # Processar imagens
            total_images = 0
            total_faces_detected = 0
            total_faces_unknown = 0
            detections = {}  # { employee_id: { 'name': name, 'count': 0, 'confidence_sum': 0 } }
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
                    total_faces_detected += len(face_locations)
                    
                    if face_locations:
                        # Processar cada face encontrada
                        face_encodings = face_recognition.face_encodings(image, face_locations)
                        
                        for face_encoding in face_encodings:
                            # Buscar match direto no banco
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
            
            # Extrair timestamp do batch_path
            timestamp_str = batch_path.split('/')[-1]  # formato: YYYYMMDD_HHMM
            capture_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M")

            # Preparar dados do lote na ordem correta
            batch_data = {
                'line_id': line_id,
                'batch_path': batch_path,
                'timestamp': datetime.now(),
                'capture_datetime': capture_datetime,
                'processed_at': datetime.now(),
                'processor_id': os.getenv('PROCESSOR_ID'),
                'total_images': total_images,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'total_faces_detected': total_faces_detected,
                'total_faces_recognized': sum(d['count'] for d in detections.values()),
                'total_faces_unknown': total_faces_unknown,
                'unique_people_recognized': len([d for d in detections.values() if d['count'] > 0]),
                'unique_people_unknown': total_faces_unknown,
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
            
            # Registrar no banco
            self.db_handler.register_batch_detection(batch_data)
            
            # Marcar como completo
            self.db_handler.update_batch_status(batch_path, 'completed')
            
            # Log do resumo
            logger.info(f"Resumo do lote {batch_path}:")
            logger.info(f"- Total de imagens: {batch_data['total_images']}")
            logger.info(f"- Faces detectadas: {batch_data['total_faces_detected']}")
            logger.info(f"- Faces reconhecidas: {batch_data['total_faces_recognized']}")
            logger.info(f"- Faces não reconhecidas: {batch_data['total_faces_unknown']}")
            logger.info(f"- Pessoas únicas reconhecidas: {batch_data['unique_people_recognized']}")
            logger.info(f"- Pessoas únicas não reconhecidas: {batch_data['unique_people_unknown']}")
            
        except Exception as e:
            logger.error(f"Erro ao processar lote {batch_path}: {str(e)}")
            self.db_handler.update_batch_status(
                batch_path, 
                'error',
                error_message=str(e)
            )
            raise

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

    def _compare_face(self, face_encoding):
        """Compara uma face com todos os encodings conhecidos em chunks"""
        chunk_size = 100
        total_chunks = self.db_handler.count_total_encodings() // chunk_size + 1
        
        for chunk in range(total_chunks):
            # Carregar chunk atual
            encodings, names, ids = self.db_handler.get_encodings_chunk(
                skip=chunk * chunk_size,
                limit=chunk_size
            )
            
            if not encodings:
                continue
                
            # Comparar com faces do chunk atual
            matches = face_recognition.compare_faces(
                encodings,
                face_encoding,
                tolerance=self.tolerance
            )
            
            if True in matches:
                match_index = matches.index(True)
                return {
                    'name': names[match_index],
                    'employee_id': ids[match_index],
                    'confidence': 1 - face_recognition.face_distance([encodings[match_index]], face_encoding)[0]
                }
                
        return None 