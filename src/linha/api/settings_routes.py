from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
import os
from linha.core.instance import get_image_capture, get_face_processor
from linha.config.settings import (
    MOTION_THRESHOLD,
    MOTION_MIN_AREA,
    MOTION_DRAW_CONTOURS,
    MOTION_CAPTURE_FRAMES,
    MOTION_CAPTURE_INTERVAL,
    FACE_RECOGNITION_TOLERANCE,
    ENABLE_PREPROCESSING,
    FACE_PROCESSOR_MAX_WORKERS,
    CAPTURE_MAX_WORKERS,
    MOTION_DETECTION_MAX_WORKERS,
    ENABLE_CAPTURE,
    ENABLE_PROCESSING
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["settings"])

# Modelos para validação de dados
class MotionSettings(BaseModel):
    threshold: Optional[float] = Field(None, description="Limiar para detecção de movimento")
    min_area: Optional[float] = Field(None, description="Área mínima para considerar movimento")
    draw_contours: Optional[bool] = Field(None, description="Desenhar contornos nos frames")
    capture_frames: Optional[int] = Field(None, description="Número de frames a capturar quando detectar movimento")
    capture_interval: Optional[float] = Field(None, description="Intervalo entre frames em segundos")

class ProcessingSettings(BaseModel):
    face_recognition_tolerance: Optional[float] = Field(None, description="Tolerância do reconhecimento facial")
    enable_preprocessing: Optional[bool] = Field(None, description="Habilitar pré-processamento de imagens")

class WorkerSettings(BaseModel):
    face_processor_max_workers: Optional[int] = Field(None, description="Número de workers para processamento de faces")
    capture_max_workers: Optional[int] = Field(None, description="Número de workers para captura")
    motion_detection_max_workers: Optional[int] = Field(None, description="Número de workers para detecção de movimento")

class ComponentsSettings(BaseModel):
    enable_capture: Optional[bool] = Field(None, description="Habilitar/desabilitar captura de imagens")
    enable_processing: Optional[bool] = Field(None, description="Habilitar/desabilitar processamento de faces")

# Variáveis globais para armazenar configurações atuais
current_settings = {
    "motion": {
        "threshold": MOTION_THRESHOLD,
        "min_area": MOTION_MIN_AREA,
        "draw_contours": MOTION_DRAW_CONTOURS,
        "capture_frames": MOTION_CAPTURE_FRAMES,
        "capture_interval": MOTION_CAPTURE_INTERVAL
    },
    "processing": {
        "face_recognition_tolerance": FACE_RECOGNITION_TOLERANCE,
        "enable_preprocessing": ENABLE_PREPROCESSING
    },
    "workers": {
        "face_processor_max_workers": FACE_PROCESSOR_MAX_WORKERS,
        "capture_max_workers": CAPTURE_MAX_WORKERS,
        "motion_detection_max_workers": MOTION_DETECTION_MAX_WORKERS
    },
    "components": {
        "enable_capture": ENABLE_CAPTURE,
        "enable_processing": ENABLE_PROCESSING
    }
}

@router.get("/settings", include_in_schema=True)
@router.get("/settings/", include_in_schema=True)
def get_all_settings():
    """Retorna todas as configurações atuais"""
    return current_settings

@router.get("/settings/motion", include_in_schema=True)
@router.get("/settings/motion/", include_in_schema=True)
def get_motion_settings():
    """Retorna configurações de detecção de movimento"""
    return current_settings["motion"]

@router.post("/settings/motion", include_in_schema=True)
@router.post("/settings/motion/", include_in_schema=True)
def update_motion_settings(settings: MotionSettings):
    """Atualiza configurações de detecção de movimento"""
    try:
        # Obter instância atual do MotionCapture
        image_capture = get_image_capture()
        if not image_capture or not hasattr(image_capture, 'motion_detector'):
            raise HTTPException(status_code=400, detail="Sistema de captura não inicializado ou não suporta detecção de movimento")
        
        # Atualizar configurações
        updated = {}
        
        if settings.threshold is not None:
            image_capture.motion_threshold = settings.threshold
            image_capture.motion_detector.threshold = settings.threshold
            current_settings["motion"]["threshold"] = settings.threshold
            updated["threshold"] = settings.threshold
            
        if settings.min_area is not None:
            image_capture.motion_min_area = settings.min_area
            image_capture.motion_detector.area_minima = settings.min_area
            current_settings["motion"]["min_area"] = settings.min_area
            updated["min_area"] = settings.min_area
            
        if settings.draw_contours is not None:
            image_capture.motion_draw_contours = settings.draw_contours
            image_capture.motion_detector.desenhar_contornos = settings.draw_contours
            current_settings["motion"]["draw_contours"] = settings.draw_contours
            updated["draw_contours"] = settings.draw_contours
            
        if settings.capture_frames is not None:
            image_capture.motion_capture_frames = settings.capture_frames
            current_settings["motion"]["capture_frames"] = settings.capture_frames
            updated["capture_frames"] = settings.capture_frames
            
        if settings.capture_interval is not None:
            image_capture.motion_capture_interval = settings.capture_interval
            current_settings["motion"]["capture_interval"] = settings.capture_interval
            updated["capture_interval"] = settings.capture_interval
        
        # Registrar alterações
        if updated:
            logger.info(f"Configurações de movimento atualizadas: {updated}")
            return {"message": "Configurações de movimento atualizadas com sucesso", "updated": updated}
        else:
            return {"message": "Nenhuma configuração foi alterada"}
            
    except Exception as e:
        logger.error(f"Erro ao atualizar configurações de movimento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar configurações: {str(e)}")

@router.get("/settings/processing", include_in_schema=True)
@router.get("/settings/processing/", include_in_schema=True)
def get_processing_settings():
    """Retorna configurações de processamento de imagem"""
    return current_settings["processing"]

@router.post("/settings/processing", include_in_schema=True)
@router.post("/settings/processing/", include_in_schema=True)
def update_processing_settings(settings: ProcessingSettings):
    """Atualiza configurações de processamento de imagem"""
    try:
        # Obter instância atual do FaceProcessor
        face_processor = get_face_processor()
        if not face_processor:
            raise HTTPException(status_code=400, detail="Processador de faces não inicializado")
        
        # Atualizar configurações
        updated = {}
        
        if settings.face_recognition_tolerance is not None:
            # Atualizar variável global
            global FACE_RECOGNITION_TOLERANCE
            FACE_RECOGNITION_TOLERANCE = settings.face_recognition_tolerance
            
            # Atualizar configuração no processador
            if hasattr(face_processor, 'recognition_tolerance'):
                face_processor.recognition_tolerance = settings.face_recognition_tolerance
                
            current_settings["processing"]["face_recognition_tolerance"] = settings.face_recognition_tolerance
            updated["face_recognition_tolerance"] = settings.face_recognition_tolerance
            
        if settings.enable_preprocessing is not None:
            # Atualizar variável global
            global ENABLE_PREPROCESSING
            ENABLE_PREPROCESSING = settings.enable_preprocessing
            
            current_settings["processing"]["enable_preprocessing"] = settings.enable_preprocessing
            updated["enable_preprocessing"] = settings.enable_preprocessing
        
        # Registrar alterações
        if updated:
            logger.info(f"Configurações de processamento atualizadas: {updated}")
            return {"message": "Configurações de processamento atualizadas com sucesso", "updated": updated}
        else:
            return {"message": "Nenhuma configuração foi alterada"}
            
    except Exception as e:
        logger.error(f"Erro ao atualizar configurações de processamento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar configurações: {str(e)}")

@router.get("/settings/workers", include_in_schema=True)
@router.get("/settings/workers/", include_in_schema=True)
def get_worker_settings():
    """Retorna configurações de workers"""
    return current_settings["workers"]

@router.post("/settings/workers", include_in_schema=True)
@router.post("/settings/workers/", include_in_schema=True)
def update_worker_settings(settings: WorkerSettings):
    """Atualiza configurações de workers"""
    try:
        # Atualizar configurações
        updated = {}
        
        # Nota: Alterações nos workers não afetam pools já criados,
        # mas serão aplicadas em novos pools criados após a alteração
        
        if settings.face_processor_max_workers is not None:
            # Atualizar variável global
            global FACE_PROCESSOR_MAX_WORKERS
            FACE_PROCESSOR_MAX_WORKERS = settings.face_processor_max_workers
            current_settings["workers"]["face_processor_max_workers"] = settings.face_processor_max_workers
            updated["face_processor_max_workers"] = settings.face_processor_max_workers
            
        if settings.capture_max_workers is not None:
            # Atualizar variável global
            global CAPTURE_MAX_WORKERS
            CAPTURE_MAX_WORKERS = settings.capture_max_workers
            current_settings["workers"]["capture_max_workers"] = settings.capture_max_workers
            updated["capture_max_workers"] = settings.capture_max_workers
            
        if settings.motion_detection_max_workers is not None:
            # Atualizar variável global
            global MOTION_DETECTION_MAX_WORKERS
            MOTION_DETECTION_MAX_WORKERS = settings.motion_detection_max_workers
            current_settings["workers"]["motion_detection_max_workers"] = settings.motion_detection_max_workers
            updated["motion_detection_max_workers"] = settings.motion_detection_max_workers
        
        # Registrar alterações
        if updated:
            logger.info(f"Configurações de workers atualizadas: {updated}")
            return {
                "message": "Configurações de workers atualizadas com sucesso. Nota: Alterações serão aplicadas apenas em novos pools de workers.",
                "updated": updated
            }
        else:
            return {"message": "Nenhuma configuração foi alterada"}
            
    except Exception as e:
        logger.error(f"Erro ao atualizar configurações de workers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar configurações: {str(e)}")

@router.get("/settings/components", include_in_schema=True)
@router.get("/settings/components/", include_in_schema=True)
def get_components_settings():
    """Retorna configurações de componentes do sistema"""
    return current_settings["components"]

@router.post("/settings/components", include_in_schema=True)
@router.post("/settings/components/", include_in_schema=True)
def update_components_settings(settings: ComponentsSettings):
    """Atualiza configurações de componentes do sistema"""
    try:
        # Obter instâncias
        image_capture = get_image_capture()
        face_processor = get_face_processor()
        
        if not image_capture:
            raise HTTPException(status_code=400, detail="Sistema de captura não inicializado")
            
        # Atualizar configurações
        updated = {}
        
        if settings.enable_capture is not None:
            # Atualizar variável global
            global ENABLE_CAPTURE
            ENABLE_CAPTURE = settings.enable_capture
            current_settings["components"]["enable_capture"] = settings.enable_capture
            updated["enable_capture"] = settings.enable_capture
            
            # Iniciar ou parar captura
            if settings.enable_capture and not image_capture.is_capturing:
                image_capture.start_capture()
                logger.info("Captura de imagens iniciada")
            elif not settings.enable_capture and image_capture.is_capturing:
                image_capture.stop_capture()
                logger.info("Captura de imagens parada")
            
        if settings.enable_processing is not None and face_processor:
            # Atualizar variável global
            global ENABLE_PROCESSING
            ENABLE_PROCESSING = settings.enable_processing
            current_settings["components"]["enable_processing"] = settings.enable_processing
            updated["enable_processing"] = settings.enable_processing
            
            # Iniciar ou parar processamento
            if settings.enable_processing and not face_processor.is_processing:
                face_processor.start_processing()
                logger.info("Processamento de faces iniciado")
            elif not settings.enable_processing and face_processor.is_processing:
                face_processor.stop_processing()
                logger.info("Processamento de faces parado")
        
        # Registrar alterações
        if updated:
            logger.info(f"Configurações de componentes atualizadas: {updated}")
            return {"message": "Configurações de componentes atualizadas com sucesso", "updated": updated}
        else:
            return {"message": "Nenhuma configuração foi alterada"}
            
    except Exception as e:
        logger.error(f"Erro ao atualizar configurações de componentes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar configurações: {str(e)}") 