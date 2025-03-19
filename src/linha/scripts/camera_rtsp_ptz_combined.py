import cv2
import time
import logging
import threading
import argparse
from onvif import ONVIFCamera

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração da câmera
CAMERA_IP = "192.168.0.130"
ONVIF_PORT = 6688  # Porta ONVIF confirmada
RTSP_PORT = 8554   # Porta RTSP confirmada
USERNAME = "admin"
PASSWORD = "admin123456"

# Perfis RTSP conhecidos
RTSP_PROFILES = [
    "profile0",  # 1920x1080 @ 16fps
    "profile1",  # 640x360 @ 16fps
    "profile2",  # 640x360 @ 5fps
]

class CameraController:
    def __init__(self, ip, onvif_port, rtsp_port, username, password):
        self.ip = ip
        self.onvif_port = onvif_port
        self.rtsp_port = rtsp_port
        self.username = username
        self.password = password
        self.cam = None
        self.ptz = None
        self.media = None
        self.profiles = []
        self.current_profile = None
        self.stream_thread = None
        self.stop_stream = False
        self.connected = False
        self.cap = None
        self.current_rtsp_url = None
        
    def connect_onvif(self):
        """Conecta à câmera via ONVIF."""
        try:
            logger.info(f"Conectando à câmera ONVIF em {self.ip}:{self.onvif_port}")
            self.cam = ONVIFCamera(self.ip, self.onvif_port, self.username, self.password)
            
            # Inicializar serviços
            self.media = self.cam.create_media_service()
            self.ptz = self.cam.create_ptz_service()
            
            # Obter perfis disponíveis
            self.profiles = self.media.GetProfiles()
            
            if self.profiles:
                self.current_profile = self.profiles[0]
                logger.info(f"Conectado com sucesso. Encontrados {len(self.profiles)} perfis.")
                
                # Exibir informações dos perfis
                for i, profile in enumerate(self.profiles):
                    if profile.VideoEncoderConfiguration:
                        res = profile.VideoEncoderConfiguration.Resolution
                        fps = profile.VideoEncoderConfiguration.RateControl.FrameRateLimit
                        logger.info(f"Perfil {i}: {profile.Name} - {res.Width}x{res.Height} @ {fps}fps")
                
                self.connected = True
                return True
            else:
                logger.error("Nenhum perfil encontrado na câmera")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao conectar via ONVIF: {str(e)}")
            return False
    
    def get_rtsp_urls(self):
        """Obtém as URLs RTSP para todos os perfis."""
        rtsp_urls = {}
        
        # URLs via ONVIF
        if self.connected and self.media:
            for profile in self.profiles:
                try:
                    stream_uri = self.media.GetStreamUri({
                        'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}},
                        'ProfileToken': profile.token
                    })
                    rtsp_urls[profile.Name] = stream_uri.Uri
                except Exception as e:
                    logger.error(f"Erro ao obter URI RTSP para {profile.Name}: {str(e)}")
        
        # URLs conhecidas
        for profile in RTSP_PROFILES:
            url = f"rtsp://{self.username}:{self.password}@{self.ip}:{self.rtsp_port}/{profile}"
            rtsp_urls[f"Manual-{profile}"] = url
            
        return rtsp_urls
    
    def test_rtsp_urls(self):
        """Testa todas as URLs RTSP conhecidas e retorna as que funcionam."""
        rtsp_urls = self.get_rtsp_urls()
        working_urls = {}
        
        logger.info(f"Testando {len(rtsp_urls)} URLs RTSP...")
        
        for name, url in rtsp_urls.items():
            logger.info(f"Testando {name}: {url}")
            cap = cv2.VideoCapture(url)
            time.sleep(2)  # Dar tempo para conectar
            
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Salvar um frame como amostra
                    filename = f"camera_frame_{name.replace('/', '_')}.jpg"
                    cv2.imwrite(filename, frame)
                    logger.info(f"✅ URL funcionando: {url}")
                    logger.info(f"Frame salvo em {filename}")
                    
                    # Obter informações do stream
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    working_urls[name] = {
                        "url": url,
                        "resolution": f"{width}x{height}",
                        "fps": fps
                    }
                else:
                    logger.warning(f"⚠️ Stream aberto mas não conseguiu ler frame: {url}")
            else:
                logger.warning(f"❌ Falha ao abrir stream: {url}")
            
            cap.release()
        
        return working_urls
    
    def start_stream(self, rtsp_url):
        """Inicia o stream de vídeo."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        
        logger.info(f"Iniciando stream: {rtsp_url}")
        self.current_rtsp_url = rtsp_url
        self.cap = cv2.VideoCapture(rtsp_url)
        time.sleep(2)  # Dar tempo para conectar
        
        if not self.cap.isOpened():
            logger.error(f"❌ Falha ao abrir stream: {rtsp_url}")
            return False
        
        ret, frame = self.cap.read()
        if not ret or frame is None:
            logger.error(f"❌ Stream aberto mas não conseguiu ler frame: {rtsp_url}")
            self.cap.release()
            self.cap = None
            return False
        
        logger.info(f"✅ Stream iniciado: {rtsp_url}")
        return True
    
    def stop_stream(self):
        """Para o stream de vídeo."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("Stream parado")
    
    def get_frame(self):
        """Obtém o frame atual do stream."""
        if self.cap is None or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return None
        
        return frame
    
    def continuous_move(self, pan_speed, tilt_speed, zoom_speed=0, profile_token=None, duration=1.0):
        """Move a câmera continuamente na direção especificada por um tempo determinado."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return False
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        try:
            logger.info(f"Movimento contínuo: Pan={pan_speed}, Tilt={tilt_speed}, Zoom={zoom_speed}, Duração={duration}s")
            
            request = self.ptz.create_type('ContinuousMove')
            request.ProfileToken = profile_token
            
            # Criar objeto Velocity se não existir
            if not hasattr(request, 'Velocity'):
                request.Velocity = self.ptz.GetStatus({'ProfileToken': profile_token}).Position
            
            # Definir velocidades
            if hasattr(request.Velocity, 'PanTilt'):
                request.Velocity.PanTilt.x = pan_speed
                request.Velocity.PanTilt.y = tilt_speed
            
            if hasattr(request.Velocity, 'Zoom'):
                request.Velocity.Zoom.x = zoom_speed
            
            # Executar movimento
            self.ptz.ContinuousMove(request)
            
            # Aguardar a duração especificada
            time.sleep(duration)
            
            # Parar o movimento
            self.ptz.Stop({'ProfileToken': profile_token})
            return True
        except Exception as e:
            logger.error(f"Erro ao executar movimento contínuo: {str(e)}")
            # Tentar parar o movimento em caso de erro
            try:
                self.ptz.Stop({'ProfileToken': profile_token})
            except:
                pass
            return False
    
    def move_right(self, speed=0.5, duration=1.0):
        """Move a câmera para a direita."""
        return self.continuous_move(speed, 0, 0, duration=duration)
    
    def move_left(self, speed=0.5, duration=1.0):
        """Move a câmera para a esquerda."""
        return self.continuous_move(-speed, 0, 0, duration=duration)
    
    def move_up(self, speed=0.5, duration=1.0):
        """Move a câmera para cima."""
        return self.continuous_move(0, speed, 0, duration=duration)
    
    def move_down(self, speed=0.5, duration=1.0):
        """Move a câmera para baixo."""
        return self.continuous_move(0, -speed, 0, duration=duration)
    
    def zoom_in(self, speed=0.5, duration=1.0):
        """Aumenta o zoom da câmera."""
        return self.continuous_move(0, 0, speed, duration=duration)
    
    def zoom_out(self, speed=0.5, duration=1.0):
        """Diminui o zoom da câmera."""
        return self.continuous_move(0, 0, -speed, duration=duration)
    
    def get_presets(self):
        """Obtém as posições predefinidas da câmera."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return []
        
        try:
            presets = self.ptz.GetPresets({'ProfileToken': self.current_profile.token})
            logger.info(f"Presets encontrados: {len(presets)}")
            for preset in presets:
                logger.info(f"  - Preset: {preset.Name} (Token: {preset.token})")
            return presets
        except Exception as e:
            logger.error(f"Erro ao obter presets: {str(e)}")
            return []
    
    def set_preset(self, name):
        """Define uma nova posição predefinida."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return None
        
        try:
            logger.info(f"Definindo preset: {name}")
            preset = self.ptz.SetPreset({
                'ProfileToken': self.current_profile.token,
                'PresetName': name
            })
            logger.info(f"✅ Preset '{name}' definido com token: {preset.PresetToken}")
            return preset.PresetToken
        except Exception as e:
            logger.error(f"❌ Erro ao definir preset: {str(e)}")
            return None
    
    def goto_preset(self, preset_token):
        """Move a câmera para uma posição predefinida."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return False
        
        try:
            logger.info(f"Indo para preset: {preset_token}")
            self.ptz.GotoPreset({
                'ProfileToken': self.current_profile.token,
                'PresetToken': preset_token
            })
            logger.info(f"✅ Movido para preset: {preset_token}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao ir para preset: {str(e)}")
            return False

def run_interactive_demo(controller):
    """Executa uma demonstração interativa com stream de vídeo e controle PTZ."""
    # Testar URLs RTSP
    working_urls = controller.test_rtsp_urls()
    
    if not working_urls:
        logger.error("Nenhuma URL RTSP funcionando")
        return
    
    # Usar a primeira URL que funciona
    first_url = list(working_urls.values())[0]["url"]
    
    # Iniciar stream
    if not controller.start_stream(first_url):
        logger.error("Falha ao iniciar stream")
        return
    
    # Criar janela para exibir o vídeo
    window_name = "Camera Control - Pressione ESC para sair"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    print("\n=== Controle da Câmera ===")
    print("Comandos de teclado:")
    print("  A: Mover para a esquerda")
    print("  D: Mover para a direita")
    print("  W: Mover para cima")
    print("  S: Mover para baixo")
    print("  Z: Zoom in")
    print("  X: Zoom out")
    print("  P: Definir preset na posição atual")
    print("  G: Ir para preset")
    print("  1-3: Alternar entre perfis de vídeo")
    print("  ESC: Sair")
    
    # Loop principal
    running = True
    while running:
        # Obter frame
        frame = controller.get_frame()
        
        if frame is not None:
            # Adicionar informações ao frame
            height, width = frame.shape[:2]
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Resolução: {width}x{height}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Adicionar instruções na tela
            cv2.putText(frame, "W: Cima, S: Baixo, A: Esq, D: Dir", (10, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Z: Zoom+, X: Zoom-, ESC: Sair", (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Exibir frame
            cv2.imshow(window_name, frame)
        
        # Processar teclas - esperar 30ms por uma tecla
        key = cv2.waitKey(30) & 0xFF
        
        # Verificar teclas pressionadas
        if key == 27:  # ESC
            running = False
            logger.info("Saindo do programa")
        elif key == ord('a') or key == ord('A'):
            logger.info("Movendo para a esquerda")
            controller.move_left(speed=0.5, duration=0.5)
        elif key == ord('d') or key == ord('D'):
            logger.info("Movendo para a direita")
            controller.move_right(speed=0.5, duration=0.5)
        elif key == ord('w') or key == ord('W'):
            logger.info("Movendo para cima")
            controller.move_up(speed=0.5, duration=0.5)
        elif key == ord('s') or key == ord('S'):
            logger.info("Movendo para baixo")
            controller.move_down(speed=0.5, duration=0.5)
        elif key == ord('z') or key == ord('Z'):
            logger.info("Zoom in")
            controller.zoom_in(speed=0.5, duration=0.5)
        elif key == ord('x') or key == ord('X'):
            logger.info("Zoom out")
            controller.zoom_out(speed=0.5, duration=0.5)
        elif key == ord('p') or key == ord('P'):
            # Pausar o stream para entrada do usuário
            name = input("Digite o nome do preset: ")
            controller.set_preset(name)
        elif key == ord('g') or key == ord('G'):
            # Pausar o stream para entrada do usuário
            presets = controller.get_presets()
            if presets:
                for i, preset in enumerate(presets):
                    print(f"{i+1} - {preset.Name} (Token: {preset.token})")
                try:
                    idx = int(input("Selecione o número do preset: ")) - 1
                    if 0 <= idx < len(presets):
                        controller.goto_preset(presets[idx].token)
                except ValueError:
                    print("Entrada inválida")
            else:
                print("Nenhum preset disponível")
        elif key == ord('1'):
            # Alternar para perfil 0 (alta resolução)
            url = f"rtsp://{controller.username}:{controller.password}@{controller.ip}:{controller.rtsp_port}/profile0"
            controller.start_stream(url)
        elif key == ord('2'):
            # Alternar para perfil 1 (média resolução)
            url = f"rtsp://{controller.username}:{controller.password}@{controller.ip}:{controller.rtsp_port}/profile1"
            controller.start_stream(url)
        elif key == ord('3'):
            # Alternar para perfil 2 (baixa resolução)
            url = f"rtsp://{controller.username}:{controller.password}@{controller.ip}:{controller.rtsp_port}/profile2"
            controller.start_stream(url)
    
    # Limpar
    controller.stop_stream()
    cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='Controle PTZ com visualização RTSP para câmera ONVIF')
    parser.add_argument('--ip', default=CAMERA_IP, help='Endereço IP da câmera')
    parser.add_argument('--onvif-port', type=int, default=ONVIF_PORT, help='Porta ONVIF')
    parser.add_argument('--rtsp-port', type=int, default=RTSP_PORT, help='Porta RTSP')
    parser.add_argument('--user', default=USERNAME, help='Nome de usuário')
    parser.add_argument('--password', default=PASSWORD, help='Senha')
    
    args = parser.parse_args()
    
    # Criar controlador
    controller = CameraController(
        args.ip, 
        args.onvif_port, 
        args.rtsp_port, 
        args.user, 
        args.password
    )
    
    # Conectar à câmera
    if not controller.connect_onvif():
        logger.error("Falha ao conectar à câmera. Encerrando.")
        return
    
    # Executar demonstração interativa
    run_interactive_demo(controller)

if __name__ == "__main__":
    main() 