import requests
from typing import Dict

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        print(f"\nTentando conectar à API: {self.base_url}")
        
        # Testar conexão
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                print("✓ Conectado ao backend com sucesso")
            else:
                print(f"✗ Erro ao conectar: Status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("✗ Erro: Backend não está rodando")
        except Exception as e:
            print(f"✗ Erro ao conectar: {str(e)}")
            
    def get_capture_status(self) -> Dict:
        """
        Retorna status do sistema de captura:
        - Estado do sistema
        - Configuração das câmeras
        - Taxa de captura atual (imagens/minuto)
        - Último frame capturado
        """
        print("\nSolicitando status de captura...")
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            response.raise_for_status()  # Lança exceção para status != 200
            data = response.json()
            print(f"Status recebido: {data}")
            return data
        except requests.exceptions.ConnectionError:
            print("✗ Erro: Não foi possível conectar ao backend")
            return {'error': 'Backend não está respondendo'}
        except Exception as e:
            print(f"✗ Erro ao obter status: {str(e)}")
            return {
                'system_running': False,
                'cameras_configured': False,
                'cameras': {},
                'is_capturing': False,
                'error': str(e)
            }
            
    def get_processor_status(self) -> Dict:
        """Obtém status do processador"""
        try:
            response = requests.get(f"{self.base_url}/processor/status")
            return response.json()
        except Exception as e:
            print(f"Erro ao obter status do processador: {e}")
            return {
                'running': False,
                'error': str(e)
            }

    def create_employee(self, employee_id: str, name: str, photo) -> Dict:
        """Cria novo funcionário"""
        try:
            print(f"\nEnviando foto: tamanho={len(photo.getvalue())} bytes")
            
            # Preparar dados do formulário
            files = {
                'photo': ('photo.jpg', photo.getvalue(), 'image/jpeg'),
                'employee_id': (None, employee_id),
                'name': (None, name)
            }
            
            # Enviar como multipart/form-data
            response = requests.post(
                f"{self.base_url}/employees",
                files=files
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erro ao criar funcionário: {e}")
            return {'error': str(e)}

    def list_employees(self, active_only: bool = True) -> Dict:
        """Lista funcionários"""
        try:
            response = requests.get(f"{self.base_url}/employees", params={'active_only': active_only})
            return response.json()
        except Exception as e:
            print(f"Erro ao listar funcionários: {e}")
            return {'error': str(e)}

    def update_employee(self, employee_id: str, name: str = None, photo = None) -> Dict:
        """Atualiza funcionário"""
        try:
            data = {}
            files = {}
            if name:
                data['name'] = name
            if photo:
                files['photo'] = photo
            
            response = requests.put(f"{self.base_url}/employees/{employee_id}", data=data, files=files)
            return response.json()
        except Exception as e:
            print(f"Erro ao atualizar funcionário: {e}")
            return {'error': str(e)}

    def delete_employee(self, employee_id: str) -> Dict:
        """Remove funcionário"""
        try:
            response = requests.delete(f"{self.base_url}/employees/{employee_id}")
            return response.json()
        except Exception as e:
            print(f"Erro ao remover funcionário: {e}")
            return {'error': str(e)} 