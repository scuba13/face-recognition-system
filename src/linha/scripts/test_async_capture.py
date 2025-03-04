#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar a captura de frames usando a nova implementação com AsyncVideoCapture.
Este script configura uma câmera RTSP e captura frames em intervalos regulares.
"""

import os
import sys
import time
import argparse
import cv2
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Adicionar diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from linha.utils.camera import setup_camera
from linha.utils.async_camera import AsyncVideoCapture

def parse_args():
    parser = argparse.ArgumentParser(description='Teste de captura de frames com AsyncVideoCapture')
    parser.add_argument('--url', type=str, default='rtsp://192.168.0.141:554/0/av0',
                        help='URL da câmera RTSP')
    parser.add_argument('--transport', type=str, default='tcp', choices=['tcp', 'udp'],
                        help='Protocolo de transporte RTSP (tcp ou udp)')
    parser.add_argument('--frames', type=int, default=10,
                        help='Número de frames para capturar')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Intervalo entre capturas (segundos)')
    parser.add_argument('--output-dir', type=str, default='async_capture_test',
                        help='Diretório para salvar os frames')
    parser.add_argument('--public', action='store_true',
                        help='Usar stream RTSP público para teste')
    parser.add_argument('--direct', action='store_true',
                        help='Usar AsyncVideoCapture diretamente em vez de setup_camera')
    return parser.parse_args()

def create_output_dir(output_dir):
    """Cria o diretório de saída se não existir"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

def save_frame(frame, output_dir, index):
    """Salva um frame com timestamp"""
    timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
    filename = f"frame_{index:03d}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, frame)
    print(f"Frame {index} salvo: {filename}")
    return filepath

def main():
    args = parse_args()
    
    # Usar stream público se solicitado
    if args.public:
        # URL de um stream RTSP público para teste
        args.url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
        print(f"Usando stream RTSP público: {args.url}")
    
    print(f"Conectando à câmera RTSP: {args.url}")
    print(f"Protocolo de transporte: {args.transport}")
    
    # Criar diretório de saída
    output_dir = create_output_dir(args.output_dir)
    print(f"Frames serão salvos em: {output_dir}")
    
    # Configurar câmera
    if args.direct:
        print("Usando AsyncVideoCapture diretamente")
        cap = AsyncVideoCapture(args.url, buffer_size=3)
        if not cap.start():
            print("Erro ao iniciar captura assíncrona")
            return 1
    else:
        print("Usando setup_camera")
        camera_config = {
            'type': 'ip',
            'url': args.url,
            'rtsp_transport': args.transport
        }
        cap = setup_camera(camera_config)
        
        # Verificar se a câmera foi aberta
        if not cap:
            print("Erro ao abrir a câmera RTSP")
            return 1
        
        # Verificar se é uma câmera assíncrona
        is_async = hasattr(cap, 'read') and hasattr(cap, 'stop') and hasattr(cap, 'get_fps')
        print(f"Câmera assíncrona: {'Sim' if is_async else 'Não'}")
    
    print("Câmera aberta com sucesso")
    print(f"Capturando {args.frames} frames com intervalo de {args.interval} segundos")
    
    # Aguardar um pouco para a câmera inicializar
    print("Aguardando 3 segundos para inicialização...")
    time.sleep(3)
    
    try:
        # Capturar frames
        for i in range(1, args.frames + 1):
            print(f"\nCapturando frame {i}/{args.frames}...")
            
            # Capturar frame
            ret, frame = cap.read()
            
            if not ret or frame is None or frame.size == 0:
                print(f"Erro ao capturar frame {i}")
                continue
            
            # Salvar frame
            save_frame(frame, output_dir, i)
            
            # Mostrar estatísticas se for câmera assíncrona
            if hasattr(cap, 'get_fps'):
                print(f"FPS atual: {cap.get_fps():.2f}")
                print(f"Frames capturados: {cap.get_frame_count()}")
                print(f"Frames descartados: {cap.get_drop_count()}")
                print(f"Tamanho da fila: {cap.get_queue_size()}")
            
            # Aguardar intervalo
            if i < args.frames:
                print(f"Aguardando {args.interval} segundos...")
                time.sleep(args.interval)
    
    except KeyboardInterrupt:
        print("\nCaptura interrompida pelo usuário")
    except Exception as e:
        print(f"Erro durante a captura: {str(e)}")
    finally:
        # Liberar câmera
        if hasattr(cap, 'stop'):
            cap.stop()
        elif hasattr(cap, 'release'):
            cap.release()
    
    print("\nTeste concluído!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 