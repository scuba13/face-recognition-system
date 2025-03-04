#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar a captura de vídeo assíncrona.
Este script usa a classe AsyncVideoCapture para capturar frames de uma câmera RTSP
e verificar se estão sendo capturados corretamente, sem duplicação ou corrupção.
"""

import os
import sys
import time
import argparse
import cv2
import numpy as np
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from linha.utils.async_camera import AsyncVideoCapture

def parse_args():
    parser = argparse.ArgumentParser(description='Teste de captura de vídeo assíncrona')
    parser.add_argument('--url', type=str, default='rtsp://192.168.0.141:554/0/av0',
                        help='URL da câmera RTSP')
    parser.add_argument('--buffer', type=int, default=3,
                        help='Tamanho do buffer de frames')
    parser.add_argument('--frames', type=int, default=10,
                        help='Número de frames para capturar')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Intervalo entre capturas (segundos)')
    parser.add_argument('--output-dir', type=str, default='async_test_frames',
                        help='Diretório para salvar os frames')
    parser.add_argument('--public', action='store_true',
                        help='Usar stream RTSP público para teste')
    parser.add_argument('--resize', type=int, default=None,
                        help='Redimensionar frames para esta largura')
    return parser.parse_args()

def create_output_dir(output_dir):
    """Cria o diretório de saída se não existir"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

def save_frame_with_info(frame, output_dir, index, timestamp, hash_value):
    """Salva um frame com informações sobre qualidade"""
    # Adicionar informações ao frame
    height, width = frame.shape[:2]
    info_text = [
        f"Frame #{index} - {timestamp}",
        f"Hash: {hash_value}",
        f"Size: {width}x{height}"
    ]
    
    # Criar uma cópia do frame para não modificar o original
    frame_with_info = frame.copy()
    
    # Adicionar texto com informações
    y_pos = 30
    for text in info_text:
        cv2.putText(
            frame_with_info, 
            text, 
            (10, y_pos), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.7, 
            (0, 255, 0), 
            2
        )
        y_pos += 30
    
    # Salvar frame com informações
    filename = f"frame_{index:03d}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, frame_with_info)
    
    print(f"Frame {index} salvo: {filename}")
    return filepath

def calculate_frame_hash(frame):
    """Calcula um hash simples do frame"""
    return hash(frame.tobytes())

def main():
    args = parse_args()
    
    # Usar stream público se solicitado
    if args.public:
        # URL de um stream RTSP público para teste
        args.url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
        print(f"Usando stream RTSP público: {args.url}")
    
    print(f"Conectando à câmera RTSP: {args.url}")
    print(f"Tamanho do buffer: {args.buffer}")
    
    # Criar diretório de saída
    output_dir = create_output_dir(args.output_dir)
    print(f"Frames serão salvos em: {output_dir}")
    
    # Inicializar captura assíncrona
    cap = AsyncVideoCapture(args.url, buffer_size=args.buffer, resize_width=args.resize)
    
    if not cap.start():
        print("Erro ao iniciar captura assíncrona")
        return 1
    
    print("Captura assíncrona iniciada com sucesso")
    print(f"Capturando {args.frames} frames com intervalo de {args.interval} segundos")
    
    # Aguardar um pouco para a thread de captura iniciar e preencher o buffer
    print("Aguardando 3 segundos para inicialização...")
    time.sleep(3)
    
    # Estatísticas
    frames_info = []
    hashes = set()
    
    try:
        # Capturar frames
        for i in range(1, args.frames + 1):
            print(f"\nCapturando frame {i}/{args.frames}...")
            
            # Capturar frame
            ret, frame = cap.read()
            
            if not ret or frame is None or frame.size == 0:
                print(f"Erro ao capturar frame {i}")
                continue
            
            # Obter informações do frame
            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
            frame_hash = calculate_frame_hash(frame)
            
            # Verificar se é duplicado
            is_duplicate = frame_hash in hashes
            if not is_duplicate:
                hashes.add(frame_hash)
            
            # Salvar frame
            filepath = save_frame_with_info(frame, output_dir, i, timestamp, frame_hash)
            
            # Armazenar informações
            frames_info.append({
                'index': i,
                'hash': frame_hash,
                'filepath': filepath,
                'duplicate': is_duplicate
            })
            
            # Mostrar estatísticas
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
        # Parar captura
        cap.stop()
    
    # Relatório final
    print("\n" + "="*50)
    print("RELATÓRIO DE CAPTURA ASSÍNCRONA")
    print("="*50)
    print(f"Total de frames capturados: {len(frames_info)}")
    
    # Verificar frames duplicados
    duplicates = sum(1 for f in frames_info if f['duplicate'])
    print(f"Frames duplicados: {duplicates} ({duplicates/len(frames_info)*100:.1f}% se > 0)")
    
    print("\nFrames capturados:")
    for frame in frames_info:
        status = "DUPLICADO" if frame['duplicate'] else "OK"
        print(f"  Frame #{frame['index']}: {status} - {os.path.basename(frame['filepath'])}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 