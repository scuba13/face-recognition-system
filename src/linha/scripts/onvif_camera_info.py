#!/usr/bin/env python3
"""
Script para obter informações básicas de câmeras IP usando o protocolo ONVIF.

Uso:
    python onvif_camera_info.py --ip 192.168.0.141 [--port 80] [--user admin] [--password admin]

Saída:
    As informações são exibidas no console e salvas em um arquivo JSON.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('onvif_camera_info')

# Verificar dependências
try:
    from onvif import ONVIFCamera
except ImportError:
    logger.error("Biblioteca onvif-zeep não encontrada. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "onvif-zeep"])
    from onvif import ONVIFCamera

def get_onvif_info(ip, port=80, username='admin', password='admin'):
    """
    Obtém informações básicas de uma câmera ONVIF.
    
    Args:
        ip: Endereço IP da câmera
        port: Porta da câmera
        username: Nome de usuário
        password: Senha
        
    Returns:
        Dicionário com informações da câmera
    """
    try:
        # Criar a conexão com a câmera
        cam = ONVIFCamera(ip, port, username, password)
        
        # Criar os serviços necessários
        device_service = cam.create_devicemgmt_service()
        media_service = cam.create_media_service()
        
        # Obter informações básicas do dispositivo
        device_info = device_service.GetDeviceInformation()
        
        # Obter perfis de vídeo
        profiles = media_service.GetProfiles()
        streams = []
        resolutions = []
        
        for profile in profiles:
            # URL do stream
            stream_setup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }
            stream_uri = media_service.GetStreamUri(stream_setup, profile.token)
            
            # Configurações de vídeo
            video_config = None
            for config in profile.Configurations:
                if hasattr(config, 'VideoEncoder'):
                    video_config = config.VideoEncoder
                    break
            
            # Nome do perfil
            profile_name = profile.Name
            
            # Adicionar informações do stream
            streams.append({
                'name': profile_name,
                'stream_url': stream_uri.Uri
            })
            
            # Adicionar informações de resolução
            if video_config and hasattr(video_config, 'Resolution'):
                resolutions.append({
                    'name': profile_name,
                    'width': video_config.Resolution.Width,
                    'height': video_config.Resolution.Height
                })
        
        # Compilar todas as informações
        camera_info = {
            'device_info': {
                'manufacturer': device_info.Manufacturer,
                'model': device_info.Model,
                'firmware_version': device_info.FirmwareVersion,
                'serial_number': device_info.SerialNumber,
                'hardware_id': getattr(device_info, 'HardwareId', 'N/A')
            },
            'streams': streams,
            'resolutions': resolutions
        }
        
        return camera_info
    
    except Exception as e:
        logger.error(f"Erro ao obter informações da câmera: {e}")
        
        # Tentar obter informações básicas via RTSP
        try:
            import subprocess
            import re
            
            # Tentar diferentes caminhos RTSP comuns
            rtsp_paths = [
                f"rtsp://{ip}:{port}/stream",
                f"rtsp://{ip}:{port}/0/av0",
                f"rtsp://{ip}:{port}/0/av1",
                f"rtsp://{ip}:{port}/live",
                f"rtsp://{ip}:{port}/ch01/01",
                f"rtsp://{ip}:{port}/cam/realmonitor",
                f"rtsp://{ip}:{port}/h264Preview_01_main",
                f"rtsp://{ip}:{port}/video1",
                f"rtsp://{ip}:{port}/media/video1",
                f"rtsp://{ip}:{port}/Streaming/Channels/1"
            ]
            
            # Adicionar versões com credenciais
            if username and password:
                auth_paths = []
                for path in rtsp_paths:
                    # Inserir credenciais na URL
                    auth_path = path.replace(f"rtsp://{ip}:", f"rtsp://{username}:{password}@{ip}:")
                    auth_paths.append(auth_path)
                rtsp_paths.extend(auth_paths)
            
            # Testar caminhos RTSP
            working_streams = []
            for rtsp_url in rtsp_paths:
                try:
                    # Usar ffprobe para verificar o stream
                    cmd = [
                        "ffprobe",
                        "-v", "error",
                        "-rtsp_transport", "tcp",
                        "-i", rtsp_url,
                        "-show_entries", "stream=width,height,codec_name",
                        "-of", "json",
                        "-timeout", "3000000"  # 3 segundos
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        # Extrair informações
                        try:
                            info = json.loads(result.stdout)
                            streams = info.get("streams", [])
                            
                            if streams:
                                # Extrair nome do stream do caminho
                                path_parts = rtsp_url.split('/')
                                stream_name = path_parts[-1] if path_parts[-1] else path_parts[-2]
                                
                                # Adicionar à lista de streams funcionando
                                working_streams.append({
                                    "url": rtsp_url,
                                    "name": stream_name,
                                    "width": streams[0].get("width"),
                                    "height": streams[0].get("height"),
                                    "codec": streams[0].get("codec_name")
                                })
                        except json.JSONDecodeError:
                            pass
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass
            
            # Criar informações básicas da câmera
            if working_streams:
                streams = []
                resolutions = []
                
                for stream in working_streams:
                    streams.append({
                        "name": stream["name"],
                        "stream_url": stream["url"]
                    })
                    
                    if stream.get("width") and stream.get("height"):
                        resolutions.append({
                            "name": stream["name"],
                            "width": stream["width"],
                            "height": stream["height"]
                        })
                
                return {
                    "device_info": {
                        "manufacturer": "Unknown",
                        "model": "Unknown",
                        "firmware_version": "Unknown",
                        "serial_number": "Unknown",
                        "hardware_id": "Unknown"
                    },
                    "streams": streams,
                    "resolutions": resolutions,
                    "note": "Informações obtidas via RTSP, não ONVIF"
                }
        
        except Exception as rtsp_error:
            logger.error(f"Erro ao obter informações via RTSP: {rtsp_error}")
        
        # Se tudo falhar, retornar erro
        return {
            "error": str(e),
            "ip": ip,
            "port": port
        }

def save_to_file(data, filename=None):
    """
    Salva as informações da câmera em um arquivo JSON.
    
    Args:
        data: Dados a serem salvos
        filename: Nome do arquivo (opcional)
        
    Returns:
        Caminho do arquivo salvo
    """
    if not filename:
        # Gerar nome de arquivo baseado no IP e data/hora
        ip = data.get("ip", "unknown")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"camera_info_{ip}_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        logger.info(f"Informações da câmera salvas em {filename}")
        return filename
    except Exception as e:
        logger.error(f"Erro ao salvar informações em arquivo: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Obter informações básicas de câmeras IP usando ONVIF')
    
    parser.add_argument('--ip', required=True, help='Endereço IP da câmera')
    parser.add_argument('--port', type=int, default=80, help='Porta da câmera (padrão: 80)')
    parser.add_argument('--user', default='admin', help='Nome de usuário (padrão: admin)')
    parser.add_argument('--password', default='admin', help='Senha (padrão: admin)')
    parser.add_argument('--output', help='Nome do arquivo de saída (opcional)')
    
    args = parser.parse_args()
    
    # Obter informações da câmera
    camera_info = get_onvif_info(args.ip, args.port, args.user, args.password)
    
    # Adicionar IP para referência
    camera_info["ip"] = args.ip
    
    # Salvar em arquivo
    output_file = args.output
    if not output_file:
        # Gerar nome de arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"camera_info_{args.ip}_{timestamp}.json"
    
    save_to_file(camera_info, output_file)
    
    # Imprimir informações no console
    print(json.dumps(camera_info, indent=4))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
