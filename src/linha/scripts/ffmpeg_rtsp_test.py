#!/usr/bin/env python3
"""
Script para testar captura de frames RTSP usando FFmpeg diretamente.
Isso pode contornar problemas com o OpenCV.
"""
import os
import sys
import time
import subprocess
import shutil
from datetime import datetime

# URL da câmera RTSP
RTSP_URL = "rtsp://192.168.0.141:554/0/av0"

# Diretório para salvar os frames
OUTPUT_DIR = "ffmpeg_frames"

def check_ffmpeg():
    """Verifica se o FFmpeg está instalado"""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def capture_frame(frame_number):
    """Captura um frame usando FFmpeg"""
    print(f"\nCapturando frame {frame_number}...")
    
    # Criar diretório de saída se não existir
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Nome do arquivo de saída
    timestamp = datetime.now().strftime("%H-%M-%S-%f")[:-3]
    output_file = os.path.join(OUTPUT_DIR, f"frame_{frame_number}_{timestamp}.jpg")
    
    # Comando FFmpeg para capturar um único frame
    # -y: sobrescrever arquivo de saída
    # -rtsp_transport tcp: usar TCP para RTSP
    # -i: URL de entrada
    # -frames:v 1: capturar apenas um frame
    # -q:v 1: qualidade máxima
    cmd = [
        "ffmpeg",
        "-y",
        "-rtsp_transport", "tcp",
        "-i", RTSP_URL,
        "-frames:v", "1",
        "-q:v", "1",
        output_file
    ]
    
    try:
        # Executar comando
        print(f"Executando: {' '.join(cmd)}")
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Verificar resultado
        if process.returncode == 0 and os.path.exists(output_file):
            print(f"Frame {frame_number} capturado com sucesso!")
            print(f"Salvo em: {output_file}")
            return output_file
        else:
            print(f"ERRO ao capturar frame {frame_number}:")
            print(process.stderr)
            return None
    except Exception as e:
        print(f"ERRO: {str(e)}")
        return None

def main():
    """Função principal"""
    print("=== Teste de Captura RTSP com FFmpeg ===")
    
    # Verificar se FFmpeg está instalado
    if not check_ffmpeg():
        print("ERRO: FFmpeg não encontrado. Por favor, instale o FFmpeg.")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        return
    
    # Capturar primeiro frame
    print("\n=== PRIMEIRO FRAME ===")
    frame1 = capture_frame(1)
    
    if not frame1:
        print("ERRO: Não foi possível capturar o primeiro frame")
        return
    
    # Aguardar para o usuário se mover
    print("\nAGUARDANDO 10 SEGUNDOS - MOVA-SE NA FRENTE DA CÂMERA!")
    for i in range(10, 0, -1):
        print(f"Capturando próximo frame em {i} segundos...")
        time.sleep(1)
    
    # Capturar segundo frame
    print("\n=== SEGUNDO FRAME ===")
    frame2 = capture_frame(2)
    
    if not frame2:
        print("ERRO: Não foi possível capturar o segundo frame")
        return
    
    print("\n=== COMPARAÇÃO ===")
    print(f"Frame 1: {frame1}")
    print(f"Frame 2: {frame2}")
    
    # Comparar tamanhos dos arquivos como verificação básica
    size1 = os.path.getsize(frame1)
    size2 = os.path.getsize(frame2)
    
    print(f"Tamanho do Frame 1: {size1} bytes")
    print(f"Tamanho do Frame 2: {size2} bytes")
    print(f"Diferença de tamanho: {abs(size1 - size2)} bytes")
    
    if abs(size1 - size2) < 100:
        print("AVISO: Os frames têm tamanhos muito similares, podem ser quase idênticos.")
    else:
        print("Os frames têm tamanhos diferentes, provavelmente são distintos.")
    
    print(f"\nImagens salvas no diretório: {os.path.abspath(OUTPUT_DIR)}")
    print("Verifique visualmente as imagens para confirmar se são diferentes.")

if __name__ == "__main__":
    main() 