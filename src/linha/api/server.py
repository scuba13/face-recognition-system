from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from linha.core.instance import get_image_capture, get_face_processor
import tempfile
import os
from datetime import datetime
from linha.config.settings import EMPLOYEES_DIR

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def get_status():
    """Retorna status do sistema de captura"""
    print("\n=== API: Recebida solicitação de status ===")
    try:
        image_capture = get_image_capture()
        if not image_capture:
            print("✗ Sistema não inicializado")
            return {"error": "Sistema não inicializado"}
            
        # Montar status manualmente
        status = {
            'system_running': image_capture.running,
            'cameras_configured': bool(image_capture.cameras),
            'cameras': {},
            'is_capturing': image_capture.running and bool(image_capture.cameras)
        }
        
        # Status por câmera
        for line_id, cameras in image_capture.production_lines.items():
            for cam in cameras:
                camera_key = f"{line_id}_usb_{cam['id']}"
                camera_status = {
                    'name': cam['name'],
                    'position': cam['position'],
                    'is_configured': camera_key in image_capture.cameras,
                    'is_opened': False,
                    'can_capture': False,
                    'last_image_time': image_capture.last_capture_time.get(camera_key, None),
                    'fps': image_capture.get_camera_fps(camera_key)
                }
                
                if camera_key in image_capture.cameras:
                    camera = image_capture.cameras[camera_key]
                    camera_status['is_opened'] = camera.isOpened()
                    if camera_status['is_opened']:
                        ret, _ = camera.read()
                        camera_status['can_capture'] = ret
                
                status['cameras'][camera_key] = camera_status
                
        print(f"Status enviado: {status}")
        return status
        
    except Exception as e:
        print(f"✗ Erro ao obter status: {str(e)}")
        return {"error": str(e)}

@app.get("/cameras")
async def get_cameras():
    """Retorna lista de câmeras configuradas"""
    image_capture = get_image_capture()
    if not image_capture:
        return {"error": "Sistema não inicializado"}
        
    return {
        "cameras": image_capture.cameras,
        "production_lines": image_capture.production_lines
    }

@app.get("/processor/status")
async def get_processor_status():
    """Retorna status do processador facial"""
    face_processor = get_face_processor()
    if not face_processor:
        return {"error": "Processador não inicializado"}
        
    # Buscar detecções recentes
    try:
        recent_detections = face_processor.db_handler.detections.find().sort([("timestamp", -1)]).limit(100)
        recent_detections = list(recent_detections)
        # Converter ObjectId e datetime para string
        for det in recent_detections:
            det['_id'] = str(det['_id'])
            if 'timestamp' in det:
                det['timestamp'] = det['timestamp'].isoformat()
    except Exception as e:
        print(f"Erro ao buscar detecções: {e}")
        recent_detections = []
        
    return {
        "running": face_processor.running,
        "pending_batches": len(face_processor.db_handler.get_pending_batches()),
        "processing_batches": len(face_processor.db_handler.get_processing_batches()),
        "completed_batches": len(face_processor.db_handler.get_completed_batches()),
        "recent_detections": recent_detections
    }

@app.post("/employees")
async def create_employee(
    employee_id: str = Form(...),
    name: str = Form(...),
    photo: UploadFile = File(...)
):
    """Cria novo funcionário"""
    print("\n=== API: Criando funcionário ===")
    temp_path = None
    try:
        face_processor = get_face_processor()
        if not face_processor:
            print("✗ Sistema não inicializado")
            return {"error": "Sistema não inicializado"}
            
        print(f"Dados recebidos: id={employee_id}, name={name}, photo={photo.filename}")
            
        # Salvar foto temporariamente na pasta correta
        temp_path = os.path.join(EMPLOYEES_DIR, f"temp_{photo.filename}")
        content = await photo.read()
        with open(temp_path, "wb") as f:
            f.write(content)
            
        # Criar funcionário usando o CRUD existente
        result = face_processor.db_handler.employee_crud.create({
            "employee_id": employee_id,
            "name": name,
            "photo_path": temp_path,
            "active": True
        })
        
        print(f"✓ Funcionário criado com ID: {result}")
        return {"success": True, "id": result}
        
    except Exception as e:
        print(f"✗ Erro ao criar funcionário: {str(e)}")
        return {"error": str(e)}
    finally:
        # Limpar arquivo temporário se ainda existir
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

@app.get("/employees")
async def list_employees(active_only: bool = True):
    """Lista funcionários"""
    print("\n=== API: Listando funcionários ===")
    try:
        face_processor = get_face_processor()
        if not face_processor:
            print("✗ Sistema não inicializado")
            return {"error": "Sistema não inicializado"}
            
        # Usar o método list do CRUD
        employees = face_processor.db_handler.employee_crud.list(active_only)
        print(f"✓ Funcionários encontrados: {len(employees)}")
        
        # Verificar dados antes de retornar
        response = {"employees": employees}
        print(f"Dados retornados: {response}")
        return response
        
    except Exception as e:
        print(f"✗ Erro ao listar funcionários: {str(e)}")
        return {"error": str(e)}

@app.put("/employees/{employee_id}")
async def update_employee(employee_id: str, name: str = None, photo: UploadFile = None):
    """Atualiza funcionário"""
    try:
        face_processor = get_face_processor()
        if not face_processor:
            return {"error": "Sistema não inicializado"}
            
        update_data = {}
        if name:
            update_data["name"] = name
            
        if photo:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                tmp.write(photo.file.read())
                update_data["photo_path"] = tmp.name
                
        result = face_processor.db_handler.employee_crud.update(employee_id, update_data)
        
        if "photo_path" in update_data:
            os.unlink(update_data["photo_path"])
            
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str):
    """Remove funcionário"""
    try:
        face_processor = get_face_processor()
        if not face_processor:
            return {"error": "Sistema não inicializado"}
            
        result = face_processor.db_handler.employee_crud.delete(employee_id)
        return {"success": result}
    except Exception as e:
        return {"error": str(e)}

def start_api_server():
    """Inicia servidor API"""
    uvicorn.run(app, host="0.0.0.0", port=8000) 