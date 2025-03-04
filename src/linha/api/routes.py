from datetime import datetime, timedelta
from fastapi import APIRouter, File, Form, UploadFile
from linha.core.instance import (
    get_image_capture,
    get_face_processor,
    get_db_handler,  # Importar do instance.py ao invés de handler.py
    set_image_capture
)
from typing import Optional
from linha.config.settings import (
    FACE_RECOGNITION_TOLERANCE,  # Adicionar import
    PRODUCTION_LINES
)
from linha.core.capture_factory import CaptureFactory
import face_recognition
import io
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Criar o router
router = APIRouter()

# Tentar importar e incluir router de configurações
try:
    from linha.api.settings_routes import router as settings_router
    router.include_router(settings_router)
    print("✓ Router de configurações incluído com sucesso")
except Exception as e:
    print(f"✗ Erro ao importar router de configurações: {str(e)}")
    logger.error(f"Erro ao importar router de configurações: {str(e)}")

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
def get_processor_status(hours: int = 24):
    """Retorna métricas do processador"""
    try:
        print(f"\n=== API: Status do Processador (últimas {hours} horas) ===")
        
        # Get instance
        db_handler = get_db_handler()
        
        # Buscar todas as métricas direto do MongoDB com filtro de horas
        stats = db_handler.get_processor_statistics(hours=hours)
        
        # Formatar resposta
        response = {
            'avg_processing_time': stats['avg_processing_time'],
            'avg_images_per_batch': stats['avg_images_per_batch'],
            'total_faces_detected': stats['total_faces_detected'],
            'total_faces_recognized': stats['total_faces_recognized'], 
            'total_faces_unknown': stats['total_faces_unknown'],
            'avg_distance': stats['avg_distance'],
            'tolerance': FACE_RECOGNITION_TOLERANCE,
            'pending_batches': stats['pending_batches'],
            'processing_batches': stats['processing_batches'],
            'completed_batches': stats['completed_batches'],
            'error_batches': stats['error_batches'],
            'hourly_stats': stats['hourly_stats']
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
        face_processor = get_face_processor()
        
        # Build simple response
        dashboard = {
            'total_employees': len(db_handler.employee_crud.list(True)),
            'active_cameras': 0,  # Zero quando não há captura
            'system_status': 'Offline'  # Offline quando não há processamento
        }
        
        # Atualizar status apenas se os serviços estiverem rodando
        if image_capture:
            dashboard['active_cameras'] = len([
                c for c in image_capture.get_status().get('cameras', {}).values() 
                if c.get('is_opened', False)
            ])
            
        if face_processor:
            dashboard['system_status'] = 'Online' if face_processor.running else 'Offline'
        
        print(f"Dashboard montado: {dashboard}")
        return dashboard
        
    except Exception as e:
        print(f"✗ Erro no dashboard: {str(e)}")
        return {'error': str(e)}

@router.get("/detections")
def get_detections(days: int = 1):
    """Retorna detecções dos últimos X dias"""
    try:
        print(f"\n=== API: Buscando detecções dos últimos {days} dias ===")
        
        # Get instance
        db_handler = get_db_handler()
        if not db_handler:
            return {'error': 'DB Handler não inicializado'}
        
        # Buscar detecções
        result = db_handler.get_recent_detections(days=days)
        
        # Verificar se é um erro
        if isinstance(result, dict) and 'error' in result:
            return result
            
        # Retornar lista de detecções
        return {
            'detections': result,
            'total': len(result),
            'days': days
        }
        
    except Exception as e:
        print(f"✗ Erro: {str(e)}")
        return {'error': str(e)}

@router.post("/capture/mode")
def set_capture_mode(mode: str):
    """
    Altera o modo de captura entre 'interval' e 'motion'
    
    Args:
        mode: Tipo de captura ('interval' ou 'motion')
    """
    try:
        print(f"\n=== API: Alterando modo de captura para: {mode} ===")
        
        # Validar modo
        if mode not in ['interval', 'motion']:
            return {'error': f'Modo inválido: {mode}. Use "interval" ou "motion"'}
        
        # Obter instância atual
        current_capture = get_image_capture()
        if not current_capture:
            return {'error': 'Sistema de captura não inicializado'}
        
        # Verificar se já está no modo desejado
        current_mode = getattr(current_capture, 'capture_type', 'interval')
        if hasattr(current_capture, 'get_status'):
            status = current_capture.get_status()
            current_mode = status.get('capture_type', current_mode)
            
        if current_mode == mode:
            return {
                'message': f'Sistema já está no modo {mode}',
                'changed': False,
                'current_mode': mode
            }
        
        # Parar captura atual
        print(f"Parando sistema de captura atual ({current_mode})...")
        current_capture.stop_capture()
        
        # Criar nova instância com o modo desejado
        print(f"Criando nova instância de captura ({mode})...")
        new_capture = CaptureFactory.create_capture(
            production_lines=PRODUCTION_LINES,
            capture_type=mode
        )
        
        # Configurar e iniciar nova instância
        db_handler = get_db_handler()
        if db_handler:
            new_capture.set_db_handler(db_handler)
            
        new_capture.start_capture()
        
        # Atualizar instância global
        set_image_capture(new_capture)
        
        return {
            'message': f'Modo de captura alterado para {mode}',
            'changed': True,
            'previous_mode': current_mode,
            'current_mode': mode
        }
        
    except Exception as e:
        print(f"✗ Erro ao alterar modo de captura: {str(e)}")
        return {'error': str(e)} 