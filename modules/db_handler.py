from pymongo import MongoClient, ReturnDocument, ASCENDING
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError
import backoff
import logging
import numpy as np
from datetime import datetime, timedelta
import os
from config import (
    MONGODB_URI, BATCH_LOCK_TIMEOUT, MONGODB_TIMEOUT_MS,
    MONGODB_MAX_POOL_SIZE, MONGODB_RETRY_WRITES
)
import time
from typing import Dict
import face_recognition

logger = logging.getLogger(__name__)

class MongoDBHandler:
    def __init__(self, connection_string, max_retries=5, retry_interval=5):
        self.connection_string = connection_string
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.client = None
        self.db = None
        
        # Tentar conectar com retry
        self._connect_with_retry()
        
    def _connect_with_retry(self):
        """Tenta conectar ao MongoDB com retry"""
        for attempt in range(self.max_retries):
            try:
                self.client = MongoClient(self.connection_string)
                # Testar conexão
                self.client.admin.command('ping')
                self.db = self.client.face_recognition_db
                self._setup_collections()
                logger.info("Conexão com MongoDB estabelecida com sucesso")
                return
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Tentativa {attempt + 1} falhou. Tentando novamente em {self.retry_interval}s...")
                    time.sleep(self.retry_interval)
                else:
                    logger.error("Não foi possível conectar ao MongoDB após todas as tentativas")
                    raise

    def _setup_collections(self):
        """Configura coleções e índices"""
        # Configurar coleções
        self.detections = self.db.detections      # Detecções de faces
        self.employees = self.db.employees        # Cadastro de funcionários
        self.batch_control = self.db.batch_control # Controle de lotes de imagens
        self.metrics = self.db.metrics            # Métricas do sistema

        # Criar índices
        self._create_indexes()

    def _create_indexes(self):
        """
        Estrutura das coleções e seus índices:
        
        1. employees (Funcionários):
        {
            "_id": ObjectId,
            "employee_id": str,          # ID único do funcionário
            "name": str,                 # Nome completo
            "department": str,           # Departamento (novo campo)
            "position": str,             # Cargo (novo campo)
            "encoding": list,            # Encoding facial
            "photo_path": str,           # Caminho da foto
            "active": bool,              # Status
            "created_at": datetime,
            "updated_at": datetime
        }
        Índices:
        - employee_id (único)
        - name
        - department
        - position
        
        2. detections (Detecções):
        {
            "_id": ObjectId,
            "employee_id": str,          # ID do funcionário detectado
            "timestamp": datetime,       # Data/hora da detecção
            "production_line": str,      # ID da linha de produção
            "camera_id": str,            # ID da câmera
            "confidence": float,         # Confiança da detecção
            "image_path": str,           # Caminho da imagem
            "batch_id": ObjectId         # ID do lote de processamento
        }
        Índices:
        - timestamp
        - (production_line, timestamp)
        - employee_id
        
        3. batch_control (Controle de Lotes):
        {
            "_id": ObjectId,
            "line_id": str,             # ID da linha de produção
            "batch_path": str,           # Caminho do diretório do lote
            "status": str,              # Status: new, processing, completed, failed
            "created_at": datetime,      # Data de criação do lote
            "processed_at": datetime,    # Data de processamento
            "processor_id": str,         # ID do processador
            "total_images": int,         # Total de imagens no lote
            "processed_images": int,     # Imagens processadas
            "failed_images": int         # Imagens com falha
        }
        Índices:
        - (line_id, status)
        - batch_path (único)
        - created_at
        - processor_id
        
        4. metrics (Métricas):
        {
            "_id": ObjectId,
            "timestamp": datetime,       # Data/hora da métrica
            "type": str,                # Tipo de métrica
            "value": float,             # Valor da métrica
            "production_line": str,      # ID da linha (opcional)
            "camera_id": str,           # ID da câmera (opcional)
            "processor_id": str          # ID do processador
        }
        Índices:
        - timestamp
        """
        # Índices para detections
        self.detections.create_index([("timestamp", 1)])
        self.detections.create_index([("production_line", 1), ("timestamp", 1)])
        self.detections.create_index([("employee_id", 1)])

        # Índices para employees
        self.employees.create_index([("employee_id", 1)], unique=True)
        self.employees.create_index([("name", 1)])
        self.employees.create_index([("department", 1)])
        self.employees.create_index([("position", 1)])

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
        """Retorna todos os encodings conhecidos"""
        try:
            employees = list(self.employees.find({"encoding": {"$exists": True}}))
            
            if not employees:
                logger.info("Nenhum encoding encontrado no banco")
                return [], [], []  # Retornar 3 listas vazias
            
            # Extrair dados
            encodings = [np.array(emp["encoding"]) for emp in employees]
            names = [emp["name"] for emp in employees]
            ids = [str(emp["_id"]) for emp in employees]
            
            logger.info(f"Carregados {len(encodings)} encodings do banco")
            return encodings, names, ids
            
        except Exception as e:
            logger.error(f"Erro ao carregar encodings: {str(e)}")
            return [], [], []  # Em caso de erro, retornar listas vazias

    def register_batch_detection(self, batch_data: Dict) -> None:
        """Registra detecções de um lote"""
        try:
            # Registrar exatamente os campos recebidos, sem adicionar campos extras
            result = self.detections.insert_one(batch_data)
            logger.info(f"Detecções do lote registradas com ID: {result.inserted_id}")
            
        except Exception as e:
            logger.error(f"Erro ao registrar detecções do lote: {str(e)}")
            raise

    def get_pending_batches(self, line_id):
        """Recupera lotes pendentes para uma linha"""
        try:
            query = {
                'line_id': line_id,
                'status': 'pending'
            }
            
            return list(self.batch_control.find(query))
            
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

    def get_encodings_chunk(self, skip=0, limit=100):
        """Retorna chunk de encodings"""
        try:
            employees = list(self.employees
                           .find({"encoding": {"$exists": True}})
                           .skip(skip)
                           .limit(limit))
            
            if not employees:
                return [], [], []
            
            encodings = [np.array(emp["encoding"]) for emp in employees]
            names = [emp["name"] for emp in employees]
            ids = [str(emp["_id"]) for emp in employees]
            
            return encodings, names, ids
            
        except Exception as e:
            logger.error(f"Erro ao carregar chunk de encodings: {str(e)}")
            return [], [], []
            
    def count_total_encodings(self):
        """Retorna total de encodings cadastrados"""
        return self.employees.count_documents({"encoding": {"$exists": True}})

    def find_matching_face(self, face_encoding, tolerance=0.6):
        """
        Busca face mais próxima no banco de dados
        Retorna None se não encontrar match dentro da tolerância
        """
        try:
            # Buscar todos os funcionários com encoding
            employees = self.employees.find({"encoding": {"$exists": True}})
            
            best_match = None
            min_distance = float('inf')
            
            # Comparar com cada funcionário
            for emp in employees:
                stored_encoding = np.array(emp["encoding"])
                distance = face_recognition.face_distance([stored_encoding], face_encoding)[0]
                
                if distance < min_distance and distance <= tolerance:
                    min_distance = distance
                    best_match = {
                        'employee_id': str(emp["_id"]),
                        'name': emp["name"],
                        'confidence': 1 - distance
                    }
            
            return best_match
            
        except Exception as e:
            logger.error(f"Erro ao buscar face no banco: {str(e)}")
            return None 