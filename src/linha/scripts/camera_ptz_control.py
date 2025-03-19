import cv2
import time
import json
import sys
import os
import numpy as np
import threading
from onvif import ONVIFCamera
import logging
import argparse

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração padrão da câmera
DEFAULT_CAMERA_IP = "192.168.0.130"
DEFAULT_ONVIF_PORT = 6688  # Porta ONVIF confirmada
DEFAULT_RTSP_PORT = 8554   # Porta RTSP confirmada
DEFAULT_USER = "admin"
DEFAULT_PASS = "admin123456"

# Perfis RTSP conhecidos
RTSP_PROFILES = [
    "profile0",  # 1920x1080 @ 16fps
    "profile1",  # 640x360 @ 16fps
    "profile2",   # 640x360 @ 5fps
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
    
    def stream_video(self, rtsp_url, window_name="Camera Stream"):
        """Exibe o stream de vídeo em uma janela."""
        def stream_thread_func(rtsp_url, window_name):
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                logger.error(f"Não foi possível abrir o stream: {rtsp_url}")
                return
            
            logger.info(f"Stream iniciado: {rtsp_url}")
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            
            while not self.stop_stream:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Erro ao ler frame do stream")
                    time.sleep(0.5)
                    continue
                
                # Adicionar informações ao frame
                height, width = frame.shape[:2]
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Resolução: {width}x{height}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
            cv2.destroyWindow(window_name)
            logger.info("Stream encerrado")
        
        # Parar stream anterior se existir
        self.stop_stream_video()
        
        # Iniciar novo stream
        self.stop_stream = False
        self.stream_thread = threading.Thread(target=stream_thread_func, args=(rtsp_url, window_name))
        self.stream_thread.daemon = True
        self.stream_thread.start()
    
    def stop_stream_video(self):
        """Para o stream de vídeo."""
        if self.stream_thread and self.stream_thread.is_alive():
            self.stop_stream = True
            self.stream_thread.join(timeout=3)
            logger.info("Stream de vídeo interrompido")
    
    def get_ptz_status(self, profile_token=None):
        """Obtém o status atual do PTZ."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return None
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        try:
            status = self.ptz.GetStatus({'ProfileToken': profile_token})
            return status
        except Exception as e:
            logger.error(f"Erro ao obter status PTZ: {str(e)}")
            return None
    
    def absolute_move(self, pan, tilt, zoom, profile_token=None):
        """Move a câmera para uma posição absoluta."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return False
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        try:
            logger.info(f"Movendo para posição absoluta: Pan={pan}, Tilt={tilt}, Zoom={zoom}")
            
            request = self.ptz.create_type('AbsoluteMove')
            request.ProfileToken = profile_token
            
            request.Position = self.ptz.GetStatus({'ProfileToken': profile_token}).Position
            
            # Definir posição desejada
            request.Position.PanTilt.x = pan
            request.Position.PanTilt.y = tilt
            request.Position.Zoom.x = zoom
            
            # Executar movimento
            self.ptz.AbsoluteMove(request)
            return True
        except Exception as e:
            logger.error(f"Erro ao executar movimento absoluto: {str(e)}")
            return False
    
    def continuous_move(self, pan_speed, tilt_speed, zoom_speed, profile_token=None, duration=1.0):
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
    
    def move_preset_positions(self, profile_token=None):
        """Move a câmera para posições predefinidas para testar o PTZ."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return False
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        # Testar movimentos contínuos em diferentes direções
        movements = [
            {"name": "Direita", "pan": 0.5, "tilt": 0, "zoom": 0},
            {"name": "Esquerda", "pan": -0.5, "tilt": 0, "zoom": 0},
            {"name": "Cima", "pan": 0, "tilt": 0.5, "zoom": 0},
            {"name": "Baixo", "pan": 0, "tilt": -0.5, "zoom": 0},
            {"name": "Zoom In", "pan": 0, "tilt": 0, "zoom": 0.5},
            {"name": "Zoom Out", "pan": 0, "tilt": 0, "zoom": -0.5},
            {"name": "Diagonal Superior Direita", "pan": 0.3, "tilt": 0.3, "zoom": 0},
            {"name": "Diagonal Inferior Esquerda", "pan": -0.3, "tilt": -0.3, "zoom": 0},
            {"name": "Centro", "pan": 0, "tilt": 0, "zoom": 0}
        ]
        
        for move in movements:
            logger.info(f"Testando movimento: {move['name']}")
            self.continuous_move(move["pan"], move["tilt"], move["zoom"], profile_token, duration=2.0)
            time.sleep(1)  # Pausa entre movimentos
        
        return True
    
    def get_presets(self, profile_token=None):
        """Obtém as posições predefinidas da câmera."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return []
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        try:
            presets = self.ptz.GetPresets({'ProfileToken': profile_token})
            logger.info(f"Presets encontrados: {len(presets)}")
            for preset in presets:
                logger.info(f"  - Preset: {preset.Name} (Token: {preset.token})")
            return presets
        except Exception as e:
            logger.error(f"Erro ao obter presets: {str(e)}")
            return []
    
    def goto_preset(self, preset_token, profile_token=None):
        """Move a câmera para uma posição predefinida."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return False
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        try:
            logger.info(f"Indo para preset: {preset_token}")
            self.ptz.GotoPreset({'ProfileToken': profile_token, 'PresetToken': preset_token})
            return True
        except Exception as e:
            logger.error(f"Erro ao ir para preset: {str(e)}")
            return False
    
    def set_preset(self, preset_name, profile_token=None):
        """Define uma nova posição predefinida."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return False
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        try:
            logger.info(f"Definindo preset: {preset_name}")
            preset = self.ptz.SetPreset({'ProfileToken': profile_token, 'PresetName': preset_name})
            logger.info(f"Preset definido com token: {preset.PresetToken}")
            return preset.PresetToken
        except Exception as e:
            logger.error(f"Erro ao definir preset: {str(e)}")
            return None
    
    def remove_preset(self, preset_token, profile_token=None):
        """Remove uma posição predefinida."""
        if not self.connected or not self.ptz:
            logger.error("Não conectado à câmera ou PTZ não disponível")
            return False
        
        if profile_token is None and self.current_profile:
            profile_token = self.current_profile.token
        
        try:
            logger.info(f"Removendo preset: {preset_token}")
            self.ptz.RemovePreset({'ProfileToken': profile_token, 'PresetToken': preset_token})
            return True
        except Exception as e:
            logger.error(f"Erro ao remover preset: {str(e)}")
            return False
    
    def run_interactive_demo(self):
        """Executa uma demonstração interativa de controle da câmera."""
        if not self.connected:
            logger.error("Não conectado à câmera")
            return
        
        # Testar URLs RTSP
        working_urls = self.test_rtsp_urls()
        
        if not working_urls:
            logger.error("Nenhuma URL RTSP funcionando")
            return
        
        # Usar a primeira URL que funciona
        first_url = list(working_urls.values())[0]["url"]
        
        # Iniciar stream de vídeo
        self.stream_video(first_url)
        
        print("\n=== Demonstração Interativa de Controle PTZ ===")
        print("Comandos disponíveis:")
        print("  1 - Mover para a direita")
        print("  2 - Mover para a esquerda")
        print("  3 - Mover para cima")
        print("  4 - Mover para baixo")
        print("  5 - Zoom in")
        print("  6 - Zoom out")
        print("  7 - Testar sequência de movimentos")
        print("  8 - Listar presets")
        print("  9 - Definir preset atual")
        print("  0 - Ir para preset")
        print("  q - Sair")
        
        while True:
            cmd = input("\nDigite um comando: ")
            
            if cmd == 'q':
                break
            elif cmd == '1':
                self.continuous_move(0.5, 0, 0, duration=1.0)
            elif cmd == '2':
                self.continuous_move(-0.5, 0, 0, duration=1.0)
            elif cmd == '3':
                self.continuous_move(0, 0.5, 0, duration=1.0)
            elif cmd == '4':
                self.continuous_move(0, -0.5, 0, duration=1.0)
            elif cmd == '5':
                self.continuous_move(0, 0, 0.5, duration=1.0)
            elif cmd == '6':
                self.continuous_move(0, 0, -0.5, duration=1.0)
            elif cmd == '7':
                self.move_preset_positions()
            elif cmd == '8':
                self.get_presets()
            elif cmd == '9':
                name = input("Digite o nome do preset: ")
                self.set_preset(name)
            elif cmd == '0':
                presets = self.get_presets()
                if presets:
                    for i, preset in enumerate(presets):
                        print(f"{i+1} - {preset.Name} (Token: {preset.token})")
                    idx = int(input("Selecione o número do preset: ")) - 1
                    if 0 <= idx < len(presets):
                        self.goto_preset(presets[idx].token)
                else:
                    print("Nenhum preset disponível")
        
        # Parar o stream de vídeo
        self.stop_stream_video()

def main():
    parser = argparse.ArgumentParser(description='Controle PTZ e teste de RTSP para câmera ONVIF')
    parser.add_argument('--ip', default=DEFAULT_CAMERA_IP, help='Endereço IP da câmera')
    parser.add_argument('--onvif-port', type=int, default=DEFAULT_ONVIF_PORT, help='Porta ONVIF')
    parser.add_argument('--rtsp-port', type=int, default=DEFAULT_RTSP_PORT, help='Porta RTSP')
    parser.add_argument('--user', default=DEFAULT_USER, help='Nome de usuário')
    parser.add_argument('--password', default=DEFAULT_PASS, help='Senha')
    parser.add_argument('--test-rtsp', action='store_true', help='Apenas testar URLs RTSP')
    parser.add_argument('--test-ptz', action='store_true', help='Apenas testar movimentos PTZ')
    parser.add_argument('--interactive', action='store_true', help='Modo interativo')
    
    args = parser.parse_args()
    
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
    
    if args.test_rtsp:
        # Apenas testar URLs RTSP
        working_urls = controller.test_rtsp_urls()
        print("\n=== URLs RTSP Funcionando ===")
        for name, info in working_urls.items():
            print(f"{name}: {info['url']} ({info['resolution']} @ {info['fps']}fps)")
    
    elif args.test_ptz:
        # Apenas testar movimentos PTZ
        print("\n=== Testando Movimentos PTZ ===")
        controller.move_preset_positions()
    
    elif args.interactive:
        # Modo interativo
        controller.run_interactive_demo()
    
    else:
        # Executar demonstração completa
        print("\n=== Demonstração Completa ===")
        
        # Testar URLs RTSP
        working_urls = controller.test_rtsp_urls()
        if working_urls:
            print("\n=== URLs RTSP Funcionando ===")
            for name, info in working_urls.items():
                print(f"{name}: {info['url']} ({info['resolution']} @ {info['fps']}fps)")
            
            # Usar a primeira URL que funciona
            first_url = list(working_urls.values())[0]["url"]
            
            # Iniciar stream de vídeo
            print("\nIniciando stream de vídeo. Pressione 'q' na janela do vídeo para sair.")
            controller.stream_video(first_url)
            
            # Testar movimentos PTZ
            print("\n=== Testando Movimentos PTZ ===")
            controller.move_preset_positions()
            
            # Aguardar um pouco para visualizar o stream
            time.sleep(5)
            
            # Parar o stream de vídeo
            controller.stop_stream_video()
        else:
            print("Nenhuma URL RTSP funcionando")

if __name__ == "__main__":
    main() 