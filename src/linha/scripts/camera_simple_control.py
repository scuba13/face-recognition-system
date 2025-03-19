import cv2
import time
import logging
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

# URL RTSP que sabemos que funciona
RTSP_URL = f"rtsp://{USERNAME}:{PASSWORD}@{CAMERA_IP}:{RTSP_PORT}/profile1"

class SimpleCameraControl:
    def __init__(self, ip, onvif_port, rtsp_url):
        self.ip = ip
        self.onvif_port = onvif_port
        self.rtsp_url = rtsp_url
        self.username = USERNAME
        self.password = PASSWORD
        self.cam = None
        self.ptz = None
        self.media = None
        self.profile = None
        self.cap = None
        
    def connect(self):
        """Conecta à câmera via ONVIF."""
        try:
            logger.info(f"Conectando à câmera ONVIF em {self.ip}:{self.onvif_port}")
            self.cam = ONVIFCamera(self.ip, self.onvif_port, self.username, self.password)
            
            # Inicializar serviços
            self.media = self.cam.create_media_service()
            self.ptz = self.cam.create_ptz_service()
            
            # Obter perfil
            profiles = self.media.GetProfiles()
            if profiles:
                self.profile = profiles[0]
                logger.info(f"Conectado com sucesso. Usando perfil: {self.profile.Name}")
                return True
            else:
                logger.error("Nenhum perfil encontrado na câmera")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao conectar via ONVIF: {str(e)}")
            return False
    
    def start_stream(self):
        """Inicia o stream de vídeo."""
        logger.info(f"Iniciando stream: {self.rtsp_url}")
        self.cap = cv2.VideoCapture(self.rtsp_url)
        time.sleep(2)  # Dar tempo para conectar
        
        if not self.cap.isOpened():
            logger.error(f"Falha ao abrir stream: {self.rtsp_url}")
            return False
        
        logger.info("Stream iniciado com sucesso")
        return True
    
    def move_camera(self, pan_direction, tilt_direction, zoom_direction=0):
        """Move a câmera usando AbsoluteMove em vez de ContinuousMove."""
        if not self.ptz or not self.profile:
            logger.error("PTZ não disponível")
            return False
        
        try:
            # Obter posição atual
            status = self.ptz.GetStatus({'ProfileToken': self.profile.token})
            logger.info(f"Status atual: {status}")
            
            if not status or not hasattr(status, 'Position') or not hasattr(status.Position, 'PanTilt'):
                logger.error("Não foi possível obter a posição atual da câmera")
                return False
            
            # Obter posição atual
            current_x = status.Position.PanTilt.x
            current_y = status.Position.PanTilt.y
            
            # Calcular nova posição (valores entre 0 e 1)
            # Usar incrementos maiores para movimentos mais perceptíveis
            increment = 0.2  # Incremento significativo
            new_x = max(0, min(1, current_x + (pan_direction * increment)))
            new_y = max(0, min(1, current_y + (tilt_direction * increment)))
            
            logger.info(f"Movendo de ({current_x:.2f}, {current_y:.2f}) para ({new_x:.2f}, {new_y:.2f})")
            
            # Criar request para movimento absoluto
            request = {
                'ProfileToken': self.profile.token,
                'Position': {
                    'PanTilt': {
                        'x': new_x,
                        'y': new_y
                    },
                    'Zoom': {
                        'x': 0  # Zoom fixo, já que não é suportado
                    }
                },
                'Speed': {
                    'PanTilt': {
                        'x': 1.0,  # Velocidade máxima
                        'y': 1.0   # Velocidade máxima
                    },
                    'Zoom': {
                        'x': 1.0
                    }
                }
            }
            
            # Executar movimento absoluto
            self.ptz.AbsoluteMove(request)
            logger.info(f"Comando AbsoluteMove enviado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao mover câmera: {str(e)}")
            return False
    
    def zoom(self, zoom_factor):
        """Informa que o zoom não é suportado pela câmera."""
        logger.warning("Zoom não suportado por esta câmera via ONVIF (Zoom retorna None no status)")
        logger.info("Verificando status da câmera para confirmar...")
        
        try:
            # Obter posição atual
            status = self.ptz.GetStatus({'ProfileToken': self.profile.token})
            
            # Verificar se o zoom está disponível
            if status and hasattr(status, 'Position') and status.Position.Zoom is None:
                logger.warning("Confirmado: Zoom não está disponível nesta câmera via ONVIF")
                return False
            
            # Se chegou aqui, talvez o zoom esteja disponível, tentar mesmo assim
            logger.info(f"Tentando aplicar zoom mesmo assim: {zoom_factor}")
            
            # Tentar usar RelativeMove para zoom
            request = {
                'ProfileToken': self.profile.token,
                'Translation': {
                    'Zoom': {
                        'x': zoom_factor
                    }
                },
                'Speed': {
                    'Zoom': {
                        'x': 0.5
                    }
                }
            }
            
            self.ptz.RelativeMove(request)
            return True
        except Exception as e:
            logger.error(f"Erro ao aplicar zoom: {str(e)}")
            return False
    
    def set_preset(self, name):
        """Define uma nova posição predefinida."""
        if not self.ptz or not self.profile:
            logger.error("PTZ não disponível")
            return None
        
        try:
            preset = self.ptz.SetPreset({
                'ProfileToken': self.profile.token,
                'PresetName': name
            })
            logger.info(f"Preset '{name}' definido com token: {preset.PresetToken}")
            return preset.PresetToken
        except Exception as e:
            logger.error(f"Erro ao definir preset: {str(e)}")
            return None
    
    def goto_preset(self, preset_token):
        """Move a câmera para uma posição predefinida."""
        if not self.ptz or not self.profile:
            logger.error("PTZ não disponível")
            return False
        
        try:
            self.ptz.GotoPreset({
                'ProfileToken': self.profile.token,
                'PresetToken': preset_token
            })
            logger.info(f"Movido para preset: {preset_token}")
            return True
        except Exception as e:
            logger.error(f"Erro ao ir para preset: {str(e)}")
            return False
    
    def get_presets(self):
        """Obtém as posições predefinidas da câmera."""
        if not self.ptz or not self.profile:
            logger.error("PTZ não disponível")
            return []
        
        try:
            presets = self.ptz.GetPresets({'ProfileToken': self.profile.token})
            logger.info(f"Presets encontrados: {len(presets)}")
            for preset in presets:
                logger.info(f"  - Preset: {preset.Name} (Token: {preset.token})")
            return presets
        except Exception as e:
            logger.error(f"Erro ao obter presets: {str(e)}")
            return []
    
    def run(self):
        """Executa o controle da câmera."""
        if not self.start_stream():
            logger.error("Falha ao iniciar stream. Encerrando.")
            return
        
        window_name = "Controle de Câmera - ESC para sair"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        print("\n=== CONTROLE SIMPLES DE CÂMERA ===")
        print("Comandos de teclado:")
        print("  W: Mover para cima")
        print("  S: Mover para baixo")
        print("  A: Mover para a esquerda")
        print("  D: Mover para a direita")
        print("  Z: Zoom in (pode não funcionar)")
        print("  X: Zoom out (pode não funcionar)")
        print("  P: Definir preset")
        print("  G: Ir para preset")
        print("  ESC: Sair")
        
        # Verificar se o zoom é suportado
        try:
            status = self.ptz.GetStatus({'ProfileToken': self.profile.token})
            if status and hasattr(status, 'Position') and status.Position.Zoom is None:
                print("\n⚠️ AVISO: Zoom não suportado por esta câmera via ONVIF")
                print("   Os comandos Z e X podem não funcionar.")
        except Exception:
            pass
        
        running = True
        while running:
            # Ler frame
            ret, frame = self.cap.read()
            
            if ret:
                # Adicionar informações ao frame
                height, width = frame.shape[:2]
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Adicionar instruções na tela
                cv2.putText(frame, "W/S/A/D: Movimento (AbsoluteMove)", (10, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "ESC: Sair | P: Preset | G: Ir para preset", (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Exibir frame
                cv2.imshow(window_name, frame)
            
            # Processar teclas - esperar 30ms por uma tecla
            key = cv2.waitKey(30) & 0xFF
            
            # Verificar teclas pressionadas
            if key == 27:  # ESC
                running = False
                logger.info("Saindo do programa")
            elif key == ord('w') or key == ord('W'):
                logger.info("Movendo para cima")
                self.move_camera(0, 0.3)
            elif key == ord('s') or key == ord('S'):
                logger.info("Movendo para baixo")
                self.move_camera(0, -0.3)
            elif key == ord('a') or key == ord('A'):
                logger.info("Movendo para a esquerda")
                self.move_camera(-0.3, 0)
            elif key == ord('d') or key == ord('D'):
                logger.info("Movendo para a direita")
                self.move_camera(0.3, 0)
            elif key == ord('z') or key == ord('Z'):
                logger.info("Tentando zoom in")
                self.zoom(0.1)
            elif key == ord('x') or key == ord('X'):
                logger.info("Tentando zoom out")
                self.zoom(-0.1)
            elif key == ord('p') or key == ord('P'):
                # Pausar o stream para entrada do usuário
                name = input("Digite o nome do preset: ")
                self.set_preset(name)
            elif key == ord('g') or key == ord('G'):
                # Pausar o stream para entrada do usuário
                presets = self.get_presets()
                if presets:
                    for i, preset in enumerate(presets):
                        print(f"{i+1} - {preset.Name} (Token: {preset.token})")
                    try:
                        idx = int(input("Selecione o número do preset: ")) - 1
                        if 0 <= idx < len(presets):
                            self.goto_preset(presets[idx].token)
                    except ValueError:
                        print("Entrada inválida")
                else:
                    print("Nenhum preset disponível")
        
        # Limpar
        self.cap.release()
        cv2.destroyAllWindows()

def main():
    # Criar controlador
    controller = SimpleCameraControl(CAMERA_IP, ONVIF_PORT, RTSP_URL)
    
    # Conectar à câmera
    if not controller.connect():
        logger.error("Falha ao conectar à câmera. Encerrando.")
        return
    
    # Executar controle
    controller.run()

if __name__ == "__main__":
    main() 