from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError
import backoff
import logging
import numpy as np
from datetime import datetime, timedelta
import os
from config import (
    MONGODB_URI, BATCH_LOCK_TIMEOUT, MONGODB_TIMEOUT_MS,
    MONGODB_MAX_POOL_SIZE, MONGODB_RETRY_WRITES
)

logger = logging.getLogger(__name__)

class MongoDBHandler:
    def __init__(self, connection_string=MONGODB_URI):
        self.client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=MONGODB_TIMEOUT_MS,
            maxPoolSize=MONGODB_MAX_POOL_SIZE,
            retryWrites=MONGODB_RETRY_WRITES
        )
        self.db = self.client.face_recognition_db
        self._setup_collections()

    def _setup_collections(self):
        """Configura coleções e índices"""
        # Configurar coleções
        self.detections = self.db.detections
        self.employees = self.db.employees
        self.batch_control = self.db.batch_control
        self.metrics = self.db.metrics

        # Criar índices
        self._create_indexes()

    def _create_indexes(self):
        """Cria índices necessários"""
        # Índices para detections
        self.detections.create_index([("timestamp", 1)])
        self.detections.create_index([("production_line", 1), ("timestamp", 1)])
        self.detections.create_index([("employee_id", 1)])

        # Índices para employees
        self.employees.create_index([("employee_id", 1)], unique=True)
        self.employees.create_index([("name", 1)])

        # Índices para batch_control
        self.batch_control.create_index([("line_id", 1), ("status", 1)])
        self.batch_control.create_index([("batch_path", 1)], unique=True)
        self.batch_control.create_index([("created_at", 1)])
        self.batch_control.create_index([("processor_id", 1)])

        # Índices para metrics
        self.metrics.create_index([("timestamp", 1)])

    def register_detection(self, detection_data):
        """
        Registra uma detecção no banco de dados
        
        Args:
            detection_data: dicionário com os dados da detecção
                {
                    'employee_id': str,
                    'timestamp': float,
                    'production_line': int,
                    'image_path': str
                }
        """
        try:
            result = self.detections.insert_one(detection_data)
            logger.info(f"Detecção registrada com ID: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Erro ao registrar detecção: {str(e)}")
            raise

    def store_employee_encoding(self, employee_data):
        """
        Armazena o encoding facial de um funcionário
        Args:
            employee_data: {
                'employee_id': str,
                'name': str,
                'face_encoding': list,  # Numpy array convertido para lista
                'created_at': datetime
            }
        """
        try:
            result = self.employees.insert_one(employee_data)
            logger.info(f"Encoding do funcionário armazenado: {employee_data['name']}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Erro ao armazenar encoding: {str(e)}")
            raise

    def get_all_encodings(self):
        """Recupera todos os encodings dos funcionários"""
        try:
            employees = list(self.employees.find())
            encodings = []
            names = []
            for emp in employees:
                encodings.append(np.array(emp['face_encoding']))
                names.append(emp['name'])
            return encodings, names
        except Exception as e:
            logger.error(f"Erro ao recuperar encodings: {str(e)}")
            raise

    def register_batch_detection(self, batch_data):
        """
        Registra detecções em lote (um registro por minuto)
        Args:
            batch_data: {
                'timestamp': datetime,
                'production_line': str,
                'detections': [
                    {
                        'employee_id': str,
                        'name': str,
                        'confidence': float,
                        'detection_count': int
                    }
                ],
                'total_images': int,
                'batch_folder': str
            }
        """
        try:
            batch_data.update({
                'processor_id': os.getenv('PROCESSOR_ID'),
                'processing_metrics': {
                    'total_frames': batch_data['total_images'],
                    'faces_detected': sum(d['detection_count'] for d in batch_data['detections']),
                    'processing_time': datetime.now() - batch_data['timestamp']
                },
                'camera_info': self.cameras[batch_data['camera_id']].get_info()
            })
            result = self.detections.insert_one(batch_data)
            logger.info(f"Lote registrado com ID: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Erro ao registrar lote: {str(e)}")
            raise

    def get_pending_batches(self, line_id):
        """Recupera lotes pendentes para uma linha"""
        try:
            # Usa findAndModify para garantir exclusividade
            batch = self.batch_control.find_one_and_update(
                {
                    'line_id': line_id,
                    'status': 'pending',
                    'lock_timestamp': {'$lt': datetime.now() - timedelta(minutes=BATCH_LOCK_TIMEOUT)}
                },
                {
                    '$set': {
                        'lock_timestamp': datetime.now(),
                        'processor_id': os.getenv('PROCESSOR_ID', 'default')
                    }
                },
                sort=[('created_at', 1)]
            )
            return [batch] if batch else []
        except Exception as e:
            logger.error(f"Erro ao obter lotes pendentes: {str(e)}")
            return []

    def register_new_batch(self, line_id, batch_path):
        """Registra um novo lote para processamento"""
        try:
            self.batch_control.insert_one({
                'line_id': line_id,
                'batch_path': batch_path,
                'created_at': datetime.now(),
                'status': 'pending',
                'processed_at': None,
                'error_message': None,
                'lock_timestamp': None,
                'processor_id': None
            })
            logger.info(f"Novo lote registrado: {batch_path}")
        except Exception as e:
            logger.error(f"Erro ao registrar lote: {str(e)}")

    def update_batch_status(self, batch_path, status, error_message=None):
        """Atualiza o status de um lote"""
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

    @backoff.on_exception(backoff.expo, PyMongoError, max_tries=3)
    def get_processing_stats(self):
        """Obtém estatísticas de processamento"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        stats = {
            'total_batches': self.batch_control.count_documents({}),
            'pending_batches': self.batch_control.count_documents({'status': 'pending'}),
            'processing_batches': self.batch_control.count_documents({'status': 'processing'}),
            'completed_batches': self.batch_control.count_documents({'status': 'completed'}),
            'error_batches': self.batch_control.count_documents({'status': 'error'}),
            'last_hour_detections': self.detections.count_documents({
                'timestamp': {'$gte': hour_ago}
            }),
            'avg_processing_time': self._calculate_avg_processing_time()
        }
        
        return stats

    def _calculate_avg_processing_time(self):
        """Calcula tempo médio de processamento"""
        pipeline = [
            {
                '$match': {
                    'status': 'completed',
                    'processing_time': {'$exists': True}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'avg_time': {'$avg': '$processing_time'}
                }
            }
        ]
        
        result = list(self.batch_control.aggregate(pipeline))
        return result[0]['avg_time'] if result else None

    def save_metrics(self, metrics):
        """Salva métricas de monitoramento"""
        try:
            self.metrics.insert_one(metrics)
        except Exception as e:
            logger.error(f"Erro ao salvar métricas: {str(e)}") 