#!/usr/bin/env python3
"""
Script de diagnóstico para câmera RTSP.
Captura apenas dois frames com um intervalo grande entre eles.
"""
import cv2
import time
import os
import sys
import numpy as np
from datetime import datetime
import hashlib

# Adicionar diretório raiz ao path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# URL da câmera RTSP
RTSP_URL = "rtsp://192.168.0.141:554/0/av0"

# Diretório para salvar os frames
OUTPUT_DIR = "debug_frames"

def capture_frame(cap, frame_number):
    """Captura um frame e retorna informações detalhadas"""
    print(f"\nCapturando frame {frame_number}...")
    
    # Descartar frames em buffer
    for _ in range(5):
        cap.grab()
    
    # Capturar frame
    ret, frame = cap.read()
    if not ret or frame is None:
        print(f"ERRO: Falha ao capturar frame {frame_number}")
        return None, None
    
    # Calcular hash do frame
    frame_hash = hashlib.md5(frame.tobytes()).hexdigest()
    
    # Adicionar informações no frame
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    text = f"Frame #{frame_number} - {timestamp}"
    
    # Adicionar texto com fundo preto para melhor visibilidade
    cv2.putText(frame, text, (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 6)
    cv2.putText(frame, text, (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    # Adicionar hash do frame
    hash_text = f"Hash: {frame_hash[:16]}..."
    cv2.putText(frame, hash_text, (20, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
    cv2.putText(frame, hash_text, (20, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    # Salvar frame
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"debug_frame_{frame_number}_{timestamp.replace(':', '-')}.jpg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    cv2.imwrite(filepath, frame)
    
    print(f"Frame {frame_number} capturado:")
    print(f"  Timestamp: {timestamp}")
    print(f"  Hash: {frame_hash}")
    print(f"  Salvo em: {filepath}")
    
    return frame, frame_hash

def main():
    """Função principal"""
    print(f"Conectando à câmera RTSP: {RTSP_URL}")
    
    # Configurar parâmetros RTSP
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    # Abrir câmera
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        print("ERRO: Não foi possível abrir a câmera RTSP")
        return
    
    try:
        # Configurar buffer pequeno
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Capturar primeiro frame
        print("\n=== PRIMEIRO FRAME ===")
        frame1, hash1 = capture_frame(cap, 1)
        
        if frame1 is None:
            print("ERRO: Não foi possível capturar o primeiro frame")
            return
        
        # Mostrar primeiro frame
        cv2.imshow("Frame 1", frame1)
        cv2.waitKey(1)
        
        # Aguardar 10 segundos para o usuário se mover
        print("\nAGUARDANDO 10 SEGUNDOS - MOVA-SE NA FRENTE DA CÂMERA!")
        for i in range(10, 0, -1):
            print(f"Capturando próximo frame em {i} segundos...")
            time.sleep(1)
        
        # Capturar segundo frame
        print("\n=== SEGUNDO FRAME ===")
        frame2, hash2 = capture_frame(cap, 2)
        
        if frame2 is None:
            print("ERRO: Não foi possível capturar o segundo frame")
            return
        
        # Mostrar segundo frame
        cv2.imshow("Frame 2", frame2)
        cv2.waitKey(0)
        
        # Comparar frames
        print("\n=== COMPARAÇÃO ===")
        if hash1 == hash2:
            print("PROBLEMA DETECTADO: Os frames são IDÊNTICOS!")
            print("Isso indica que a câmera está enviando o mesmo frame repetidamente.")
        else:
            print("Os frames são diferentes (hashes diferentes).")
            
            # Calcular diferença entre frames
            if frame1.shape == frame2.shape:
                diff = cv2.absdiff(frame1, frame2)
                gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                mean_diff = np.mean(gray_diff)
                
                print(f"Diferença média entre pixels: {mean_diff:.2f}")
                
                if mean_diff < 5.0:
                    print("AVISO: Diferença muito pequena entre os frames!")
                    print("Os frames parecem quase idênticos visualmente.")
                elif mean_diff < 15.0:
                    print("AVISO: Diferença pequena entre os frames.")
                    print("Pode ser apenas ruído ou pequenas mudanças de luz.")
                else:
                    print("Diferença significativa detectada entre os frames.")
                
                # Salvar imagem da diferença
                diff_filename = "debug_frame_diff.jpg"
                diff_filepath = os.path.join(OUTPUT_DIR, diff_filename)
                cv2.imwrite(diff_filepath, gray_diff)
                print(f"Imagem da diferença salva em: {diff_filepath}")
                
                # Mostrar diferença
                cv2.imshow("Diferença", gray_diff)
                cv2.waitKey(0)
            
        print(f"\nImagens salvas no diretório: {os.path.abspath(OUTPUT_DIR)}")
        
    except Exception as e:
        print(f"ERRO: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 