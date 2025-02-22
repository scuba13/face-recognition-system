import os
import json
from pathlib import Path
from threading import Lock

# Arquivo para status do backend
STATUS_FILE = Path("backend_status.json")

# Lock para acesso às instâncias globais
_lock = Lock()

# Instâncias globais
_image_capture = None
_face_processor = None

def set_image_capture(instance):
    """Define instância global do ImageCapture"""
    global _image_capture
    with _lock:
        _image_capture = instance

def set_face_processor(instance):
    """Define instância global do FaceProcessor"""
    global _face_processor
    with _lock:
        _face_processor = instance

def get_image_capture():
    """Retorna instância global do ImageCapture"""
    with _lock:
        return _image_capture

def get_face_processor():
    """Retorna instância global do FaceProcessor"""
    with _lock:
        return _face_processor

def save_backend_status(running=True):
    """Salva status do backend"""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump({
                'running': running,
                'pid': os.getpid()
            }, f)
    except Exception as e:
        print(f"Erro ao salvar status: {e}")

def check_backend_status():
    """Verifica se backend está rodando"""
    try:
        if not STATUS_FILE.exists():
            return False
            
        with open(STATUS_FILE) as f:
            status = json.load(f)
            
        # Verificar se processo ainda existe
        pid = status.get('pid')
        if pid:
            try:
                os.kill(pid, 0)  # Testa se processo existe
                return status.get('running', False)
            except OSError:
                return False
                
        return False
    except Exception as e:
        print(f"Erro ao verificar status: {e}")
        return False 