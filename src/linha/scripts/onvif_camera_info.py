import cv2
import subprocess
import time
import json
import sys
import requests
from onvif import ONVIFCamera
import logging
import os

# Configurar logging para ver mensagens detalhadas
logging.basicConfig(level=logging.DEBUG)

# Configuração da câmera
CAMERA_IP = "192.168.0.130"
CAMERA_USER = "admin"  # Usuário padrão comum para câmeras
CAMERA_PASS = "admin123456"  # Senha padrão comum para câmeras

# Portas específicas da câmera (conforme informado)
HTTP_PORT = 80
RTSP_PORT = 8554
HTTPS_PORT = 443
SERVER_PORT = 6688

# Portas para testar com ONVIF
ONVIF_PORTS = [HTTP_PORT, HTTPS_PORT, SERVER_PORT, 8000, 8080]

# Caminhos ONVIF comuns para testar
ONVIF_PATHS = [
    "/onvif/device_service",
    "/onvif/services",
    "/onvif/service",
    "/device_service",
    "/services",
    "/onvif"
]

# URLs RTSP para testar
RTSP_URLS = [
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/stream",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/live",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/h264",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/ch01/main/av_stream",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/profile1",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/profile2",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/cam/realmonitor",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/video1",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/video2",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/media/video1",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/11",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/1",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/Streaming/Channels/1",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/Streaming/Channels/101",
    f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/cam/realmonitor?channel=1&subtype=0"
]

# Dicionário para armazenar as informações da câmera
camera_data = {
    "device_info": {},
    "network_config": [],
    "video_profiles": [],
    "rtsp_tests": {},
    "onvif_services": {},
    "ptz_status": "Indisponível",
    "connection_attempts": [],
    "rtsp_url_tests": {}
}

def testar_stream_opencv(rtsp_url):
    """Testa o RTSP usando OpenCV com tempo extra para carregar o stream."""
    print(f"Testando stream RTSP: {rtsp_url}")
    try:
        time.sleep(1)
        cap = cv2.VideoCapture(rtsp_url)
        time.sleep(3)
        is_opened = cap.isOpened()
        if is_opened:
            # Tentar ler um frame para confirmar que o stream está funcionando
            ret, frame = cap.read()
            is_opened = ret and frame is not None
            if is_opened:
                print(f"✅ Stream RTSP funcionando: {rtsp_url}")
                # Salvar um frame como imagem para verificação
                img_path = f"camera_frame_{CAMERA_IP.replace('.', '_')}.jpg"
                cv2.imwrite(img_path, frame)
                print(f"Frame salvo em {img_path}")
            else:
                print(f"⚠ Stream RTSP aberto mas não conseguiu ler frame: {rtsp_url}")
        else:
            print(f"❌ Stream RTSP falhou: {rtsp_url}")
        cap.release()
        return is_opened
    except Exception as e:
        print(f"❌ Erro ao testar stream RTSP {rtsp_url}: {str(e)}")
        return False

def testar_servicos_onvif(cam):
    """Testa os serviços ONVIF disponíveis na câmera."""
    servicos = {
        "device": cam.create_devicemgmt_service,
        "media": cam.create_media_service,
        "ptz": cam.create_ptz_service,
        "imaging": cam.create_imaging_service,
        "events": cam.create_events_service
    }

    for nome, func in servicos.items():
        try:
            print(f"Testando serviço ONVIF: {nome}")
            service = func()
            if service:
                camera_data["onvif_services"][nome] = "Disponível"
        except Exception as e:
            print(f"Erro ao testar serviço {nome}: {str(e)}")
            camera_data["onvif_services"][nome] = "Indisponível"

def mover_camera(ptz, profile_token, pan=0, tilt=0, zoom=0, speed=0.5):
    """Movimenta a câmera em Pan (esquerda/direita), Tilt (cima/baixo) e Zoom."""
    try:
        move_request = ptz.create_type("ContinuousMove")
        move_request.ProfileToken = profile_token
        move_request.Velocity = ptz.GetStatus({"ProfileToken": profile_token}).Position

        # Define velocidade de movimento
        move_request.Velocity.PanTilt.x = pan * speed  # -1 esquerda, 1 direita
        move_request.Velocity.PanTilt.y = tilt * speed  # -1 para baixo, 1 para cima
        move_request.Velocity.Zoom.x = zoom * speed  # -1 zoom out, 1 zoom in

        ptz.ContinuousMove(move_request)
        time.sleep(1)  # Espera 1 segundo para a câmera se mover
        ptz.Stop({"ProfileToken": profile_token})  # Para o movimento
    except Exception as e:
        print(f"Erro ao mover câmera: {str(e)}")

def testar_http_camera():
    """Testa se a câmera responde a requisições HTTP básicas."""
    try:
        print(f"\n=== Testando conexão HTTP básica com a câmera ===")
        url = f"http://{CAMERA_IP}"
        response = requests.get(url, timeout=5)
        print(f"Resposta HTTP: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao conectar via HTTP: {str(e)}")
        return False

def testar_https_camera():
    """Testa se a câmera responde a requisições HTTPS."""
    try:
        print(f"\n=== Testando conexão HTTPS com a câmera ===")
        url = f"https://{CAMERA_IP}:{HTTPS_PORT}"
        response = requests.get(url, timeout=5, verify=False)
        print(f"Resposta HTTPS: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao conectar via HTTPS: {str(e)}")
        return False

def tentar_conectar_onvif(ip, port, user, password, path=None):
    """Tenta conectar à câmera ONVIF com os parâmetros fornecidos."""
    attempt_info = {
        "ip": ip,
        "port": port,
        "user": user,
        "password": "***" if password else "",
        "path": path,
        "success": False,
        "error": None
    }
    
    try:
        print(f"\n=== Tentando conectar à câmera ONVIF em {ip}:{port}{' com path '+path if path else ''} com usuário '{user}' ===")
        
        # Se um caminho específico foi fornecido, use-o
        if path:
            # Criar URL base para o serviço ONVIF
            wsdl_override = {'devicemgmt': f'http://{ip}:{port}{path}?wsdl'}
            cam = ONVIFCamera(ip, port, user, password, wsdl_override=wsdl_override)
        else:
            cam = ONVIFCamera(ip, port, user, password)
        
        # Testar conexão básica
        devicemgmt = cam.create_devicemgmt_service()
        info = devicemgmt.GetDeviceInformation()
        
        print(f"Conexão bem-sucedida! Informações do dispositivo:")
        print(f"Fabricante: {info.Manufacturer}")
        print(f"Modelo: {info.Model}")
        print(f"Firmware: {info.FirmwareVersion}")
        
        attempt_info["success"] = True
        attempt_info["device_info"] = {
            "manufacturer": info.Manufacturer,
            "model": info.Model,
            "firmware": info.FirmwareVersion
        }
        return cam, attempt_info
    except Exception as e:
        error_msg = str(e)
        print(f"⚠ Erro ao conectar via ONVIF: {error_msg}")
        attempt_info["error"] = error_msg
        return None, attempt_info

def testar_urls_rtsp():
    """Testa várias URLs RTSP comuns para encontrar streams disponíveis."""
    print("\n=== Testando URLs RTSP comuns ===")
    
    for url in RTSP_URLS:
        success = testar_stream_opencv(url)
        camera_data["rtsp_url_tests"][url] = "Sucesso" if success else "Falha"
        
        if success:
            print(f"✅ URL RTSP funcionando: {url}")
            # Se encontrou uma URL que funciona, não precisa testar todas
            return url
    
    return None

def obter_informacoes_camera():
    # Primeiro, testar conexão HTTP básica
    http_ok = testar_http_camera()
    if not http_ok:
        print("⚠ Aviso: Câmera não responde a requisições HTTP básicas.")
    
    # Testar conexão HTTPS
    https_ok = testar_https_camera()
    if https_ok:
        print("✅ Câmera responde a requisições HTTPS.")
    
    # Tentar conectar com ONVIF em diferentes portas e caminhos
    cam = None
    for port in ONVIF_PORTS:
        # Primeiro tenta o caminho padrão
        cam, attempt_info = tentar_conectar_onvif(CAMERA_IP, port, CAMERA_USER, CAMERA_PASS)
        camera_data["connection_attempts"].append(attempt_info)
        
        if cam:
            print(f"✅ Conexão ONVIF bem-sucedida na porta {port} com caminho padrão")
            break
        
        # Se falhar, tenta caminhos alternativos
        for path in ONVIF_PATHS:
            cam, attempt_info = tentar_conectar_onvif(CAMERA_IP, port, CAMERA_USER, CAMERA_PASS, path)
            camera_data["connection_attempts"].append(attempt_info)
            
            if cam:
                print(f"✅ Conexão ONVIF bem-sucedida na porta {port} com caminho {path}")
                break
        
        if cam:
            break
    
    # Se conseguiu conectar via ONVIF, obter informações detalhadas
    if cam:
        try:
            # Obter informações do dispositivo
            device = cam.create_devicemgmt_service()
            info = device.GetDeviceInformation()

            camera_data["device_info"] = {
                "fabricante": info.Manufacturer,
                "modelo": info.Model,
                "versao_firmware": info.FirmwareVersion,
                "hardware_id": info.HardwareId,
                "serial": info.SerialNumber
            }

            # Testar serviços ONVIF disponíveis
            testar_servicos_onvif(cam)

            # Obter informações de rede
            try:
                network_service = cam.create_devicemgmt_service()
                network_interfaces = network_service.GetNetworkInterfaces()

                for interface in network_interfaces:
                    interface_data = {
                        "interface": interface.token,
                        "mac_address": interface.Info.HwAddress,
                        "dhcp": "Ativado" if interface.IPv4.Config.DHCP else "Desativado",
                        "ipv4": interface.IPv4.Config.Manual[0].Address if interface.IPv4.Config.Manual else "DHCP"
                    }
                    camera_data["network_config"].append(interface_data)
            except Exception as e:
                print(f"Erro ao obter informações de rede: {str(e)}")

            # Obter perfis de vídeo e os links RTSP correspondentes via ONVIF
            try:
                media_service = cam.create_media_service()
                profiles = media_service.GetProfiles()

                for profile in profiles:
                    if profile.VideoEncoderConfiguration:
                        res = profile.VideoEncoderConfiguration.Resolution
                        profile_data = {
                            "perfil": profile.Name,
                            "resolucao": f"{res.Width}x{res.Height}",
                            "fps": profile.VideoEncoderConfiguration.RateControl.FrameRateLimit,
                            "rtsp": ""
                        }
                        try:
                            stream_uri = media_service.GetStreamUri({
                                'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}},
                                'ProfileToken': profile.token
                            })
                            profile_data["rtsp"] = stream_uri.Uri
                            
                            # Testar o stream RTSP
                            rtsp_ok = testar_stream_opencv(stream_uri.Uri)
                            profile_data["rtsp_test"] = "Sucesso" if rtsp_ok else "Falha"
                        except Exception as e:
                            print(f"Erro ao obter URI RTSP: {str(e)}")
                            profile_data["rtsp"] = "Erro ao obter RTSP via ONVIF"

                        camera_data["video_profiles"].append(profile_data)
            except Exception as e:
                print(f"Erro ao obter perfis de vídeo: {str(e)}")

            # Testar PTZ se disponível
            if camera_data["onvif_services"].get("ptz") == "Disponível":
                print("\n=== Testando PTZ ===")
                try:
                    ptz_service = cam.create_ptz_service()
                    profile_token = profiles[0].token  # Usa o primeiro perfil de vídeo

                    mover_camera(ptz_service, profile_token, pan=1)  # Mover para a direita
                    mover_camera(ptz_service, profile_token, pan=-1)  # Mover para a esquerda
                    mover_camera(ptz_service, profile_token, tilt=1)  # Mover para cima
                    mover_camera(ptz_service, profile_token, tilt=-1)  # Mover para baixo
                    mover_camera(ptz_service, profile_token, zoom=1)  # Zoom in
                    mover_camera(ptz_service, profile_token, zoom=-1)  # Zoom out

                    camera_data["ptz_status"] = "Movimentos testados"
                except Exception as e:
                    print(f"Erro ao testar PTZ: {str(e)}")
                    camera_data["ptz_status"] = f"Erro: {str(e)}"

        except Exception as e:
            print(f"⚠ Erro ao obter informações da câmera: {str(e)}")
    else:
        print("\n⚠ Não foi possível conectar à câmera ONVIF após várias tentativas.")
    
    # Testar URLs RTSP diretamente, mesmo se ONVIF falhar
    working_rtsp = testar_urls_rtsp()
    if working_rtsp:
        camera_data["working_rtsp_url"] = working_rtsp

# Executar o script e imprimir JSON formatado
if __name__ == "__main__":
    print("\n=== Iniciando diagnóstico de câmera ONVIF ===")
    print(f"Câmera IP: {CAMERA_IP}")
    print(f"Portas: HTTP={HTTP_PORT}, RTSP={RTSP_PORT}, HTTPS={HTTPS_PORT}, Server={SERVER_PORT}")
    print(f"Usuário: {CAMERA_USER}")
    print(f"Senha: {'*' * len(CAMERA_PASS)}")
    
    obter_informacoes_camera()
    
    print("\n=== JSON Gerado ===")
    print(json.dumps(camera_data, indent=4, ensure_ascii=False))
    
    # Salvar resultado em arquivo
    try:
        with open(f"camera_info_{CAMERA_IP}.json", "w") as f:
            json.dump(camera_data, f, indent=4, ensure_ascii=False)
        print(f"\nResultados salvos em camera_info_{CAMERA_IP}.json")
    except Exception as e:
        print(f"Erro ao salvar arquivo: {str(e)}")
    
    # Resumo final
    print("\n=== Resumo do Diagnóstico ===")
    if camera_data.get("device_info"):
        print("✅ Conexão ONVIF bem-sucedida")
        print(f"Fabricante: {camera_data['device_info'].get('fabricante', 'N/A')}")
        print(f"Modelo: {camera_data['device_info'].get('modelo', 'N/A')}")
    else:
        print("❌ Conexão ONVIF falhou")
    
    if camera_data.get("working_rtsp_url"):
        print(f"✅ URL RTSP funcionando: {camera_data['working_rtsp_url']}")
    elif any(status == "Sucesso" for status in camera_data["rtsp_url_tests"].values()):
        working_urls = [url for url, status in camera_data["rtsp_url_tests"].items() if status == "Sucesso"]
        print(f"✅ URLs RTSP funcionando: {', '.join(working_urls)}")
    else:
        print("❌ Nenhuma URL RTSP funcionou")
