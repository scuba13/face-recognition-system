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
        
        # Índices
        self.batch_control.create_index([
            ("line_id", 1),
            ("status", 1),
            ("processor_id", 1)
        ])
        self.batch_control.create_index([("locked_at", 1)], expireAfterSeconds=BATCH_LOCK_TIMEOUT)
        self.employees.create_index([("employee_id", 1)], unique=True)
        self.detections.create_index([("batch_path", 1)], unique=True)

    @backoff.on_exception(backoff.expo, PyMongoError, max_tries=3)
    def register_new_batch(self, line_id: str, batch_path: str):
        """Registra novo lote para processamento"""
        try:
            self.batch_control.insert_one({
                'line_id': line_id,
                'batch_path': batch_path,
                'created_at': datetime.now(),
                'status': 'pending',
                'processor_id': None,
                'processed_at': None,
                'error_message': None
            })
            logger.info(f"Novo lote registrado: {batch_path}")
        except Exception as e:
            logger.error(f"Erro ao registrar lote: {str(e)}")

    def get_pending_batches(self, line_id: str = None):
        """
        Recupera lotes pendentes para processamento
        Args:
            line_id: ID da linha (opcional)
        """
        try:
            query = {
                'status': 'pending',
                'processor_id': None  # Apenas lotes não atribuídos
            }
            
            # Adicionar line_id ao query se fornecido
            if line_id:
                query['line_id'] = line_id
                
            return list(self.batch_control.find(query).limit(10))
        except Exception as e:
            logger.error(f"Erro ao buscar lotes pendentes: {str(e)}")
            return []

    def get_processing_batches(self, line_id: str = None):
        """Retorna lotes em processamento"""
        try:
            query = {'status': 'processing'}
            if line_id:
                query['line_id'] = line_id
            return list(self.batch_control.find(query))
        except Exception as e:
            logger.error(f"Erro ao buscar lotes em processamento: {str(e)}")
            return []

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

    def register_batch_detection(self, detection):
        """Registra detecções de um lote"""
        try:
            self.detections.insert_one(detection.to_dict())
            logger.info(f"Detecções registradas para lote: {detection.batch_path}")
        except Exception as e:
            logger.error(f"Erro ao registrar detecções: {str(e)}")

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

    def get_recent_detections(self, line_id: str = None, days: int = 7):
        """
        Retorna detecções recentes
        Args:
            line_id: ID da linha (opcional)
            days: Número de dias para buscar (default 7)
        """
        try:
            # Calcular data limite
            date_limit = datetime.now() - timedelta(days=days)
            
            # Construir query
            query = {
                'timestamp': {'$gte': date_limit}
            }
            if line_id:
                query['line_id'] = line_id
            
            # Buscar detecções ordenadas por data
            detections = self.detections.find(
                query,
                sort=[('timestamp', -1)]  # Mais recentes primeiro
            )
            
            return list(detections)
            
        except Exception as e:
            logger.error(f"Erro ao buscar detecções recentes: {str(e)}")
            return [] 