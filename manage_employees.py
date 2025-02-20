import logging
import os
from modules.face_processor import FaceProcessor
from modules.db_handler import MongoDBHandler
from config import MONGODB_URI
import face_recognition
import cv2
from datetime import datetime
from pymongo import MongoClient
import numpy as np

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('employees.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EmployeeManager:
    def __init__(self, mongodb_uri="mongodb://mongodb:27017/"):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client.face_recognition_db
        self.employees = self.db.employees

    def add_employee(self, employee_data, photo_path):
        """
        Adiciona um novo funcionário
        Args:
            employee_data: {
                'employee_id': str,      # ID/matrícula do funcionário
                'name': str,             # Nome completo
                'department': str,        # Departamento
                'position': str,          # Cargo
                'active': bool           # Status (default: True)
            }
            photo_path: str - Caminho da foto do funcionário
        """
        try:
            # Verificar se funcionário já existe
            if self.employees.find_one({"employee_id": employee_data['employee_id']}):
                raise ValueError(f"Funcionário com ID {employee_data['employee_id']} já existe")

            # Carregar e processar a foto
            image = face_recognition.load_image_file(photo_path)
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                raise ValueError("Nenhuma face detectada na foto")
            if len(face_locations) > 1:
                raise ValueError("Múltiplas faces detectadas na foto")
            
            # Gerar encoding facial
            encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # Preparar documento para inserção
            employee_doc = {
                **employee_data,
                'encoding': encoding.tolist(),  # Converter numpy array para lista
                'photo_path': photo_path,
                'active': employee_data.get('active', True),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Inserir no banco
            result = self.employees.insert_one(employee_doc)
            logger.info(f"Funcionário {employee_data['name']} cadastrado com sucesso")
            return result.inserted_id
            
        except Exception as e:
            logger.error(f"Erro ao cadastrar funcionário: {str(e)}")
            raise

    def update_employee(self, employee_id, update_data, new_photo_path=None):
        """
        Atualiza dados do funcionário
        Args:
            employee_id: str - ID do funcionário
            update_data: dict - Dados a serem atualizados
            new_photo_path: str - Nova foto (opcional)
        """
        try:
            update_doc = {
                **update_data,
                'updated_at': datetime.now()
            }
            
            if new_photo_path:
                # Processar nova foto
                image = face_recognition.load_image_file(new_photo_path)
                encoding = face_recognition.face_encodings(image)[0]
                update_doc.update({
                    'encoding': encoding.tolist(),
                    'photo_path': new_photo_path
                })
            
            result = self.employees.update_one(
                {'employee_id': employee_id},
                {'$set': update_doc}
            )
            
            if result.modified_count:
                logger.info(f"Funcionário {employee_id} atualizado com sucesso")
            else:
                logger.warning(f"Funcionário {employee_id} não encontrado")
                
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Erro ao atualizar funcionário: {str(e)}")
            raise

    def deactivate_employee(self, employee_id):
        """Desativa um funcionário"""
        return self.update_employee(employee_id, {'active': False})

    def get_employee(self, employee_id):
        """Retorna dados de um funcionário"""
        return self.employees.find_one({'employee_id': employee_id})

    def list_employees(self, department=None, active_only=True):
        """Lista funcionários com filtros opcionais"""
        query = {'active': True} if active_only else {}
        if department:
            query['department'] = department
        
        return list(self.employees.find(query))

def processar_pasta_funcionarios(pasta="fotos"):
    """Processa todas as fotos na pasta especificada"""
    logger.info(f"Processando fotos da pasta {pasta}")
    
    # Verificar se a pasta existe
    if not os.path.exists(pasta):
        logger.error(f"Pasta {pasta} não encontrada!")
        return

    # Inicializar módulos
    db_handler = MongoDBHandler(connection_string=MONGODB_URI)
    
    # Contadores para relatório
    total = 0
    sucessos = 0
    falhas = 0

    # Processar cada arquivo
    for arquivo in os.listdir(pasta):
        if arquivo.endswith(('.jpg', '.jpeg', '.png')):
            total += 1
            try:
                # Nome do arquivo deve ser: "Nome Completo|123456.jpg"
                nome_base = os.path.splitext(arquivo)[0]
                if '|' not in nome_base:
                    logger.error(f"Arquivo {arquivo} não está no formato 'Nome|ID.jpg'")
                    falhas += 1
                    continue
                    
                nome, id_funcionario = nome_base.split('|')
                caminho_foto = os.path.join(pasta, arquivo)
                
                logger.info(f"Processando: {nome} (ID: {id_funcionario})")
                
                # Carregar e processar a foto
                image = face_recognition.load_image_file(caminho_foto)
                face_locations = face_recognition.face_locations(image)
                
                if not face_locations:
                    logger.error(f"Nenhuma face detectada na foto de {nome}")
                    falhas += 1
                    continue
                    
                if len(face_locations) > 1:
                    logger.error(f"Múltiplas faces detectadas na foto de {nome}")
                    falhas += 1
                    continue
                
                # Gerar encoding facial
                encoding = face_recognition.face_encodings(image, face_locations)[0]
                
                # Preparar dados do funcionário
                employee_data = {
                    'employee_id': id_funcionario.strip(),
                    'name': nome.strip(),
                    'encoding': encoding.tolist(),
                    'photo_path': caminho_foto,
                    'active': True,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                # Inserir no banco
                db_handler.employees.insert_one(employee_data)
                logger.info(f"Funcionário {nome} cadastrado com sucesso")
                sucessos += 1
                
            except Exception as e:
                logger.error(f"Erro ao processar {arquivo}: {str(e)}")
                falhas += 1

    # Registrar resultado final
    logger.info(f"""
    === Relatório de Processamento ===
    Total de arquivos: {total}
    Sucessos: {sucessos}
    Falhas: {falhas}
    """)
    
    return sucessos > 0  # Retorna True se pelo menos um funcionário foi cadastrado

def main():
    while True:
        print("\n=== Menu de Gerenciamento ===")
        print("1. Processar pasta de fotos")
        print("0. Sair")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            pasta = input("Caminho da pasta com as fotos (Enter para usar 'fotos'): ").strip()
            if not pasta:
                pasta = "fotos"
            processar_pasta_funcionarios(pasta)
        elif opcao == "0":
            break
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    main() 