import cv2
import time
import logging
import argparse

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração padrão da câmera
DEFAULT_CAMERA_IP = "192.168.0.130"
DEFAULT_RTSP_PORT = 8554
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123456"

# URLs RTSP conhecidas
RTSP_PROFILES = {
    "profile0": {"description": "Alta resolução (1920x1080 @ 16fps)"},
    "profile1": {"description": "Média resolução (640x360 @ 16fps)"},
    "profile2": {"description": "Baixa resolução (640x360 @ 5fps)"}
}

class RTSPViewer:
    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.cap = None
        self.current_profile = "profile1"  # Perfil padrão que sabemos que funciona
    
    def get_rtsp_url(self, profile):
        """Retorna a URL RTSP para o perfil especificado."""
        return f"rtsp://{self.username}:{self.password}@{self.ip}:{self.port}/{profile}"
    
    def start_stream(self, profile=None):
        """Inicia o stream de vídeo para o perfil especificado."""
        if profile:
            self.current_profile = profile
        
        url = self.get_rtsp_url(self.current_profile)
        logger.info(f"Iniciando stream: {url}")
        
        # Fechar stream anterior se existir
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        
        # Abrir novo stream
        self.cap = cv2.VideoCapture(url)
        time.sleep(2)  # Dar tempo para conectar
        
        if not self.cap.isOpened():
            logger.error(f"Falha ao abrir stream: {url}")
            return False
        
        logger.info("Stream iniciado com sucesso")
        return True
    
    def save_frame(self, filename=None):
        """Salva um frame do stream atual."""
        if self.cap is None or not self.cap.isOpened():
            logger.error("Stream não está aberto")
            return False
        
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Falha ao ler frame")
            return False
        
        if filename is None:
            filename = f"camera_frame_{self.ip.replace('.', '_')}_{self.current_profile}.jpg"
        
        cv2.imwrite(filename, frame)
        logger.info(f"Frame salvo como {filename}")
        return True
    
    def run(self):
        """Executa o visualizador RTSP."""
        if not self.start_stream():
            logger.error("Falha ao iniciar stream. Encerrando.")
            return
        
        window_name = "RTSP Viewer - ESC para sair | 0-2: Mudar perfil | S: Salvar frame"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        print("\n=== VISUALIZADOR RTSP ===")
        print("Comandos de teclado:")
        print("  0: Alternar para profile0 (Alta resolução)")
        print("  1: Alternar para profile1 (Média resolução)")
        print("  2: Alternar para profile2 (Baixa resolução)")
        print("  S: Salvar frame atual")
        print("  ESC: Sair")
        
        running = True
        while running:
            # Ler frame
            ret, frame = self.cap.read()
            
            if ret:
                # Adicionar informações ao frame
                height, width = frame.shape[:2]
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Perfil: {self.current_profile} ({width}x{height})", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Adicionar instruções na tela
                cv2.putText(frame, "0-2: Mudar perfil, S: Salvar frame, ESC: Sair", (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Exibir frame
                cv2.imshow(window_name, frame)
            
            # Processar teclas - esperar 30ms por uma tecla
            key = cv2.waitKey(30) & 0xFF
            
            # Verificar teclas pressionadas
            if key == 27:  # ESC
                running = False
                logger.info("Saindo do programa")
            elif key == ord('0'):
                logger.info("Alternando para profile0 (Alta resolução)")
                self.start_stream("profile0")
            elif key == ord('1'):
                logger.info("Alternando para profile1 (Média resolução)")
                self.start_stream("profile1")
            elif key == ord('2'):
                logger.info("Alternando para profile2 (Baixa resolução)")
                self.start_stream("profile2")
            elif key == ord('s') or key == ord('S'):
                logger.info("Salvando frame atual")
                self.save_frame()
        
        # Limpar
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Visualizador RTSP para câmera IP')
    parser.add_argument('--ip', default=DEFAULT_CAMERA_IP, help='Endereço IP da câmera')
    parser.add_argument('--port', type=int, default=DEFAULT_RTSP_PORT, help='Porta RTSP')
    parser.add_argument('--username', default=DEFAULT_USERNAME, help='Nome de usuário')
    parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Senha')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Criar visualizador
    viewer = RTSPViewer(args.ip, args.port, args.username, args.password)
    
    # Executar visualizador
    viewer.run()

if __name__ == "__main__":
    main() 