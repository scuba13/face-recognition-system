#!/usr/bin/env python3
"""
Script para testar conexão com câmeras RTSP.
"""
import cv2
import time
import os
import argparse
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_rtsp_connection(rtsp_url, timeout=30, transport="tcp", save_frame=True):
    """
    Testa conexão com uma câmera RTSP.
    
    Args:
        rtsp_url: URL da câmera RTSP
        timeout: Tempo máximo de espera em segundos
        transport: Protocolo de transporte (tcp ou udp)
        save_frame: Se deve salvar um frame de teste
    
    Returns:
        bool: True se a conexão foi bem-sucedida, False caso contrário
    """
    logger.info(f"Testando conexão com câmera RTSP: {rtsp_url}")
    logger.info(f"Protocolo de transporte: {transport}")
    
    # Configurar parâmetros do OpenCV para RTSP
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}"
    
    # Criar objeto de captura
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    # Configurar buffer pequeno para reduzir latência
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Verificar se a câmera foi aberta
    if not cap.isOpened():
        logger.error(f"Não foi possível abrir a câmera RTSP: {rtsp_url}")
        return False
    
    logger.info("Câmera aberta com sucesso, tentando ler frames...")
    
    # Tentar ler frames com timeout
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
            logger.info(f"Frame {frame_count} capturado com sucesso")
            
            # Salvar um frame para verificação
            if save_frame and frame_count == 1:
                os.makedirs("test_frames", exist_ok=True)
                filename = f"test_frames/rtsp_test_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
                logger.info(f"Frame salvo em: {filename}")
            
            # Se capturou pelo menos 10 frames, considerar sucesso
            if frame_count >= 10:
                logger.info(f"Teste bem-sucedido: {frame_count} frames capturados")
                cap.release()
                return True
        else:
            logger.warning("Falha ao capturar frame, tentando novamente...")
        
        # Pequena pausa para não sobrecarregar
        time.sleep(0.5)
    
    # Timeout atingido
    logger.error(f"Timeout atingido após {timeout} segundos")
    if frame_count > 0:
        logger.info(f"Foram capturados {frame_count} frames antes do timeout")
    
    cap.release()
    return frame_count > 0

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Teste de conexão com câmeras RTSP")
    parser.add_argument("--url", type=str, default="rtsp://192.168.0.133:554/0/av0",
                        help="URL da câmera RTSP")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Tempo máximo de espera em segundos")
    parser.add_argument("--transport", type=str, default="tcp", choices=["tcp", "udp"],
                        help="Protocolo de transporte (tcp ou udp)")
    parser.add_argument("--public", action="store_true",
                        help="Usar uma câmera RTSP pública para teste")
    
    args = parser.parse_args()
    
    # Usar uma câmera RTSP pública para teste
    if args.public:
        args.url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
        logger.info("Usando câmera RTSP pública para teste")
    
    # Testar conexão
    success = test_rtsp_connection(args.url, args.timeout, args.transport)
    
    if success:
        logger.info("✅ Teste concluído com sucesso")
        return 0
    else:
        logger.error("❌ Teste falhou")
        return 1

if __name__ == "__main__":
    exit(main()) 