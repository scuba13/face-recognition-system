import logging
import os
from modules.face_processor import FaceProcessor
from modules.db_handler import MongoDBHandler
from config import MONGODB_URI

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

def processar_pasta_funcionarios(pasta="fotos"):
    """Processa todas as fotos na pasta especificada"""
    print(f"\n=== Processando fotos da pasta {pasta} ===")
    
    # Verificar se a pasta existe
    if not os.path.exists(pasta):
        print(f"Erro: Pasta {pasta} não encontrada!")
        return

    # Inicializar módulos
    db_handler = MongoDBHandler(connection_string=MONGODB_URI)
    face_processor = FaceProcessor(db_handler)
    
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
                nome, id_funcionario = nome_base.split('|')
                
                caminho_foto = os.path.join(pasta, arquivo)
                
                print(f"\nProcessando: {nome} (ID: {id_funcionario})")
                
                # Validar formato do nome do arquivo
                if not nome.strip() or not id_funcionario.strip():
                    logger.error(f"Arquivo {arquivo} com formato inválido")
                    continue
                
                # Verificar se ID já existe
                if db_handler.employee_exists(id_funcionario):
                    logger.warning(f"Funcionário {id_funcionario} já cadastrado")
                    continue
                
                if face_processor.register_new_employee(
                    image_path=caminho_foto,
                    name=nome.strip(),
                    employee_id=id_funcionario.strip()
                ):
                    print(f"✓ Funcionário {nome} cadastrado com sucesso!")
                    sucessos += 1
                else:
                    print(f"✗ Erro ao processar foto de {nome}")
                    falhas += 1
                    
            except ValueError:
                print(f"✗ Erro: arquivo {arquivo} não está no formato correto (deve ser 'Nome|ID.jpg')")
                falhas += 1
            except Exception as e:
                print(f"✗ Erro ao processar {arquivo}: {str(e)}")
                falhas += 1

    # Exibir relatório
    print("\n=== Relatório de Processamento ===")
    print(f"Total de arquivos: {total}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {falhas}")

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