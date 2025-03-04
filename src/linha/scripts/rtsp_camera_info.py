#!/usr/bin/env python3
"""
Script para obter informações básicas de câmeras RTSP usando OpenCV e FFmpeg.
Este script é uma alternativa mais simples ao ONVIF para câmeras que não suportam
ou têm problemas com o protocolo ONVIF.

Uso:
    python rtsp_camera_info.py --url rtsp://ip:porta/caminho [--transport tcp|udp] [--timeout 10]
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('rtsp_camera_info')

try:
    import cv2
    import numpy as np
except ImportError:
    logger.error("Bibliotecas necessárias não encontradas. Instalando...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "numpy"])
    import cv2
    import numpy as np

def get_ffmpeg_info(rtsp_url: str, transport: str = 'tcp', timeout: int = 10) -> Dict[str, Any]:
    """
    Obtém informações detalhadas da câmera RTSP usando FFmpeg.
    
    Args:
        rtsp_url: URL RTSP da câmera
        transport: Protocolo de transporte (tcp ou udp)
        timeout: Tempo limite em segundos
        
    Returns:
        Dicionário com informações da câmera
    """
    logger.info(f"Obtendo informações da câmera {rtsp_url} usando FFmpeg...")
    
    # Preparar comando FFmpeg
    transport_option = f"rtsp_transport={transport}"
    cmd = [
        "ffprobe",
        "-v", "error",
        "-rtsp_transport", transport,
        "-i", rtsp_url,
        "-show_entries", "stream=width,height,codec_name,codec_type,r_frame_rate,avg_frame_rate",
        "-show_entries", "format=duration,bit_rate,size",
        "-of", "json",
        "-timeout", str(timeout * 1000000)  # Timeout em microssegundos
    ]
    
    try:
        # Executar comando
        logger.info(f"Executando comando: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode != 0:
            logger.error(f"Erro ao executar FFmpeg: {result.stderr}")
            return {"error": result.stderr}
        
        # Analisar saída JSON
        try:
            info = json.loads(result.stdout)
            return {
                "ffmpeg_info": info,
                "command": " ".join(cmd),
                "timestamp": datetime.now().isoformat()
            }
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao analisar saída JSON: {e}")
            return {
                "error": f"Erro ao analisar saída JSON: {e}",
                "raw_output": result.stdout
            }
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout ao executar FFmpeg após {timeout} segundos")
        return {"error": f"Timeout após {timeout} segundos"}
    except Exception as e:
        logger.error(f"Erro ao executar FFmpeg: {e}")
        return {"error": str(e)}

def get_opencv_info(rtsp_url: str, transport: str = 'tcp', timeout: int = 10) -> Dict[str, Any]:
    """
    Obtém informações básicas da câmera RTSP usando OpenCV.
    
    Args:
        rtsp_url: URL RTSP da câmera
        transport: Protocolo de transporte (tcp ou udp)
        timeout: Tempo limite em segundos
        
    Returns:
        Dicionário com informações da câmera
    """
    logger.info(f"Obtendo informações da câmera {rtsp_url} usando OpenCV...")
    
    # Configurar opções de captura
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}|stimeout;{timeout * 1000000}"
    
    # Inicializar captura
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    # Verificar se a captura foi aberta com sucesso
    if not cap.isOpened():
        logger.error(f"Erro ao abrir câmera {rtsp_url}")
        return {"error": "Não foi possível abrir a câmera"}
    
    # Obter informações básicas
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
        "codec_str": "".join([chr((int(cap.get(cv2.CAP_PROP_FOURCC)) >> 8 * i) & 0xFF) for i in range(4)]),
        "backend": cap.getBackendName(),
        "auto_focus": cap.get(cv2.CAP_PROP_AUTOFOCUS),
        "focus": cap.get(cv2.CAP_PROP_FOCUS),
        "timestamp": datetime.now().isoformat()
    }
    
    # Capturar um frame para análise
    start_time = time.time()
    frame_captured = False
    frames_info = []
    
    # Tentar capturar alguns frames para análise
    for i in range(5):
        ret, frame = cap.read()
        if ret and frame is not None and frame.size > 0:
            frame_captured = True
            
            # Calcular informações do frame
            frame_info = {
                "index": i,
                "shape": frame.shape,
                "dtype": str(frame.dtype),
                "min_value": float(np.min(frame)),
                "max_value": float(np.max(frame)),
                "mean_value": float(np.mean(frame)),
                "std_value": float(np.std(frame)),
                "capture_time": time.time() - start_time
            }
            
            # Calcular histograma para verificar qualidade da imagem
            try:
                hist = cv2.calcHist([frame], [0], None, [256], [0, 256])
                frame_info["histogram_stats"] = {
                    "min": float(np.min(hist)),
                    "max": float(np.max(hist)),
                    "mean": float(np.mean(hist)),
                    "std": float(np.std(hist))
                }
            except Exception as e:
                logger.error(f"Erro ao calcular histograma: {e}")
            
            frames_info.append(frame_info)
            
            # Salvar o primeiro frame como imagem para referência
            if i == 0:
                try:
                    temp_dir = tempfile.gettempdir()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    image_path = os.path.join(temp_dir, f"rtsp_frame_{timestamp}.jpg")
                    cv2.imwrite(image_path, frame)
                    info["sample_frame_path"] = image_path
                    logger.info(f"Frame de amostra salvo em {image_path}")
                except Exception as e:
                    logger.error(f"Erro ao salvar frame: {e}")
    
    # Liberar recursos
    cap.release()
    
    # Adicionar informações dos frames
    info["frames_captured"] = frame_captured
    info["frames_info"] = frames_info
    
    return info

def get_camera_info(rtsp_url: str, transport: str = 'tcp', timeout: int = 10) -> Dict[str, Any]:
    """
    Obtém informações completas da câmera RTSP usando OpenCV e FFmpeg.
    
    Args:
        rtsp_url: URL RTSP da câmera
        transport: Protocolo de transporte (tcp ou udp)
        timeout: Tempo limite em segundos
        
    Returns:
        Dicionário com informações da câmera
    """
    # Obter informações usando OpenCV
    opencv_info = get_opencv_info(rtsp_url, transport, timeout)
    
    # Obter informações usando FFmpeg
    ffmpeg_info = get_ffmpeg_info(rtsp_url, transport, timeout)
    
    # Combinar informações
    camera_info = {
        "rtsp_url": rtsp_url,
        "transport": transport,
        "opencv_info": opencv_info,
        "ffmpeg_info": ffmpeg_info,
        "timestamp": datetime.now().isoformat()
    }
    
    # Extrair informações para resumo
    summary = {
        "resolution": f"{opencv_info.get('width', 'N/A')}x{opencv_info.get('height', 'N/A')}",
        "fps": opencv_info.get('fps', 'N/A'),
        "codec": opencv_info.get('codec_str', 'N/A'),
        "frames_captured": opencv_info.get('frames_captured', False)
    }
    
    # Adicionar informações de streams do FFmpeg se disponíveis
    if "ffmpeg_info" in ffmpeg_info and "streams" in ffmpeg_info["ffmpeg_info"]:
        streams = ffmpeg_info["ffmpeg_info"]["streams"]
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        
        if video_streams:
            video = video_streams[0]
            summary["ffmpeg_resolution"] = f"{video.get('width', 'N/A')}x{video.get('height', 'N/A')}"
            summary["ffmpeg_codec"] = video.get("codec_name", "N/A")
            
            # Calcular FPS a partir da fração
            fps_fraction = video.get("r_frame_rate", "N/A")
            if fps_fraction != "N/A" and "/" in fps_fraction:
                num, den = map(int, fps_fraction.split("/"))
                if den != 0:
                    summary["ffmpeg_fps"] = round(num / den, 2)
        
        summary["video_streams"] = len(video_streams)
        summary["audio_streams"] = len(audio_streams)
    
    camera_info["summary"] = summary
    
    return camera_info

def save_to_file(data: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    Salva as informações da câmera em um arquivo JSON.
    
    Args:
        data: Dados a serem salvos
        filename: Nome do arquivo (opcional)
        
    Returns:
        Caminho do arquivo salvo
    """
    if not filename:
        # Gerar nome de arquivo baseado na URL e data/hora
        rtsp_url = data.get('rtsp_url', 'unknown')
        url_part = rtsp_url.split("://")[-1].replace("/", "_").replace(":", "_")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rtsp_info_{url_part}_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Informações salvas em {filename}")
    return filename

def main():
    parser = argparse.ArgumentParser(description='Obter informações de câmeras RTSP usando OpenCV e FFmpeg')
    
    parser.add_argument('--url', required=True, help='URL RTSP da câmera (ex: rtsp://192.168.0.100:554/stream)')
    parser.add_argument('--transport', choices=['tcp', 'udp'], default='tcp', help='Protocolo de transporte (padrão: tcp)')
    parser.add_argument('--timeout', type=int, default=10, help='Tempo limite em segundos (padrão: 10)')
    parser.add_argument('--output', help='Nome do arquivo de saída (padrão: rtsp_info_<URL>_<TIMESTAMP>.json)')
    
    args = parser.parse_args()
    
    # Obter informações da câmera
    camera_info = get_camera_info(args.url, args.transport, args.timeout)
    
    # Salvar informações em arquivo
    save_to_file(camera_info, args.output)
    
    # Exibir resumo das informações
    logger.info("Resumo das informações da câmera:")
    summary = camera_info.get('summary', {})
    
    logger.info(f"URL: {args.url}")
    logger.info(f"Transporte: {args.transport}")
    logger.info(f"Resolução (OpenCV): {summary.get('resolution', 'N/A')}")
    logger.info(f"FPS (OpenCV): {summary.get('fps', 'N/A')}")
    logger.info(f"Codec (OpenCV): {summary.get('codec', 'N/A')}")
    
    if 'ffmpeg_resolution' in summary:
        logger.info(f"Resolução (FFmpeg): {summary.get('ffmpeg_resolution', 'N/A')}")
        logger.info(f"FPS (FFmpeg): {summary.get('ffmpeg_fps', 'N/A')}")
        logger.info(f"Codec (FFmpeg): {summary.get('ffmpeg_codec', 'N/A')}")
    
    logger.info(f"Streams de vídeo: {summary.get('video_streams', 'N/A')}")
    logger.info(f"Streams de áudio: {summary.get('audio_streams', 'N/A')}")
    logger.info(f"Frames capturados: {'Sim' if summary.get('frames_captured', False) else 'Não'}")
    
    # Verificar se há um frame de amostra
    sample_frame = camera_info.get('opencv_info', {}).get('sample_frame_path')
    if sample_frame:
        logger.info(f"Frame de amostra salvo em: {sample_frame}")

if __name__ == "__main__":
    main() 