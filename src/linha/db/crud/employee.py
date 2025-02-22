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

    def create(self, data: Dict) -> str:
        """Cria novo funcionário"""
        try:
            # Validar dados obrigatórios
            if not all(k in data for k in ["employee_id", "name", "photo_path"]):
                raise ValueError("Dados incompletos")
            
            # Verificar se já existe
            if self.get(data["employee_id"]):
                raise ValueError("Funcionário já cadastrado")
            
            # Processar foto antes de salvar
            try:
                # Carregar e validar imagem
                image = face_recognition.load_image_file(data["photo_path"])
                if image is None:
                    raise ValueError("Imagem inválida")
                
                # Processar face
                face_encoding, face_location, face_image = self._process_face_image(data["photo_path"])
                
                # Salvar foto em local permanente
                photo_path = self._save_photo(data["photo_path"], data["employee_id"])
                
                # Atualizar dados com informações faciais
                employee_data = {
                    "employee_id": data["employee_id"],
                    "name": data["name"],
                    "photo_path": photo_path,
                    "face_encoding": face_encoding.tolist(),
                    "face_location": list(face_location),
                    "face_quality_score": float(np.mean(np.abs(face_encoding))),
                    "active": True,
                    "created_at": datetime.now()
                }
                
                # Inserir no banco
                result = self.collection.insert_one(employee_data)
                
                logger.info(f"Funcionário criado: {data['employee_id']}")
                return str(result.inserted_id)
                
            except Exception as e:
                # Limpar arquivos em caso de erro
                if 'photo_path' in locals():
                    try:
                        os.remove(photo_path)
                    except:
                        pass
                raise e
            
        except Exception as e:
            logger.error(f"Erro ao criar funcionário: {str(e)}")
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

    def list(self, active_only: bool = True) -> List[Dict]:
        """Lista funcionários"""
        try:
            # Buscar funcionários
            query = {"active": True} if active_only else {}
            cursor = self.collection.find(query)
            
            # Converter para lista de dicts serializáveis
            employees = []
            for emp in cursor:
                employee = {
                    "id": str(emp["_id"]),
                    "employee_id": emp["employee_id"],
                    "name": emp["name"],
                    "active": emp.get("active", True),
                    "photo_path": emp.get("photo_path", ""),
                    "created_at": emp.get("created_at", "").isoformat() if emp.get("created_at") else "",
                    "updated_at": emp.get("updated_at", "").isoformat() if emp.get("updated_at") else ""
                }
                employees.append(employee)
                
            logger.info(f"Listados {len(employees)} funcionários")
            return employees
            
        except Exception as e:
            logger.error(f"Erro ao listar funcionários: {str(e)}")
            return []

    def update(self, employee_id: str, data: Dict) -> bool:
        """
        Atualiza dados do funcionário
        Args:
            employee_id: ID do funcionário
            data: Campos a atualizar
        Returns:
            bool: True se atualizado com sucesso
        """
        try:
            if "photo_path" in data:
                # Salvar nova foto
                new_photo_path = self._save_photo(data["photo_path"], employee_id)
                
                # Processar nova foto facial
                face_encoding, face_location, face_image = self._process_face_image(new_photo_path)
                
                # Remover foto antiga
                old_employee = self.get(employee_id)
                if old_employee and 'photo_path' in old_employee:
                    try:
                        os.remove(old_employee['photo_path'])
                    except:
                        pass
                
                # Atualizar dados faciais
                data.update({
                    "face_encoding": face_encoding.tolist(),
                    "face_location": list(face_location),
                    "photo_path": new_photo_path,
                    "face_quality_score": np.mean(np.abs(face_encoding))
                })
                del data["photo_path"]

            data["updated_at"] = datetime.now()
            
            result = self.collection.update_one(
                {"employee_id": employee_id},
                {"$set": data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Funcionário {employee_id} atualizado")
            return success
            
        except Exception as e:
            logger.error(f"Erro ao atualizar funcionário: {str(e)}")
            # Limpar nova foto em caso de erro
            if 'new_photo_path' in locals():
                try:
                    os.remove(new_photo_path)
                except:
                    pass
            return False

    def delete(self, employee_id: str) -> bool:
        """
        Remove funcionário (soft delete)
        Args:
            employee_id: ID do funcionário
        Returns:
            bool: True se removido com sucesso
        """
        try:
            result = self.update(employee_id, {"active": False})
            if result:
                logger.info(f"Funcionário {employee_id} desativado")
            return result
        except Exception as e:
            logger.error(f"Erro ao desativar funcionário: {str(e)}")
            return False 