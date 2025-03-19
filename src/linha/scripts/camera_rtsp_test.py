import cv2
import time
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração da câmera
CAMERA_IP = "192.168.0.130"
RTSP_PORT = 8554
USERNAME = "admin"
PASSWORD = "admin123456"

# Perfis RTSP para testar
RTSP_URLS = [
    f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:{RTSP_PORT}/profile0",  # 1920x1080 @ 16fps
    f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:{RTSP_PORT}/profile1",  # 640x360 @ 16fps
    f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:{RTSP_PORT}/profile2",  # 640x360 @ 5fps
]

def test_rtsp_url(url, save_frame=True, display_video=False, duration=5):
    """
    Testa uma URL RTSP e opcionalmente salva um frame e exibe o vídeo.
    
    Args:
        url: URL RTSP para testar
        save_frame: Se True, salva um frame do vídeo
        display_video: Se True, exibe o vídeo por 'duration' segundos
        duration: Duração em segundos para exibir o vídeo
        
    Returns:
        dict: Informações sobre o stream ou None se falhar
    """
    logger.info(f"Testando URL RTSP: {url}")
    
    # Abrir o stream
    cap = cv2.VideoCapture(url)
    time.sleep(2)  # Dar tempo para conectar
    
    if not cap.isOpened():
        logger.error(f"❌ Falha ao abrir stream: {url}")
        cap.release()
        return None
    
    # Ler um frame
    ret, frame = cap.read()
    if not ret or frame is None:
        logger.error(f"❌ Stream aberto mas não conseguiu ler frame: {url}")
        cap.release()
        return None
    
    # Obter informações do stream
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    logger.info(f"✅ Stream funcionando: {url} ({width}x{height} @ {fps}fps)")
    
    # Salvar um frame
    if save_frame:
        # Criar nome de arquivo baseado na URL
        profile_name = url.split('/')[-1]
        filename = f"camera_frame_{profile_name}.jpg"
        cv2.imwrite(filename, frame)
        logger.info(f"Frame salvo em {filename}")
    
    # Exibir o vídeo
    if display_video:
        logger.info(f"Exibindo vídeo por {duration} segundos. Pressione 'q' para sair.")
        window_name = f"Stream - {url.split('/')[-1]}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        start_time = time.time()
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Adicionar informações ao frame
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Resolução: {width}x{height}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyWindow(window_name)
    
    # Fechar o stream
    cap.release()
    
    return {
        "url": url,
        "resolution": f"{width}x{height}",
        "fps": fps
    }

def main():
    """Testa todas as URLs RTSP conhecidas."""
    logger.info("=== Iniciando teste de perfis RTSP ===")
    
    working_urls = []
    
    for url in RTSP_URLS:
        result = test_rtsp_url(url, save_frame=True, display_video=True, duration=5)
        if result:
            working_urls.append(result)
    
    # Resumo
    logger.info("\n=== Resumo dos testes ===")
    if working_urls:
        logger.info(f"Total de URLs funcionando: {len(working_urls)}")
        for i, info in enumerate(working_urls):
            logger.info(f"{i+1}. {info['url']} ({info['resolution']} @ {info['fps']}fps)")
    else:
        logger.error("Nenhuma URL RTSP funcionou!")

if __name__ == "__main__":
    main() 