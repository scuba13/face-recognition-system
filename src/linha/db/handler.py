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
                'capture_type': batch_detection.capture_type,
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
            
            # Pipeline de agregação para otimizar a consulta
            pipeline = [
                # Filtrar por data
                {
                    '$match': {
                        'timestamp': {'$gte': cutoff}
                    }
                },
                
                # Projetar campos necessários e criar campos de hora e minuto
                {
                    '$project': {
                        'line_id': 1,
                        'timestamp': 1,
                        'hour': {
                            '$dateToString': {
                                'format': '%Y-%m-%d %H:00',
                                'date': '$timestamp'
                            }
                        },
                        'minute': {
                            '$dateToString': {
                                'format': '%Y-%m-%d %H:%M',
                                'date': '$timestamp'
                            }
                        },
                        'detections': {
                            '$map': {
                                'input': '$detections',
                                'as': 'detection',
                                'in': {
                                    'name': '$$detection.name',
                                    'confidence': {'$ifNull': ['$$detection.confidence', 0]},
                                    'employee_id': '$$detection.employee_id'
                                }
                            }
                        }
                    }
                },
                
                # Ordenar por timestamp decrescente
                {
                    '$sort': {
                        'timestamp': -1
                    }
                }
            ]
            
            # Executar pipeline
            detections = list(self.detections.aggregate(pipeline))
            logger.info(f"Encontradas {len(detections)} detecções")
            
            # Garantir que todos os campos existam e formatar datas
            formatted_detections = []
            for det in detections:
                try:
                    formatted_det = {
                        'line_id': det.get('line_id', 'unknown'),
                        'timestamp': det['timestamp'].isoformat() if det.get('timestamp') else None,
                        'hour': det.get('hour'),
                        'minute': det.get('minute'),
                        'detections': det.get('detections', [])
                    }
                    formatted_detections.append(formatted_det)
                except Exception as e:
                    logger.error(f"Erro ao formatar detecção: {str(e)}")
                    continue
            
            return formatted_detections
            
        except Exception as e:
            logger.error(f"Erro ao buscar detecções: {str(e)}", exc_info=True)
            return {'error': str(e)}

    @backoff.on_exception(backoff.expo, PyMongoError, max_tries=3)
    def register_batch_detections(self, detections):
        """Registra múltiplas detecções em batch"""
        try:
            if detections:
                self.detections.insert_many(detections, ordered=False)
                logger.info(f"Registradas {len(detections)} detecções em batch")
        except Exception as e:
            logger.error(f"Erro ao registrar detecções em batch: {str(e)}") 

    def get_processor_statistics(self, hours=24):
        """Retorna estatísticas de processamento das últimas X horas"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            # Pipeline para métricas gerais
            pipeline = [
                {
                    '$match': {
                        'processed_at': {'$gte': cutoff, '$lte': datetime.now()}
                    }
                },
                {
                    '$unwind': '$detections'
                },
                {
                    '$group': {
                        '_id': None,
                        'total_batches': {'$sum': 1},
                        'total_time': {'$sum': '$processing_time'},
                        'total_faces_detected': {'$sum': '$total_faces_detected'},
                        'total_faces_recognized': {'$sum': '$total_faces_recognized'},
                        'total_faces_unknown': {'$sum': '$total_faces_unknown'},
                        'total_confidence': {'$sum': '$detections.average_confidence'},
                        'count_detections': {'$sum': 1},
                        'total_images': {'$sum': '$total_images'}
                    }
                }
            ]
            
            # Pipeline para horas
            hourly_pipeline = [
                {
                    '$match': {
                        'processed_at': {'$gte': cutoff, '$lte': datetime.now()}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            '$dateToString': {
                                'format': '%Y-%m-%d %H:00',
                                'date': '$processed_at'
                            }
                        },
                        'total_batches': {'$sum': 1},
                        'total_faces': {'$sum': '$total_faces_detected'}
                    }
                },
                {'$sort': {'_id': 1}}
            ]
            
            # Executar pipelines
            result = list(self.detections.aggregate(pipeline))
            hourly_stats = list(self.detections.aggregate(hourly_pipeline))
            
            # Buscar contagens de lotes
            batch_counts = {
                'pending': self.batch_control.count_documents({
                    'status': 'pending',
                    'created_at': {'$gte': cutoff, '$lte': datetime.now()}
                }),
                'processing': self.batch_control.count_documents({
                    'status': 'processing',
                    'created_at': {'$gte': cutoff, '$lte': datetime.now()}
                }),
                'completed': self.batch_control.count_documents({
                    'status': 'completed',
                    'processed_at': {'$gte': cutoff, '$lte': datetime.now()}
                }),
                'error': self.batch_control.count_documents({
                    'status': 'error',
                    'processed_at': {'$gte': cutoff, '$lte': datetime.now()}
                })
            }
            
            # Formatar resposta
            if result:
                metrics = result[0]
                stats = {
                    'avg_processing_time': metrics['total_time'] / metrics['total_batches'] if metrics['total_batches'] > 0 else 0,
                    'avg_images_per_batch': metrics['total_images'] / metrics['total_batches'] if metrics['total_batches'] > 0 else 0,
                    'total_faces_detected': metrics['total_faces_detected'],
                    'total_faces_recognized': metrics['total_faces_recognized'],
                    'total_faces_unknown': metrics['total_faces_unknown'],
                    'avg_distance': metrics['total_confidence'] / metrics['count_detections'] if metrics['count_detections'] > 0 else 0,
                    'pending_batches': batch_counts['pending'],
                    'processing_batches': batch_counts['processing'],
                    'completed_batches': batch_counts['completed'],
                    'error_batches': batch_counts['error'],
                    'hourly_stats': [
                        {
                            'datetime': stat['_id'],
                            'total_batches': stat['total_batches'],
                            'total_faces': stat['total_faces']
                        }
                        for stat in hourly_stats
                    ]
                }
            else:
                stats = {
                    'avg_processing_time': 0,
                    'avg_images_per_batch': 0,
                    'total_faces_detected': 0,
                    'total_faces_recognized': 0,
                    'total_faces_unknown': 0,
                    'avg_distance': 0,
                    'pending_batches': batch_counts['pending'],
                    'processing_batches': batch_counts['processing'],
                    'completed_batches': batch_counts['completed'],
                    'error_batches': batch_counts['error'],
                    'hourly_stats': []
                }
                
            return stats
            
        except Exception as e:
            print(f"ERRO ao calcular estatísticas: {str(e)}")
            return {'error': str(e)} 

    # Verificar estrutura dos dados
    def check_detection_structure(self):
        sample = list(self.detections.find().limit(1))
        if sample:
            print("\nExemplo de detecção:")
            print(f"Detections: {sample[0].get('detections', [])}")
            print("\nEstrutura de uma detecção:")
            print(f"Keys: {list(sample[0].keys())}")
            if 'detections' in sample[0]:
                print(f"Detections: {sample[0]['detections']}") 