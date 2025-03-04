#!/usr/bin/env python3
"""
Script para testar a captura de frames de uma câmera RTSP.
Captura frames em sequência e verifica se são diferentes entre si.
"""
import cv2
import time
import argparse
import logging
import os
import sys
import numpy as np
from datetime import datetime
import hashlib

# Adicionar diretório raiz ao path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from linha.utils.camera import setup_camera

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_rtsp_frames')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Teste de captura de frames RTSP')
    
    # Parâmetros da câmera
    parser.add_argument('--url', type=str, required=True, help='URL da câmera RTSP')
    parser.add_argument('--transport', type=str, default='tcp', choices=['tcp', 'udp'], 
                        help='Protocolo de transporte RTSP (padrão: tcp)')
    parser.add_argument('--interval', type=float, default=1.0, 
                        help='Intervalo entre capturas em segundos (padrão: 1.0)')
    parser.add_argument('--frames', type=int, default=10, 
                        help='Número de frames a capturar (padrão: 10)')
    parser.add_argument('--save', action='store_true', 
                        help='Salvar frames capturados')
    parser.add_argument('--output-dir', type=str, default='rtsp_frames', 
                        help='Diretório para salvar frames (padrão: rtsp_frames)')
    parser.add_argument('--discard', type=int, default=3, 
                        help='Número de frames a descartar antes de cada captura (padrão: 3)')
    
    return parser.parse_args()

def calculate_frame_hash(frame):
    """Calcula um hash MD5 do frame para comparação"""
    return hashlib.md5(frame.tobytes()).hexdigest()

def calculate_frame_diff(frame1, frame2):
    """Calcula a diferença entre dois frames"""
    if frame1.shape != frame2.shape:
        return float('inf')
    
    # Converter para escala de cinza
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Calcular diferença absoluta
    diff = cv2.absdiff(gray1, gray2)
    
    # Retornar média da diferença
    return np.mean(diff)

def main():
    """Função principal"""
    args = parse_args()
    
    # Criar diretório de saída se necessário
    if args.save:
        os.makedirs(args.output_dir, exist_ok=True)
        logger.info(f"Frames serão salvos em: {args.output_dir}")
    
    # Configurar câmera RTSP
    logger.info(f"Conectando à câmera RTSP: {args.url} (transporte: {args.transport})")
    camera_config = {
        'type': 'ip',
        'url': args.url,
        'rtsp_transport': args.transport,
        'name': 'RTSP Test Camera'
    }
    
    cap = setup_camera(camera_config)
    if not cap or not cap.isOpened():
        logger.error("Não foi possível abrir a câmera RTSP")
        return
    
    logger.info(f"Câmera conectada. Capturando {args.frames} frames com intervalo de {args.interval}s")
    
    # Variáveis para controle
    frames_capturados = []
    hashes = []
    
    try:
        for i in range(1, args.frames + 1):
            logger.info(f"Capturando frame {i}/{args.frames}...")
            
            # Descartar frames em buffer
            for j in range(args.discard):
                logger.debug(f"Descartando frame {j+1}/{args.discard}")
                cap.grab()
            
            # Capturar frame
            ret, frame = cap.read()
            if not ret or frame is None or frame.size == 0:
                logger.error(f"Erro ao capturar frame {i}")
                continue
            
            # Adicionar texto com número do frame e timestamp na imagem
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            frame_text = f"Frame #{i} - {timestamp}"
            
            # Adicionar um retângulo colorido que muda de cor a cada frame
            color = (i * 25 % 255, (i * 50) % 255, (i * 100) % 255)
            cv2.rectangle(frame, (10, 10), (200, 100), color, -1)
            
            # Adicionar texto com fundo preto para melhor visibilidade
            cv2.putText(frame, frame_text, (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 6)
            cv2.putText(frame, frame_text, (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            
            # Adicionar texto com instruções
            cv2.putText(frame, "Mova-se na frente da camera", (20, frame.shape[0] - 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
            cv2.putText(frame, "Mova-se na frente da camera", (20, frame.shape[0] - 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # Calcular hash do frame
            frame_hash = calculate_frame_hash(frame)
            
            # Verificar se é duplicado
            is_duplicate = frame_hash in hashes
            
            # Armazenar frame e hash
            frames_capturados.append(frame)
            hashes.append(frame_hash)
            
            # Calcular diferença com o frame anterior
            diff_value = 0
            if len(frames_capturados) > 1:
                diff_value = calculate_frame_diff(frames_capturados[-1], frames_capturados[-2])
            
            # Mostrar informações
            logger.info(f"Frame {i}: hash={frame_hash[:8]}... {'DUPLICADO!' if is_duplicate else 'OK'} diff={diff_value:.2f}")
            
            # Salvar frame
            if args.save:
                timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"frame_{i:03d}_{timestamp_file}.jpg"
                filepath = os.path.join(args.output_dir, filename)
                cv2.imwrite(filepath, frame)
                logger.info(f"Frame salvo: {filename}")
            
            # Mostrar frame
            cv2.imshow('RTSP Frame', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                logger.info("Tecla 'q' pressionada. Encerrando...")
                break
            
            # Aguardar intervalo
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
    finally:
        # Liberar recursos
        cap.release()
        cv2.destroyAllWindows()
        
        # Mostrar estatísticas
        total_frames = len(frames_capturados)
        duplicates = sum(1 for i in range(1, len(hashes)) if hashes[i] in hashes[:i])
        
        logger.info(f"\nEstatísticas:")
        logger.info(f"  Total de frames capturados: {total_frames}")
        logger.info(f"  Frames duplicados: {duplicates}")
        logger.info(f"  Taxa de duplicação: {duplicates/total_frames*100:.1f}% (quanto menor, melhor)")
        
        # Calcular diferenças entre frames consecutivos
        if len(frames_capturados) > 1:
            diffs = [calculate_frame_diff(frames_capturados[i], frames_capturados[i-1]) 
                    for i in range(1, len(frames_capturados))]
            avg_diff = sum(diffs) / len(diffs)
            logger.info(f"  Diferença média entre frames: {avg_diff:.2f} (quanto maior, melhor)")
            
        # Mostrar onde as imagens foram salvas
        if args.save and total_frames > 0:
            abs_path = os.path.abspath(args.output_dir)
            logger.info(f"\nImagens salvas em: {abs_path}")
            logger.info(f"Para apagar as imagens: rm -rf {abs_path}")

if __name__ == "__main__":
    main() 