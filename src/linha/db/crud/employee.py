import logging
import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional
import face_recognition
import numpy as np
from linha.config.settings import EMPLOYEES_DIR
from bson import ObjectId

logger = logging.getLogger(__name__)

class EmployeeCRUD:
    """CRUD para gerenciamento de funcionários"""
    
    def __init__(self, db):
        """
        Args:
            db: Instância do MongoDBHandler
        """
        self.db = db
        self.collection = db.db.employees
        # Garantir que a pasta de fotos existe
        os.makedirs(EMPLOYEES_DIR, exist_ok=True)

    def _save_photo(self, photo_path: str, employee_id: str) -> str:
        """
        Salva foto do funcionário na pasta correta
        Args:
            photo_path: Caminho original da foto
            employee_id: ID do funcionário
        Returns:
            str: Novo caminho da foto
        """
        # Criar nome do arquivo: ID_TIMESTAMP.extensão
        extension = os.path.splitext(photo_path)[1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{employee_id}_{timestamp}{extension}"
        
        # Caminho final da foto
        new_path = os.path.join(EMPLOYEES_DIR, filename)
        
        # Copiar foto para pasta de funcionários
        shutil.copy2(photo_path, new_path)
        logger.info(f"Foto salva em: {new_path}")
        
        return new_path

    def _process_face_image(self, image_path: str) -> tuple:
        """Processa imagem facial e gera encoding"""
        try:
            print(f"\nProcessando imagem: {image_path}")
            print(f"Arquivo existe: {os.path.exists(image_path)}")
            print(f"Tamanho: {os.path.getsize(image_path)} bytes")
            
            # Carregar e verificar imagem
            image = face_recognition.load_image_file(image_path)
            if image is None:
                raise ValueError("Não foi possível carregar a imagem")
            
            print(f"Imagem carregada: {image.shape}")

            # Detectar faces
            face_locations = face_recognition.face_locations(image, model="hog")
            if not face_locations:
                raise ValueError("Nenhum rosto encontrado na foto")
            if len(face_locations) > 1:
                raise ValueError("Múltiplos rostos encontrados. Use uma foto com apenas um rosto")

            # Extrair área do rosto
            top, right, bottom, left = face_locations[0]
            face_image = image[top:bottom, left:right]

            # Gerar encoding facial
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]

            return face_encoding, face_locations[0], face_image

        except Exception as e:
            logger.error(f"Erro ao processar imagem facial: {str(e)}")
            raise

    def create(self, id: str, name: str, photo: bytes, face_encoding: list = None):
        """Cria novo funcionário"""
        try:
            # Criar diretório se não existir
            employee_dir = os.path.join(EMPLOYEES_DIR, id)
            os.makedirs(employee_dir, exist_ok=True)
            
            # Salvar foto
            photo_path = os.path.join(employee_dir, "photo.jpg")
            with open(photo_path, "wb") as f:
                f.write(photo)
            
            # Criar documento
            employee = {
                "employee_id": id,
                "name": name,
                "photo_path": photo_path,
                "face_encoding": face_encoding,
                "active": True,
                "created_at": datetime.now()
            }
            
            # Inserir no banco
            result = self.collection.insert_one(employee)
            print(f"✓ Funcionário criado com ID: {result.inserted_id}")
            
            return {
                "employee_id": id,
                "name": name,
                "photo_path": photo_path
            }
            
        except Exception as e:
            print(f"✗ Erro ao criar funcionário: {e}")
            raise

    def get(self, employee_id: str) -> Optional[Dict]:
        """
        Retorna funcionário por ID
        Args:
            employee_id: ID do funcionário
        Returns:
            Dict: Dados do funcionário ou None se não encontrado
        """
        try:
            return self.collection.find_one({"employee_id": employee_id})
        except Exception as e:
            logger.error(f"Erro ao buscar funcionário: {str(e)}")
            return None

    def list(self, active_only: bool = True):
        """Lista funcionários"""
        try:
            # Filtro de ativos
            query = {"active": True} if active_only else {}
            
            # Buscar funcionários
            employees = []
            for doc in self.collection.find(query):
                employees.append({
                    "employee_id": doc["employee_id"],
                    "name": doc["name"],
                    "photo_path": doc["photo_path"],
                    "active": doc["active"],
                    "created_at": doc["created_at"].isoformat()
                })
                
            print(f"✓ {len(employees)} funcionários encontrados")
            return employees
            
        except Exception as e:
            print(f"✗ Erro ao listar funcionários: {e}")
            raise

    def update(self, employee_id: str, data: dict) -> bool:
        """Atualiza funcionário"""
        try:
            # Processar foto se enviada
            if "photo" in data:
                # Criar diretório se não existir
                employee_dir = os.path.join(EMPLOYEES_DIR, employee_id)
                os.makedirs(employee_dir, exist_ok=True)
                
                # Salvar nova foto
                photo_path = os.path.join(employee_dir, "photo.jpg")
                with open(photo_path, "wb") as f:
                    f.write(data.pop("photo"))
                data["photo_path"] = photo_path
                
            # Atualizar no banco
            result = self.collection.update_one(
                {"employee_id": employee_id},
                {"$set": data}
            )
            
            success = result.modified_count > 0
            if success:
                print(f"✓ Funcionário {employee_id} atualizado")
            else:
                print(f"✗ Funcionário {employee_id} não encontrado")
            
            return success
            
        except Exception as e:
            print(f"✗ Erro ao atualizar funcionário: {e}")
            raise

    def delete(self, employee_id: str) -> bool:
        """Remove funcionário"""
        try:
            # Buscar funcionário
            result = self.collection.update_one(
                {"employee_id": employee_id},
                {"$set": {"active": False}}
            )
            
            success = result.modified_count > 0
            if success:
                print(f"✓ Funcionário {employee_id} removido")
            else:
                print(f"✗ Funcionário {employee_id} não encontrado")
            
            return success
            
        except Exception as e:
            print(f"✗ Erro ao remover funcionário: {e}")
            raise 