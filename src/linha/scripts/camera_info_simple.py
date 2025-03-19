import cv2
import time
import json
import requests
from onvif import ONVIFCamera
import logging
import os
import subprocess
import re
import socket

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração da câmera (credenciais conhecidas)
CAMERA_IP = "192.168.0.130"
CAMERA_USER = "admin"
CAMERA_PASS = "admin123456"

# Portas específicas da câmera
ONVIF_PORT = 6688  # Porta ONVIF confirmada
RTSP_PORT = 8554   # Porta RTSP confirmada
HTTP_PORT = 80
HTTPS_PORT = 443

# Perfis RTSP conhecidos
RTSP_PROFILES = [
    "profile0",  # 1920x1080 @ 16fps
    "profile1",  # 640x360 @ 16fps
    "profile2",  # 640x360 @ 5fps
]

def obter_mac_via_arp(ip):
    """Tenta obter o endereço MAC usando a tabela ARP do sistema."""
    print(f"\n=== Tentando obter MAC via tabela ARP para {ip} ===")
    try:
        # Primeiro, garantir que o dispositivo está na tabela ARP
        socket.setdefaulttimeout(1)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, HTTP_PORT))
        s.close()
        
        # Em sistemas Unix/Linux/macOS
        result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True)
        output = result.stdout
        
        # Procurar por padrão de MAC address (xx:xx:xx:xx:xx:xx)
        mac_matches = re.search(r'(([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))', output)
        
        if mac_matches:
            mac = mac_matches.group(1)
            print(f"✅ MAC encontrado via ARP: {mac}")
            return mac
        else:
            print("❌ MAC não encontrado via ARP")
            return None
    except Exception as e:
        print(f"Erro ao obter MAC via ARP: {str(e)}")
        return None

def obter_mac_via_http(ip, usuario, senha):
    """Tenta obter o endereço MAC através de requisições HTTP diretas à câmera."""
    print(f"\n=== Tentando obter MAC via HTTP para {ip} ===")
    
    # URLs comuns para páginas de status/configuração de câmeras
    urls = [
        f"http://{ip}/status",
        f"http://{ip}/info",
        f"http://{ip}/network",
        f"http://{ip}/config",
        f"http://{ip}/settings",
        f"http://{ip}/system",
        f"http://{ip}/device_info",
        f"http://{ip}/api/system/info",
        f"http://{ip}/api/network/info",
        f"http://{ip}/cgi-bin/status",
        f"http://{ip}/cgi-bin/network"
    ]
    
    auth = (usuario, senha)
    
    for url in urls:
        try:
            print(f"Tentando URL: {url}")
            response = requests.get(url, auth=auth, timeout=5)
            
            if response.status_code == 200:
                # Procurar por padrões de MAC address no conteúdo
                content = response.text
                mac_matches = re.search(r'(([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))', content)
                
                if mac_matches:
                    mac = mac_matches.group(1)
                    print(f"✅ MAC encontrado via HTTP: {mac}")
                    return mac
                
                # Tentar encontrar em formato JSON
                try:
                    json_data = response.json()
                    # Procurar campos comuns que podem conter MAC
                    for field in ['mac', 'macAddress', 'mac_address', 'hwAddress', 'hw_address']:
                        if field in json_data:
                            mac = json_data[field]
                            print(f"✅ MAC encontrado via HTTP (JSON): {mac}")
                            return mac
                except:
                    pass
                
                # Tentar encontrar em formato XML
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(content)
                    # Procurar elementos que podem conter MAC
                    for elem in root.iter():
                        if 'mac' in elem.tag.lower():
                            mac = elem.text
                            print(f"✅ MAC encontrado via HTTP (XML): {mac}")
                            return mac
                except:
                    pass
        except Exception as e:
            print(f"Erro ao acessar {url}: {str(e)}")
    
    print("❌ MAC não encontrado via HTTP")
    return None

def obter_mac_via_onvif_detalhado(cam):
    """Tenta obter o endereço MAC via ONVIF com análise detalhada."""
    print("\n=== Tentando obter MAC via ONVIF (análise detalhada) ===")
    try:
        # Obter informações de rede
        devicemgmt = cam.create_devicemgmt_service()
        network_interfaces = devicemgmt.GetNetworkInterfaces()
        
        for interface in network_interfaces:
            # Imprimir todos os atributos disponíveis para debug
            print(f"Interface: {interface.token}")
            
            # Tentar diferentes caminhos para o MAC
            if hasattr(interface, 'Info'):
                if hasattr(interface.Info, 'HwAddress'):
                    mac = interface.Info.HwAddress
                    if mac:
                        print(f"✅ MAC encontrado via ONVIF (Info.HwAddress): {mac}")
                        return mac
                
                # Imprimir todos os atributos de Info
                print("Atributos de Info:")
                for attr in dir(interface.Info):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(interface.Info, attr)
                            print(f"  {attr}: {value}")
                        except:
                            pass
            
            # Tentar acessar o XML bruto
            if hasattr(interface, '_value_1'):
                xml_str = interface._value_1
                print(f"XML bruto: {xml_str}")
                
                # Procurar por padrões de MAC address
                mac_matches = re.search(r'(([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))', str(xml_str))
                if mac_matches:
                    mac = mac_matches.group(1)
                    print(f"✅ MAC encontrado via ONVIF (XML bruto): {mac}")
                    return mac
        
        print("❌ MAC não encontrado via ONVIF detalhado")
        return None
    except Exception as e:
        print(f"Erro ao obter MAC via ONVIF detalhado: {str(e)}")
        return None

def obter_informacoes_camera():
    """Obtém informações detalhadas da câmera usando as configurações conhecidas."""
    camera_data = {
        "device_info": {},
        "network_info": {},
        "video_profiles": [],
        "rtsp_urls": {},
        "onvif_services": {},
        "ptz_status": "Indisponível",
        "eventos": {},
        "mac_addresses": {}
    }
    
    # Testar conexão HTTP
    try:
        print(f"\n=== Testando conexão HTTP com a câmera ===")
        url = f"http://{CAMERA_IP}"
        response = requests.get(url, timeout=5)
        print(f"Resposta HTTP: {response.status_code}")
        camera_data["http_status"] = response.status_code
    except Exception as e:
        print(f"Erro ao conectar via HTTP: {str(e)}")
        camera_data["http_status"] = "Erro"
    
    # Testar conexão HTTPS
    try:
        print(f"\n=== Testando conexão HTTPS com a câmera ===")
        url = f"https://{CAMERA_IP}:{HTTPS_PORT}"
        response = requests.get(url, timeout=5, verify=False)
        print(f"Resposta HTTPS: {response.status_code}")
        camera_data["https_status"] = response.status_code
    except Exception as e:
        print(f"Erro ao conectar via HTTPS: {str(e)}")
        camera_data["https_status"] = "Erro"
    
    # Conectar via ONVIF na porta conhecida
    print(f"\n=== Conectando à câmera ONVIF em {CAMERA_IP}:{ONVIF_PORT} ===")
    try:
        cam = ONVIFCamera(CAMERA_IP, ONVIF_PORT, CAMERA_USER, CAMERA_PASS)
        
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
        
        print(f"Informações do dispositivo:")
        print(f"Fabricante: {info.Manufacturer}")
        print(f"Modelo: {info.Model}")
        print(f"Firmware: {info.FirmwareVersion}")
        print(f"Hardware ID: {info.HardwareId}")
        print(f"Serial: {info.SerialNumber}")
        
        # Obter informações de rede (IP e MAC)
        print(f"\n=== Obtendo informações de rede ===")
        try:
            network_service = cam.create_devicemgmt_service()
            network_interfaces = network_service.GetNetworkInterfaces()
            
            camera_data["network_info"]["interfaces"] = []
            
            for interface in network_interfaces:
                interface_data = {
                    "nome": interface.token,
                    "mac": interface.Info.HardwareAddress if hasattr(interface.Info, 'HardwareAddress') else "N/A",
                    "habilitado": "Sim" if interface.Enabled else "Não",
                    "dhcp": "Sim" if hasattr(interface, 'IPv4') and interface.IPv4.Config.DHCP else "Não"
                }
                
                # Obter endereço IP
                if hasattr(interface, 'IPv4'):
                    if hasattr(interface.IPv4, 'Config') and hasattr(interface.IPv4.Config, 'Manual') and interface.IPv4.Config.Manual:
                        for ip_config in interface.IPv4.Config.Manual:
                            interface_data["ip"] = ip_config.Address
                            interface_data["mascara"] = ip_config.PrefixLength
                    elif hasattr(interface.IPv4, 'Config') and hasattr(interface.IPv4.Config, 'FromDHCP') and interface.IPv4.Config.FromDHCP:
                        interface_data["ip"] = interface.IPv4.Config.FromDHCP.Address
                        interface_data["mascara"] = interface.IPv4.Config.FromDHCP.PrefixLength
                
                camera_data["network_info"]["interfaces"].append(interface_data)
                
                print(f"Interface: {interface.token}")
                print(f"  MAC: {interface_data.get('mac', 'N/A')}")
                print(f"  IP: {interface_data.get('ip', 'N/A')}")
                print(f"  Máscara: {interface_data.get('mascara', 'N/A')}")
                print(f"  DHCP: {interface_data.get('dhcp', 'N/A')}")
        except Exception as e:
            print(f"Erro ao obter informações de rede: {str(e)}")
        
        # Testar serviços ONVIF disponíveis
        servicos = {
            "device": cam.create_devicemgmt_service,
            "media": cam.create_media_service,
            "ptz": cam.create_ptz_service,
            "imaging": cam.create_imaging_service,
            "events": cam.create_events_service
        }
        
        print(f"\n=== Testando serviços ONVIF ===")
        for nome, func in servicos.items():
            try:
                service = func()
                if service:
                    camera_data["onvif_services"][nome] = "Disponível"
                    print(f"✅ Serviço {nome}: Disponível")
            except Exception as e:
                camera_data["onvif_services"][nome] = "Indisponível"
                print(f"❌ Serviço {nome}: Indisponível - {str(e)}")
        
        # Obter perfis de vídeo
        if camera_data["onvif_services"].get("media") == "Disponível":
            media_service = cam.create_media_service()
            profiles = media_service.GetProfiles()
            
            print(f"\n=== Perfis de vídeo ===")
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
                        print(f"Perfil: {profile.Name} - {res.Width}x{res.Height} @ {profile_data['fps']}fps")
                        print(f"RTSP URI: {stream_uri.Uri}")
                    except Exception as e:
                        print(f"Erro ao obter URI RTSP para {profile.Name}: {str(e)}")
                    
                    camera_data["video_profiles"].append(profile_data)
        
        # Testar URLs RTSP
        print(f"\n=== Testando URLs RTSP ===")
        for profile in RTSP_PROFILES:
            rtsp_url = f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}:{RTSP_PORT}/{profile}"
            print(f"Testando: {rtsp_url}")
            
            try:
                cap = cv2.VideoCapture(rtsp_url)
                time.sleep(2)  # Dar tempo para conectar
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Salvar um frame como amostra
                        filename = f"camera_frame_{profile}.jpg"
                        cv2.imwrite(filename, frame)
                        camera_data["rtsp_urls"][profile] = "Sucesso"
                        print(f"✅ URL funcionando: {rtsp_url}")
                        print(f"Frame salvo em {filename}")
                    else:
                        camera_data["rtsp_urls"][profile] = "Falha (stream aberto mas sem frame)"
                        print(f"⚠️ Stream aberto mas não conseguiu ler frame: {rtsp_url}")
                else:
                    camera_data["rtsp_urls"][profile] = "Falha"
                    print(f"❌ Falha ao abrir stream: {rtsp_url}")
                
                cap.release()
            except Exception as e:
                camera_data["rtsp_urls"][profile] = f"Erro: {str(e)}"
                print(f"❌ Erro ao testar stream RTSP {rtsp_url}: {str(e)}")
        
        # Testar PTZ se disponível
        if camera_data["onvif_services"].get("ptz") == "Disponível":
            print(f"\n=== Testando capacidades PTZ ===")
            try:
                ptz_service = cam.create_ptz_service()
                
                # Obter status atual
                status = ptz_service.GetStatus({'ProfileToken': profiles[0].token})
                print(f"Status PTZ atual: {status}")
                
                # Verificar se a câmera suporta movimento absoluto
                if hasattr(status, 'Position') and hasattr(status.Position, 'PanTilt'):
                    print(f"✅ Câmera suporta movimento PTZ absoluto")
                    camera_data["ptz_status"] = "Suporta movimento absoluto"
                    
                    # Obter presets
                    try:
                        presets = ptz_service.GetPresets({'ProfileToken': profiles[0].token})
                        camera_data["ptz_presets"] = []
                        
                        print(f"\n=== Presets PTZ ===")
                        for preset in presets:
                            print(f"Preset: {preset.Name} (Token: {preset.token})")
                            camera_data["ptz_presets"].append({
                                "nome": preset.Name,
                                "token": preset.token
                            })
                    except Exception as e:
                        print(f"Erro ao obter presets: {str(e)}")
                else:
                    print(f"❌ Câmera não suporta movimento PTZ absoluto")
                    camera_data["ptz_status"] = "Não suporta movimento absoluto"
            except Exception as e:
                print(f"Erro ao testar PTZ: {str(e)}")
                camera_data["ptz_status"] = f"Erro: {str(e)}"
        
        # Testar eventos ONVIF
        if camera_data["onvif_services"].get("events") == "Disponível":
            print(f"\n=== Testando eventos ONVIF ===")
            try:
                events_service = cam.create_events_service()
                
                # Obter propriedades do serviço de eventos
                service_capabilities = events_service.GetServiceCapabilities()
                camera_data["eventos"]["capacidades"] = {
                    "WSSubscriptionPolicySupport": service_capabilities.WSSubscriptionPolicySupport if hasattr(service_capabilities, 'WSSubscriptionPolicySupport') else False,
                    "WSPullPointSupport": service_capabilities.WSPullPointSupport if hasattr(service_capabilities, 'WSPullPointSupport') else False,
                    "WSPausableSubscriptionManagerInterfaceSupport": service_capabilities.WSPausableSubscriptionManagerInterfaceSupport if hasattr(service_capabilities, 'WSPausableSubscriptionManagerInterfaceSupport') else False,
                    "MaxNotificationProducers": service_capabilities.MaxNotificationProducers if hasattr(service_capabilities, 'MaxNotificationProducers') else 0,
                    "MaxPullPoints": service_capabilities.MaxPullPoints if hasattr(service_capabilities, 'MaxPullPoints') else 0
                }
                
                print(f"Capacidades de eventos:")
                for cap, value in camera_data["eventos"]["capacidades"].items():
                    print(f"  {cap}: {value}")
                
                # Tentar obter tópicos de eventos
                try:
                    topics = events_service.GetEventProperties()
                    camera_data["eventos"]["topicos"] = []
                    
                    if hasattr(topics, 'TopicNamespaceLocation'):
                        print(f"Namespace de tópicos: {topics.TopicNamespaceLocation}")
                    
                    if hasattr(topics, 'TopicSet') and hasattr(topics.TopicSet, '_value_1'):
                        # Extrair tópicos de eventos
                        topic_set = topics.TopicSet._value_1
                        
                        # Função recursiva para extrair tópicos
                        def extract_topics(node, path=""):
                            topics_list = []
                            
                            if hasattr(node, 'tag') and node.tag:
                                current_path = f"{path}/{node.tag.split('}')[-1]}" if path else node.tag.split('}')[-1]
                                topics_list.append(current_path)
                                
                                print(f"  Tópico: {current_path}")
                                
                                # Processar filhos
                                if hasattr(node, '_children'):
                                    for child in node._children:
                                        topics_list.extend(extract_topics(child, current_path))
                            
                            return topics_list
                        
                        camera_data["eventos"]["topicos"] = extract_topics(topic_set)
                        
                        print(f"Total de tópicos encontrados: {len(camera_data['eventos']['topicos'])}")
                except Exception as e:
                    print(f"Erro ao obter tópicos de eventos: {str(e)}")
                    
                # Tentar criar uma assinatura de eventos (PullPoint)
                if camera_data["eventos"]["capacidades"].get("WSPullPointSupport", False):
                    try:
                        print(f"Testando criação de PullPoint para eventos...")
                        
                        # Criar filtro para todos os eventos
                        filter_xml = """
                        <wsnt:TopicExpression xmlns:wsnt="http://docs.oasis-open.org/wsn/b-2" 
                                             xmlns:tns1="http://www.onvif.org/ver10/topics" 
                                             Dialect="http://www.onvif.org/ver10/tev/topicExpression/ConcreteSet">
                            tns1:RuleEngine//
                        </wsnt:TopicExpression>
                        """
                        
                        # Criar assinatura
                        pullpoint = events_service.CreatePullPointSubscription({
                            'InitialTerminationTime': 'PT10S',  # 10 segundos
                            'Filter': {'TopicExpression': filter_xml}
                        })
                        
                        if pullpoint and hasattr(pullpoint, 'SubscriptionReference'):
                            print(f"✅ Assinatura de eventos criada com sucesso")
                            camera_data["eventos"]["pullpoint_test"] = "Sucesso"
                        else:
                            print(f"❌ Falha ao criar assinatura de eventos")
                            camera_data["eventos"]["pullpoint_test"] = "Falha"
                    except Exception as e:
                        print(f"Erro ao criar assinatura de eventos: {str(e)}")
                        camera_data["eventos"]["pullpoint_test"] = f"Erro: {str(e)}"
            except Exception as e:
                print(f"Erro ao testar eventos: {str(e)}")
                camera_data["eventos"]["status"] = f"Erro: {str(e)}"
        
        # Tentar obter MAC por métodos alternativos
        print("\n=== Tentando obter MAC por métodos alternativos ===")
        
        # Método 1: Tentar via ONVIF detalhado
        mac_onvif = obter_mac_via_onvif_detalhado(cam)
        if mac_onvif:
            camera_data["mac_addresses"]["onvif_detalhado"] = mac_onvif
        
        # Método 2: Tentar via ARP
        mac_arp = obter_mac_via_arp(CAMERA_IP)
        if mac_arp:
            camera_data["mac_addresses"]["arp"] = mac_arp
        
        # Método 3: Tentar via HTTP
        mac_http = obter_mac_via_http(CAMERA_IP, CAMERA_USER, CAMERA_PASS)
        if mac_http:
            camera_data["mac_addresses"]["http"] = mac_http
        
        # Resumo dos MACs encontrados
        if camera_data["mac_addresses"]:
            print("\n=== MACs encontrados ===")
            for metodo, mac in camera_data["mac_addresses"].items():
                print(f"  Via {metodo}: {mac}")
            
            # Verificar se todos os MACs encontrados são iguais
            macs = list(camera_data["mac_addresses"].values())
            if len(macs) > 1 and all(mac == macs[0] for mac in macs):
                print(f"\n✅ MAC confirmado: {macs[0]}")
                camera_data["mac_address_confirmado"] = macs[0]
            elif len(macs) == 1:
                print(f"\n✅ MAC encontrado: {macs[0]}")
                camera_data["mac_address_confirmado"] = macs[0]
            else:
                print("\n⚠️ Diferentes MACs encontrados. Verificar qual é o correto.")
        else:
            print("❌ Nenhum endereço MAC encontrado por nenhum método.")
    
    except Exception as e:
        print(f"❌ Erro ao conectar via ONVIF: {str(e)}")
    
    return camera_data

if __name__ == "__main__":
    print("\n=== Iniciando diagnóstico simplificado de câmera ===")
    print(f"Câmera IP: {CAMERA_IP}")
    print(f"Portas: ONVIF={ONVIF_PORT}, RTSP={RTSP_PORT}, HTTP={HTTP_PORT}, HTTPS={HTTPS_PORT}")
    print(f"Usuário: {CAMERA_USER}")
    print(f"Senha: {'*' * len(CAMERA_PASS)}")
    
    camera_data = obter_informacoes_camera()
    
    # Salvar resultado em arquivo
    try:
        filename = f"camera_info_simple_{CAMERA_IP}.json"
        with open(filename, "w") as f:
            json.dump(camera_data, f, indent=4, ensure_ascii=False)
        print(f"\nResultados salvos em {filename}")
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
    
    # Resumo de rede
    if camera_data.get("network_info") and camera_data["network_info"].get("interfaces"):
        for interface in camera_data["network_info"]["interfaces"]:
            print(f"Interface: {interface.get('nome', 'N/A')}")
            print(f"  MAC: {interface.get('mac', 'N/A')}")
            print(f"  IP: {interface.get('ip', 'N/A')}")
    
    # Resumo MAC
    if camera_data.get("mac_address_confirmado"):
        print(f"✅ MAC confirmado: {camera_data['mac_address_confirmado']}")
    elif camera_data.get("mac_addresses"):
        print("⚠️ MACs encontrados (verificar qual é o correto):")
        for metodo, mac in camera_data["mac_addresses"].items():
            print(f"  Via {metodo}: {mac}")
    else:
        print("❌ Nenhum MAC encontrado")
    
    # Resumo RTSP
    working_urls = [profile for profile, status in camera_data.get("rtsp_urls", {}).items() if status == "Sucesso"]
    if working_urls:
        print(f"✅ URLs RTSP funcionando: {', '.join(working_urls)}")
    else:
        print("❌ Nenhuma URL RTSP funcionou")
    
    # Resumo PTZ
    print(f"Status PTZ: {camera_data.get('ptz_status', 'Desconhecido')}")
    
    # Resumo Eventos
    if camera_data.get("eventos") and camera_data["eventos"].get("topicos"):
        print(f"✅ Eventos ONVIF: {len(camera_data['eventos']['topicos'])} tópicos disponíveis")
    else:
        print("❌ Nenhum tópico de evento encontrado") 