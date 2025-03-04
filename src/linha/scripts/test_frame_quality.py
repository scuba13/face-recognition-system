#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar a qualidade dos frames capturados de uma câmera RTSP.
Este script captura múltiplos frames, verifica se há corrupção (faixas verdes),
e salva os frames para análise posterior.
"""

import os
import sys
import cv2
import time
import argparse
import numpy as np
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from linha.utils.camera import setup_camera, _check_frame_corruption

def parse_args():
    parser = argparse.ArgumentParser(description='Teste de qualidade de frames RTSP')
    parser.add_argument('--url', type=str, default='rtsp://192.168.0.141:554/0/av0',
                        help='URL da câmera RTSP')
    parser.add_argument('--transport', type=str, default='tcp', choices=['tcp', 'udp'],
                        help='Protocolo de transporte RTSP (tcp ou udp)')
    parser.add_argument('--frames', type=int, default=10,
                        help='Número de frames para capturar')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Intervalo entre capturas (segundos)')
    parser.add_argument('--output-dir', type=str, default='quality_test_frames',
                        help='Diretório para salvar os frames')
    parser.add_argument('--public', action='store_true',
                        help='Usar stream RTSP público para teste')
    return parser.parse_args()

def create_output_dir(output_dir):
    """Cria o diretório de saída se não existir"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

def save_frame_with_info(frame, output_dir, index, is_corrupted, hash_value):
    """Salva o frame com informações sobre qualidade"""
    timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
    
    # Adicionar informações ao frame
    height, width = frame.shape[:2]
    info_text = [
        f"Frame #{index} - {timestamp}",
        f"Corrupted: {is_corrupted}",
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
            (0, 0, 255) if is_corrupted else (0, 255, 0), 
            2
        )
        y_pos += 30
    
    # Salvar frame com informações
    filename = f"frame_{index:03d}_{timestamp}_{'corrupted' if is_corrupted else 'ok'}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, frame_with_info)
    
    print(f"Frame {index} salvo: {filename}")
    return filepath

def calculate_frame_hash(frame):
    """Calcula um hash simples do frame"""
    return hash(frame.tobytes())

def analyze_frame(frame, index, output_dir):
    """Analisa um frame quanto à qualidade e corrupção"""
    # Verificar se o frame está corrompido
    is_corrupted = _check_frame_corruption(frame)
    
    # Calcular hash do frame
    frame_hash = calculate_frame_hash(frame)
    
    # Salvar frame com informações
    filepath = save_frame_with_info(frame, output_dir, index, is_corrupted, frame_hash)
    
    return {
        'index': index,
        'corrupted': is_corrupted,
        'hash': frame_hash,
        'filepath': filepath
    }

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
    camera_config = {
        'type': 'ip',
        'url': args.url,
        'rtsp_transport': args.transport
    }
    cap = setup_camera(camera_config)
    
    if not cap or not cap.isOpened():
        print("Erro ao abrir a câmera RTSP")
        return 1
    
    print("Câmera aberta com sucesso")
    print(f"Capturando {args.frames} frames com intervalo de {args.interval} segundos")
    
    # Estatísticas
    frames_info = []
    corrupted_count = 0
    
    try:
        # Descartar os primeiros frames (podem estar corrompidos)
        for _ in range(5):
            cap.grab()
            time.sleep(0.1)
        
        # Capturar frames
        for i in range(1, args.frames + 1):
            print(f"\nCapturando frame {i}/{args.frames}...")
            
            # Capturar frame
            ret, frame = cap.read()
            
            if not ret or frame is None or frame.size == 0:
                print(f"Erro ao capturar frame {i}")
                continue
            
            # Analisar frame
            frame_info = analyze_frame(frame, i, output_dir)
            frames_info.append(frame_info)
            
            if frame_info['corrupted']:
                corrupted_count += 1
            
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
        cap.release()
    
    # Relatório final
    print("\n" + "="*50)
    print("RELATÓRIO DE QUALIDADE DOS FRAMES")
    print("="*50)
    print(f"Total de frames capturados: {len(frames_info)}")
    print(f"Frames corrompidos: {corrupted_count} ({corrupted_count/len(frames_info)*100:.1f}%)")
    
    # Verificar frames duplicados
    hashes = [f['hash'] for f in frames_info]
    unique_hashes = set(hashes)
    duplicates = len(hashes) - len(unique_hashes)
    print(f"Frames duplicados: {duplicates} ({duplicates/len(frames_info)*100:.1f}%)")
    
    print("\nFrames capturados:")
    for frame in frames_info:
        status = "CORROMPIDO" if frame['corrupted'] else "OK"
        print(f"  Frame #{frame['index']}: {status} - {os.path.basename(frame['filepath'])}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 