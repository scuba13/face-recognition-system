#!/usr/bin/env python3
"""
Script para testar a detecção de movimento.
Captura frames da câmera e mostra em tempo real a detecção de movimento.
"""
import cv2
import time
import argparse
import logging
import os
import sys
from datetime import datetime

# Adicionar diretório raiz ao path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from linha.utils.motion_detector import MotionDetector
from linha.utils.camera import setup_camera
from linha.utils.async_camera import AsyncVideoCapture

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_motion')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Teste de detecção de movimento')
    
    # Parâmetros da câmera
    parser.add_argument('--url', type=str, help='URL da câmera RTSP')
    parser.add_argument('--webcam', type=int, default=0, help='ID da webcam (padrão: 0)')
    parser.add_argument('--video', type=str, help='Caminho para arquivo de vídeo')
    parser.add_argument('--transport', type=str, default='tcp', choices=['tcp', 'udp'], 
                        help='Protocolo de transporte RTSP (padrão: tcp)')
    
    # Parâmetros de detecção de movimento
    parser.add_argument('--threshold', type=float, default=25.0, 
                        help='Limiar para detecção de movimento (padrão: 25.0)')
    parser.add_argument('--min-area', type=float, default=500.0, 
                        help='Área mínima para considerar movimento (padrão: 500.0)')
    parser.add_argument('--draw', action='store_true', 
                        help='Desenhar contornos de movimento')
    parser.add_argument('--save', action='store_true', 
                        help='Salvar frames com movimento detectado')
    parser.add_argument('--output-dir', type=str, default='motion_frames', 
                        help='Diretório para salvar frames (padrão: motion_frames)')
    
    return parser.parse_args()

def setup_video_source(args):
    """Configura fonte de vídeo baseada nos argumentos"""
    if args.url:
        logger.info(f"Usando câmera RTSP: {args.url}")
        config = {
            'type': 'ip',
            'url': args.url,
            'rtsp_transport': args.transport
        }
        return setup_camera(config)
    elif args.video:
        logger.info(f"Usando arquivo de vídeo: {args.video}")
        return cv2.VideoCapture(args.video)
    else:
        logger.info(f"Usando webcam ID: {args.webcam}")
        return cv2.VideoCapture(args.webcam)

def main():
    """Função principal"""
    args = parse_args()
    
    # Criar diretório de saída se necessário
    if args.save:
        os.makedirs(args.output_dir, exist_ok=True)
        logger.info(f"Frames com movimento serão salvos em: {args.output_dir}")
    
    # Inicializar detector de movimento
    motion_detector = MotionDetector(
        threshold=args.threshold,
        area_minima=args.min_area,
        desenhar_contornos=args.draw
    )
    logger.info(f"Detector de movimento inicializado: threshold={args.threshold}, min_area={args.min_area}")
    
    # Configurar fonte de vídeo
    cap = setup_video_source(args)
    
    # Verificar se a câmera foi aberta corretamente
    if isinstance(cap, AsyncVideoCapture):
        # AsyncVideoCapture não tem método isOpened(), mas já foi verificado durante o setup
        logger.info("Usando captura assíncrona")
    elif isinstance(cap, cv2.VideoCapture) and not cap.isOpened():
        logger.error("Não foi possível abrir a fonte de vídeo")
        return
    
    logger.info("Iniciando detecção de movimento. Pressione 'q' para sair.")
    
    # Variáveis para controle
    frame_anterior = None
    frame_count = 0
    motion_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Capturar frame
            ret, frame = cap.read()
            if not ret or frame is None:
                if args.video and isinstance(cap, cv2.VideoCapture):
                    logger.info("Fim do vídeo, reiniciando...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    logger.error("Erro ao capturar frame")
                    time.sleep(0.5)  # Pequena pausa antes de tentar novamente
                    continue
            
            frame_count += 1
            
            # Redimensionar para processamento mais rápido
            frame = cv2.resize(frame, (640, 480))
            
            # Detectar movimento se tiver frame anterior
            if frame_anterior is not None:
                movimento_detectado, movimento_area, frame_marcado = motion_detector.detectar(
                    frame, frame_anterior
                )
                
                # Mostrar informações no frame
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                
                info_text = f"FPS: {fps:.1f} | Frames: {frame_count} | Movimentos: {motion_count}"
                cv2.putText(frame_marcado, info_text, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                if movimento_detectado:
                    motion_count += 1
                    motion_text = f"MOVIMENTO! Area: {movimento_area:.0f}"
                    cv2.putText(frame_marcado, motion_text, (10, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Salvar frame com movimento
                    if args.save:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                        filename = f"motion_{movimento_area:.0f}_{timestamp}.jpg"
                        filepath = os.path.join(args.output_dir, filename)
                        cv2.imwrite(filepath, frame_marcado)
                        logger.info(f"Frame com movimento salvo: {filename}")
                
                # Mostrar frame
                cv2.imshow('Detecção de Movimento', frame_marcado)
            
            # Atualizar frame anterior
            frame_anterior = frame.copy()
            
            # Verificar tecla pressionada
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                logger.info("Tecla 'q' pressionada. Encerrando...")
                break
            
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
    finally:
        # Liberar recursos
        if isinstance(cap, AsyncVideoCapture):
            cap.stop()
        else:
            cap.release()
        cv2.destroyAllWindows()
        
        # Mostrar estatísticas
        elapsed = time.time() - start_time
        logger.info(f"Estatísticas:")
        logger.info(f"  Tempo total: {elapsed:.1f} segundos")
        logger.info(f"  Frames processados: {frame_count}")
        logger.info(f"  Movimentos detectados: {motion_count}")
        logger.info(f"  FPS médio: {frame_count / elapsed if elapsed > 0 else 0:.1f}")

if __name__ == "__main__":
    main() 