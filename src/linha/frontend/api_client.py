import requests
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        print(f"\nTentando conectar à API: {self.base_url}")
        
        # Verificar se API está online
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✓ API está online")
            else:
                print(f"✗ Erro ao verificar API: Status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("✗ Erro: API não está respondendo")
        except Exception as e:
            print(f"✗ Erro ao conectar: {str(e)}")
            
    def get_capture_status(self) -> Dict:
        """Retorna status das câmeras"""
        try:
            print(f"\nChamando GET {self.base_url}/cameras/status")
            response = requests.get(f"{self.base_url}/cameras/status", timeout=5)
            data = response.json()
            print(f"Resposta: {data}")
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)}
            
    def get_processor_status(self, hours: int = 24) -> Dict:
        """Retorna status do processador"""
        try:
            print(f"\nChamando GET {self.base_url}/processor/status")
            response = requests.get(
                f"{self.base_url}/processor/status",
                params={'hours': hours},
                timeout=5
            )
            data = response.json()
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)}

    def create_employee(self, employee_id: str, name: str, photo) -> Dict:
        """Cria novo funcionário"""
        try:
            print(f"\nChamando POST {self.base_url}/employees")
            print(f"Dados: id={employee_id}, name={name}, photo={len(photo.getvalue())} bytes")
            
            files = {
                'photo': ('photo.jpg', photo.getvalue(), 'image/jpeg'),
                'employee_id': (None, employee_id),
                'name': (None, name)
            }
            
            response = requests.post(f"{self.base_url}/employees", files=files)
            data = response.json()
            print(f"Resposta: {data}")
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)}

    def list_employees(self, active_only: bool = True) -> Dict:
        """Lista funcionários"""
        try:
            print(f"\nChamando GET {self.base_url}/employees")
            response = requests.get(f"{self.base_url}/employees", params={'active_only': active_only})
            data = response.json()
            print(f"Resposta: {data}")
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)}

    def update_employee(self, employee_id: str, name: str = None, photo = None, active: bool = None):
        """Atualiza funcionário"""
        try:
            print(f"\nChamando PUT {self.base_url}/employees/{employee_id}")
            print(f"Dados: name={name}, active={active}, photo={'sim' if photo else 'não'}")
            
            files = {}
            if name is not None:
                files['name'] = (None, name)
            if active is not None:
                files['active'] = (None, str(active))
            if photo is not None:
                files['photo'] = ('photo.jpg', photo.getvalue(), 'image/jpeg')
            
            response = requests.put(f"{self.base_url}/employees/{employee_id}", files=files)
            data = response.json()
            print(f"Resposta: {data}")
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)}

    def delete_employee(self, employee_id: str) -> Dict:
        """Remove funcionário"""
        try:
            print(f"\nChamando DELETE {self.base_url}/employees/{employee_id}")
            response = requests.delete(f"{self.base_url}/employees/{employee_id}")
            data = response.json()
            print(f"Resposta: {data}")
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)}

    def get_dashboard(self) -> Dict:
        """Retorna dados do dashboard"""
        try:
            print(f"\nChamando GET {self.base_url}/dashboard")
            response = requests.get(f"{self.base_url}/dashboard")
            data = response.json()
            print(f"Resposta: {data}")
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)}

    def health_check(self) -> Dict:
        """Verifica se API está online"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return {'status': 'ok'}
            return {'error': f'Status code: {response.status_code}'}
        except requests.exceptions.ConnectionError:
            return {'error': 'API não está respondendo'}
        except Exception as e:
            return {'error': str(e)}

    def get_detections(self, days: int = 1) -> Dict:
        """Retorna detecções dos últimos X dias"""
        try:
            print(f"\nChamando GET {self.base_url}/detections")
            response = requests.get(
                f"{self.base_url}/detections",
                params={'days': days},
                timeout=5
            )
            data = response.json()
            return data
        except Exception as e:
            print(f"✗ Erro: {str(e)}")
            return {'error': str(e)} 