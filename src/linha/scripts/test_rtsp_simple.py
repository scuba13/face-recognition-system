#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simples para testar a conexão com uma câmera RTSP.
Este script tenta diferentes abordagens para conectar à câmera.
"""

import cv2
import os
import sys
import time
import argparse
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description='Teste simples de conexão RTSP')
    parser.add_argument('--url', type=str, default='rtsp://192.168.0.141:554/0/av0',
                        help='URL da câmera RTSP')
    parser.add_argument('--transport', type=str, default='tcp', choices=['tcp', 'udp'],
                        help='Protocolo de transporte RTSP (tcp ou udp)')
    parser.add_argument('--save', action='store_true',
                        help='Salvar frames capturados')
    parser.add_argument('--output-dir', type=str, default='rtsp_simple_test',
                        help='Diretório para salvar os frames')
    parser.add_argument('--public', action='store_true',
                        help='Usar stream RTSP público para teste')
    return parser.parse_args()

def create_output_dir(output_dir):
    """Cria o diretório de saída se não existir"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir

def save_frame(frame, output_dir, prefix="frame"):
    """Salva um frame com timestamp"""
    timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
    filename = f"{prefix}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, frame)
    print(f"Frame salvo: {filename}")
    return filepath

def try_connect_rtsp(url, transport='tcp', method=1):
    """
    Tenta conectar à câmera RTSP usando diferentes métodos
    
    Args:
        url: URL da câmera RTSP
        transport: Protocolo de transporte (tcp ou udp)
        method: Método de conexão (1, 2, 3 ou 4)
        
    Returns:
        Objeto VideoCapture ou None se falhar
    """
    print(f"Tentando método {method} com transporte {transport}...")
    
    try:
        if method == 1:
            # Método 1: Direto
            cap = cv2.VideoCapture(url)
        
        elif method == 2:
            # Método 2: Com variável de ambiente
            if transport == 'tcp':
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            else:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            
        elif method == 3:
            # Método 3: Com parâmetro na URL
            if transport == 'tcp':
                cap = cv2.VideoCapture(f"{url}?rtsp_transport=tcp", cv2.CAP_FFMPEG)
            else:
                cap = cv2.VideoCapture(f"{url}?rtsp_transport=udp", cv2.CAP_FFMPEG)
                
        elif method == 4:
            # Método 4: Com parâmetros adicionais
            if transport == 'tcp':
                cap = cv2.VideoCapture(f"{url}?rtsp_transport=tcp&buffer_size=0", cv2.CAP_FFMPEG)
            else:
                cap = cv2.VideoCapture(f"{url}?rtsp_transport=udp&buffer_size=0", cv2.CAP_FFMPEG)
        
        # Verificar se a câmera foi aberta
        if cap.isOpened():
            print(f"Método {method} com transporte {transport}: SUCESSO")
            return cap
        else:
            print(f"Método {method} com transporte {transport}: FALHA")
            return None
            
    except Exception as e:
        print(f"Erro no método {method}: {str(e)}")
        return None

def main():
    args = parse_args()
    
    # Usar stream público se solicitado
    if args.public:
        # URL de um stream RTSP público para teste
        args.url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
        print(f"Usando stream RTSP público: {args.url}")
    
    print(f"Testando conexão com câmera RTSP: {args.url}")
    print(f"Protocolo de transporte: {args.transport}")
    
    # Criar diretório de saída se necessário
    output_dir = None
    if args.save:
        output_dir = create_output_dir(args.output_dir)
        print(f"Frames serão salvos em: {output_dir}")
    
    # Tentar diferentes métodos de conexão
    cap = None
    for method in range(1, 5):
        cap = try_connect_rtsp(args.url, args.transport, method)
        if cap is not None and cap.isOpened():
            break
    
    if cap is None or not cap.isOpened():
        print("FALHA: Não foi possível conectar à câmera RTSP com nenhum método")
        return 1
    
    print("\nConexão estabelecida com sucesso!")
    
    # Tentar capturar alguns frames
    try:
        print("\nCapturando frames de teste...")
        
        # Descartar os primeiros frames
        for _ in range(5):
            cap.grab()
            time.sleep(0.1)
        
        # Capturar e mostrar/salvar 3 frames
        for i in range(1, 4):
            print(f"\nCapturando frame {i}/3...")
            
            # Capturar frame
            ret, frame = cap.read()
            
            if not ret or frame is None or frame.size == 0:
                print(f"Erro ao capturar frame {i}")
                continue
            
            # Obter informações do frame
            height, width = frame.shape[:2]
            print(f"Frame capturado: {width}x{height}")
            
            # Salvar frame se solicitado
            if args.save and output_dir:
                save_frame(frame, output_dir, f"frame_{i}")
            
            # Aguardar um pouco
            if i < 3:
                print("Aguardando 1 segundo...")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nCaptura interrompida pelo usuário")
    except Exception as e:
        print(f"Erro durante a captura: {str(e)}")
    finally:
        # Liberar câmera
        if cap is not None:
            cap.release()
    
    print("\nTeste concluído!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 