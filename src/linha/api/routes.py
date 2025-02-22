from datetime import datetime, timedelta
from fastapi import APIRouter, File, Form, UploadFile
from linha.core.instance import (
    get_image_capture,
    get_face_processor,
    get_db_handler  # Importar do instance.py ao invés de handler.py
)
from typing import Optional
from linha.config.settings import FACE_RECOGNITION_TOLERANCE  # Adicionar import
import face_recognition
import io

# Criar o router
router = APIRouter()

# Adicionar log para debug
print("\n=== Configurando Rotas ===")

@router.get("/cameras/status")
def get_cameras_status():
    """Retorna status das câmeras"""
    print("Registrando rota: /cameras/status")
    try:
        print("\n=== API: Status das Câmeras ===")
        image_capture = get_image_capture()
        
        if not image_capture:
            return {
                'error': 'Sistema de câmeras não inicializado',
                'system_running': False,
                'cameras_configured': False,
                'cameras': {},
                'is_capturing': False
            }
            
        camera_status = image_capture.get_status()
        print(f"Status das câmeras: {camera_status}")
        return camera_status
        
    except Exception as e:
        print(f"✗ Erro nas câmeras: {str(e)}")
        return {
            'error': str(e),
            'system_running': False,
            'cameras_configured': False,
            'cameras': {},
            'is_capturing': False
        }

@router.get("/processor/status")
def get_processor_status():
    """Retorna métricas do processador"""
    try:
        print("\n=== API: Status do Processador ===")
        
        # Get instances
        db_handler = get_db_handler()
        face_processor = get_face_processor()
        
        # Buscar estatísticas do MongoDB (últimas 24h, limitado a 100 registros)
        pipeline = [
            {
                '$match': {
                    'timestamp': {
                        '$gte': datetime.now() - timedelta(hours=24)
                    }
                }
            },
            {
                '$sort': {'timestamp': -1}  # Ordenar mais recentes primeiro
            },
            {
                '$limit': 100  # Limitar a 100 registros
            },
            {
                '$group': {
                    '_id': {
                        'hour': {'$dateToString': {'format': "%H:00", 'date': "$timestamp"}}
                    },
                    'total_faces': {'$sum': '$faces_detected'},
                    'recognized_faces': {'$sum': '$faces_recognized'},
                    'unknown_faces': {'$sum': '$faces_unknown'},
                    'total_batches': {'$sum': 1},
                    'avg_time': {'$avg': '$processing_time'},
                    'avg_confidence': {'$avg': '$avg_confidence'}
                }
            },
            {
                '$sort': {'_id.hour': 1}
            }
        ]
        
        hourly_stats = list(db_handler.db.batch_detections.aggregate(pipeline))
        
        # Calcular totais
        total_faces = sum(stat['total_faces'] for stat in hourly_stats)
        total_recognized = sum(stat['recognized_faces'] for stat in hourly_stats)
        total_unknown = sum(stat['unknown_faces'] for stat in hourly_stats)
        
        # Status atual dos lotes (últimos 100)
        batch_stats = db_handler.db.batch_control.aggregate([
            {
                '$sort': {'timestamp': -1}
            },
            {
                '$limit': 100
            },
            {
                '$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }
            }
        ])
        
        batch_counts = {
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'error': 0
        }
        
        for stat in batch_stats:
            status = stat['_id']
            count = stat['count']
            if status == 'pending':
                batch_counts['pending'] = count
            elif status == 'processing':
                batch_counts['processing'] = count
            elif status == 'completed':
                batch_counts['completed'] = count
            elif status == 'error':
                batch_counts['error'] = count
        
        # Formatar resposta
        response = {
            'avg_processing_time': sum(stat['avg_time'] for stat in hourly_stats) / len(hourly_stats) if hourly_stats else 0,
            'total_faces_detected': total_faces,
            'total_faces_recognized': total_recognized,
            'total_faces_unknown': total_unknown,
            'avg_distance': sum(stat['avg_confidence'] for stat in hourly_stats) / len(hourly_stats) if hourly_stats else 0,
            'tolerance': FACE_RECOGNITION_TOLERANCE,
            'pending_batches': batch_counts['pending'],
            'processing_batches': batch_counts['processing'],
            'completed_batches': batch_counts['completed'],
            'error_batches': batch_counts['error'],
            'hourly_stats': [
                {
                    'hour': stat['_id']['hour'],
                    'total_batches': stat['total_batches'],
                    'total_faces': stat['total_faces']
                }
                for stat in hourly_stats
            ]
        }
        
        print(f"Métricas calculadas: {response}")
        return response
        
    except Exception as e:
        print(f"✗ Erro: {str(e)}")
        return {'error': str(e)}

@router.get("/health")
def health_check():
    """Verifica se a API está online"""
    print("Registrando rota: /health")
    try:
        print("\n=== API: Health Check ===")
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"✗ Erro no health check: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

@router.post("/employees")
async def create_employee(
    employee_id: str = Form(...),
    name: str = Form(...),
    photo: UploadFile = File(...)
):
    """Cria novo funcionário"""
    try:
        print(f"\n=== API: Criando funcionário {name} (ID: {employee_id}) ===")
        
        # Verificar banco
        db_handler = get_db_handler()
        if not db_handler:
            return {'error': 'Banco de dados não conectado'}
            
        # Ler foto
        photo_bytes = await photo.read()
        
        # Gerar encoding da face
        image = face_recognition.load_image_file(io.BytesIO(photo_bytes))
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            return {'error': 'Nenhuma face detectada na foto'}
            
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
        
        # Criar funcionário com encoding
        result = db_handler.employee_crud.create(
            id=employee_id,
            name=name,
            photo=photo_bytes,
            face_encoding=face_encoding.tolist()  # Converter numpy array para lista
        )
        
        print(f"Funcionário criado: {result}")
        return result
        
    except Exception as e:
        print(f"✗ Erro ao criar funcionário: {str(e)}")
        return {'error': str(e)}

@router.get("/employees")
def list_employees(active_only: bool = True):
    """Lista funcionários"""
    try:
        print("\n=== API: Listando funcionários ===")
        
        # Verificar banco
        db_handler = get_db_handler()
        if not db_handler:
            return {'error': 'Banco de dados não conectado'}
            
        # Buscar funcionários - mudando para list()
        employees = db_handler.employee_crud.list(active_only)
        print(f"Funcionários encontrados: {len(employees)}")
        
        return {'employees': employees}
        
    except Exception as e:
        print(f"✗ Erro ao listar funcionários: {str(e)}")
        return {'error': str(e)}

@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: str):
    """Remove funcionário"""
    try:
        print(f"\n=== API: Removendo funcionário {employee_id} ===")
        
        # Verificar banco
        db_handler = get_db_handler()
        if not db_handler:
            return {'error': 'Banco de dados não conectado'}
            
        # Remover funcionário
        if db_handler.employee_crud.delete(employee_id):
            print(f"✓ Funcionário {employee_id} removido")
            return {'success': True}
        else:
            print(f"✗ Funcionário {employee_id} não encontrado")
            return {'error': 'Funcionário não encontrado'}
        
    except Exception as e:
        print(f"✗ Erro ao remover funcionário: {str(e)}")
        return {'error': str(e)}

@router.put("/employees/{employee_id}")
async def update_employee(
    employee_id: str,
    name: str = Form(None),
    photo: UploadFile = File(None),
    active: bool = Form(None)
):
    """Atualiza funcionário"""
    try:
        print(f"\n=== API: Atualizando funcionário {employee_id} ===")
        print(f"Dados recebidos: name={name}, active={active}")
        
        # Verificar banco
        db_handler = get_db_handler()
        if not db_handler:
            return {'error': 'Banco de dados não conectado'}
            
        # Preparar dados
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if active is not None:
            update_data["active"] = active
            
        # Processar foto se enviada
        if photo:
            photo_bytes = await photo.read()
            update_data["photo"] = photo_bytes
            
        print(f"Dados para atualização: {update_data}")
        
        # Atualizar funcionário
        if db_handler.employee_crud.update(employee_id, update_data):
            print(f"✓ Funcionário {employee_id} atualizado com {update_data}")
            return {'success': True}
        else:
            print(f"✗ Funcionário {employee_id} não encontrado")
            return {'error': 'Funcionário não encontrado'}
        
    except Exception as e:
        print(f"✗ Erro ao atualizar funcionário: {str(e)}")
        return {'error': str(e)}

@router.get("/dashboard")
def get_dashboard():
    """Retorna dados simplificados para dashboard"""
    try:
        print("\n=== API: Dashboard ===")
        
        # Get instances
        db_handler = get_db_handler()
        print("✓ DB Handler obtido")
        
        image_capture = get_image_capture()
        print("✓ Image Capture obtido")
        
        face_processor = get_face_processor()
        print("✓ Face Processor obtido")
        
        # Build simple response
        dashboard = {
            'total_employees': len(db_handler.employee_crud.list()),
            'active_cameras': len([c for c in image_capture.get_status().get('cameras', {}).values() if c.get('is_opened', False)]),
            'system_status': 'Online' if face_processor.running else 'Offline'
        }
        
        print(f"Dashboard montado: {dashboard}")
        return dashboard
        
    except Exception as e:
        print(f"✗ Erro no dashboard: {str(e)}")
        return {'error': str(e)} 