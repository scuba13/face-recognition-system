from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError
import logging
import numpy as np
from datetime import datetime, timedelta
import backoff
from linha.config.settings import (
    MONGODB_URI,
    MONGODB_DB,
    BATCH_LOCK_TIMEOUT
)
from linha.db.crud.employee import EmployeeCRUD
import os
import uuid

logger = logging.getLogger(__name__)

class MongoDBHandler:
    def __init__(self, connection_string=MONGODB_URI):
        self.client = MongoClient(connection_string)
        self.db = self.client[MONGODB_DB]
        self._setup_collections()
        
        # Criar instância do CRUD de funcionários
        self.employee_crud = EmployeeCRUD(self)
        
        logger.info("Conexão com MongoDB estabelecida")
        
    def _setup_collections(self):
        """Configura coleções e índices"""
        # Collections
        self.batch_control = self.db.batch_control
        self.detections = self.db.detections
        self.employees = self.db.employees
        
        # Índices otimizados
        self.batch_control.create_index([
            ("line_id", 1),
            ("status", 1),
            ("processor_id", 1)
        ])
        
        self.detections.create_index([
            ("line_id", 1),
            ("timestamp", -1)
        ])
        
        self.detections.create_index([
            ("batch_path", 1)
        ], unique=True)
        
        self.employees.create_index([
            ("employee_id", 1)
        ], unique=True)
        
        # Índice TTL para limpeza automática
        self.batch_control.create_index(
            "processed_at", 
            expireAfterSeconds=30*24*60*60  # 30 dias
        )

    @backoff.on_exception(backoff.expo, PyMongoError, max_tries=3)
    def register_new_batch(self, line_id: str, batch_path: str):
        """Registra novo lote para processamento"""
        try:
            self.batch_control.insert_one({
                'line_id': line_id,
                'batch_path': batch_path,
                'created_at': datetime.now(),
                'status': 'pending',
                'processor_id': None,  # Será definido quando o lote for pego para processamento
                'processed_at': None,
                'error_message': None
            })
            logger.info(f"Novo lote registrado: {batch_path}")
        except Exception as e:
            logger.error(f"Erro ao registrar lote: {str(e)}")

    def get_pending_batches(self, line_id: str = None):
        """Recupera lotes pendentes para processamento"""
        try:
            query = {
                'status': 'pending',
                'processor_id': None  # Apenas lotes não atribuídos
            }
            
            if line_id:
                query['line_id'] = line_id
                
            # Buscar lotes pendentes
            batches = list(self.batch_control.find(query).limit(10))
            
            # Atualizar processor_id dos lotes encontrados
            if batches:
                for batch in batches:
                    # Gerar um novo ID único para cada lote
                    batch_processor_id = str(uuid.uuid4())
                    self.batch_control.update_one(
                        {'_id': batch['_id']},
                        {
                            '$set': {
                                'processor_id': batch_processor_id,
                                'status': 'processing'
                            }
                        }
                    )
                    # Atualizar o ID no objeto batch que será retornado
                    batch['processor_id'] = batch_processor_id
            
            return batches
        except Exception as e:
            logger.error(f"Erro ao buscar lotes pendentes: {str(e)}")
            return []

    def get_processing_batches(self):
        """Retorna lotes em processamento"""
        return list(self.batch_control.find({'status': 'processing'}))

    def get_completed_batches(self, line_id: str = None):
        """Retorna lotes completados"""
        try:
            query = {'status': 'completed'}
            if line_id:
                query['line_id'] = line_id
            return list(self.batch_control.find(query))
        except Exception as e:
            logger.error(f"Erro ao buscar lotes completados: {str(e)}")
            return []

    def update_batch_status(self, batch_path: str, status: str, error_message: str = None):
        """Atualiza status do lote"""
        update = {
            'status': status,
            'processed_at': datetime.now() if status in ['completed', 'error'] else None
        }
        if error_message:
            update['error_message'] = error_message
            
        self.batch_control.update_one(
            {'batch_path': batch_path},
            {'$set': update}
        )

    def register_batch_detection(self, batch_detection):
        """Registra uma detecção de lote no banco"""
        try:
            logger.info("\n=== Registrando detecção de lote ===")
            
            # Converter para dicionário
            detection_data = {
                'line_id': batch_detection.line_id,
                'batch_path': batch_detection.batch_path,
                'timestamp': batch_detection.timestamp,
                'capture_datetime': batch_detection.capture_datetime,
                'processed_at': batch_detection.processed_at,
                'processor_id': batch_detection.processor_id,
                'total_images': batch_detection.total_images,
                'processing_time': batch_detection.processing_time,
                'total_faces_detected': batch_detection.total_faces_detected,
                'total_faces_recognized': batch_detection.total_faces_recognized,
                'total_faces_unknown': batch_detection.total_faces_unknown,
                'preprocessing_enabled': batch_detection.preprocessing_enabled,
                'detections': batch_detection.detections
            }
            
            logger.info(f"Dados para inserção: {detection_data}")
            
            # Inserir no banco
            result = self.detections.insert_one(detection_data)
            logger.info(f"Detecção registrada com ID: {result.inserted_id}")
            
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Erro ao registrar detecção: {str(e)}", exc_info=True)
            raise

    def find_matching_face(self, face_encoding, tolerance=0.6):
        """Busca face mais próxima no banco"""
        try:
            employees = list(self.employees.find())
            if not employees:
                return None
                
            best_match = None
            min_distance = float('inf')
            
            for emp in employees:
                if 'face_encoding' not in emp:
                    continue
                
                stored_encoding = np.array(emp['face_encoding'])
                distance = np.linalg.norm(face_encoding - stored_encoding)
                
                if distance < min_distance and distance <= tolerance:
                    min_distance = distance
                    best_match = {
                        'employee_id': emp['employee_id'],
                        'name': emp['name'],
                        'confidence': 1 - distance
                    }
                    
            return best_match
            
        except Exception as e:
            logger.error(f"Erro ao buscar face: {str(e)}")
            return None 

    def list_employees(self):
        """Lista todos os funcionários cadastrados"""
        try:
            employees = list(self.employees.find())
            logger.info(f"Total de funcionários: {len(employees)}")
            for emp in employees:
                logger.info(f"- {emp.get('name')} (ID: {emp.get('employee_id')})")
            return employees
        except Exception as e:
            logger.error(f"Erro ao listar funcionários: {str(e)}")
            return [] 

    def get_recent_detections(self, days=1):
        """Retorna detecções dos últimos X dias"""
        try:
            logger.info(f"Buscando detecções dos últimos {days} dias")
            cutoff = datetime.now() - timedelta(days=days)
            logger.info(f"Data limite: {cutoff}")
            
            # Construir query
            query = {'timestamp': {'$gte': cutoff}}
            logger.info(f"Query: {query}")
            
            # Executar busca
            detections = list(self.detections.find(
                query,
                sort=[('timestamp', -1)]
            ))
            
            logger.info(f"Detecções encontradas: {len(detections)}")
            for det in detections[:5]:  # Mostrar primeiras 5
                logger.debug(f"Detecção: {det['_id']} - {det['timestamp']}")
            
            return detections
            
        except Exception as e:
            logger.error(f"Erro ao buscar detecções recentes: {str(e)}", exc_info=True)
            return []

    @backoff.on_exception(backoff.expo, PyMongoError, max_tries=3)
    def register_batch_detections(self, detections):
        """Registra múltiplas detecções em batch"""
        try:
            if detections:
                self.detections.insert_many(detections, ordered=False)
                logger.info(f"Registradas {len(detections)} detecções em batch")
        except Exception as e:
            logger.error(f"Erro ao registrar detecções em batch: {str(e)}") 

    def get_processor_statistics(self, days=1):
        """Retorna estatísticas de processamento dos últimos X dias"""
        try:
            print("\n=== Buscando estatísticas de processamento ===")
            
            # Buscar dados dos últimos X dias
            cutoff = datetime.now() - timedelta(days=days)
            pipeline = [
                {'$match': {'timestamp': {'$gte': cutoff}}},
                {'$group': {
                    '_id': None,
                    'total_batches': {'$sum': 1},
                    'total_time': {'$sum': '$processing_time'},
                    'total_faces': {'$sum': '$total_faces_detected'},
                    'recognized_faces': {'$sum': '$total_faces_recognized'},
                    'unknown_faces': {'$sum': '$total_faces_unknown'},
                    'unique_people': {'$addToSet': '$detections.employee_id'},
                    'avg_confidence': {'$avg': {'$arrayElemAt': ['$detections.average_confidence', 0]}}
                }}
            ]
            
            result = list(self.detections.aggregate(pipeline))
            print(f"Resultado agregação: {result}")
            
            # Buscar últimos 50 registros para histórico
            history = list(self.detections.find(
                {},
                {'timestamp': 1, 'processing_time': 1, 'total_faces_detected': 1, 'total_faces_recognized': 1},
                sort=[('timestamp', -1)],
                limit=50
            ))
            
            # Buscar contagens de lotes
            pending = len(self.get_pending_batches())
            processing = len(self.get_processing_batches())
            
            if result:
                metrics = result[0]
                total_batches = metrics['total_batches']
                
                stats = {
                    'running': True,
                    'pending_batches': pending,
                    'processing_batches': processing,
                    'completed_batches': total_batches,
                    'avg_processing_time': metrics['total_time'] / total_batches,
                    'total_faces_detected': metrics['total_faces'],
                    'total_faces_recognized': metrics['recognized_faces'],
                    'total_faces_unknown': metrics['unknown_faces'],
                    'recognition_rate': metrics['recognized_faces'] / metrics['total_faces'] if metrics['total_faces'] > 0 else 0,
                    'unique_people_recognized': len(metrics['unique_people']),
                    'avg_confidence': metrics['avg_confidence'] or 0,
                    'processing_history': [
                        {
                            'timestamp': h['timestamp'].isoformat(),
                            'processing_time': h['processing_time'],
                            'faces_detected': h['total_faces_detected'],
                            'faces_recognized': h['total_faces_recognized']
                        }
                        for h in history
                    ]
                }
            else:
                stats = {
                    'running': True,
                    'pending_batches': pending,
                    'processing_batches': processing,
                    'completed_batches': 0,
                    'avg_processing_time': 0,
                    'total_faces_detected': 0,
                    'total_faces_recognized': 0,
                    'total_faces_unknown': 0,
                    'recognition_rate': 0,
                    'unique_people_recognized': 0,
                    'avg_confidence': 0,
                    'processing_history': []
                }
                
            print(f"Estatísticas calculadas: {stats}")
            return stats
            
        except Exception as e:
            print(f"ERRO ao calcular estatísticas: {str(e)}")
            return {'error': str(e)} 