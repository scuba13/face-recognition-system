import subprocess
import re
import socket
import requests
import time
import logging
import json
from pysnmp.hlapi import *
import nmap
import xml.etree.ElementTree as ET
from onvif import ONVIFCamera

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração da câmera
CAMERA_IP = "192.168.0.130"
CAMERA_USER = "admin"
CAMERA_PASS = "admin123456"
ONVIF_PORT = 6688
HTTP_PORT = 80

def obter_mac_via_arp():
    """Tenta obter o endereço MAC usando a tabela ARP do sistema."""
    print("\n=== Tentando obter MAC via tabela ARP ===")
    try:
        # Primeiro, garantir que o dispositivo está na tabela ARP
        socket.setdefaulttimeout(1)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((CAMERA_IP, HTTP_PORT))
        s.close()
        
        # Em sistemas Unix/Linux/macOS
        result = subprocess.run(['arp', '-n', CAMERA_IP], capture_output=True, text=True)
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

def obter_mac_via_nmap():
    """Tenta obter o endereço MAC usando nmap."""
    print("\n=== Tentando obter MAC via nmap ===")
    try:
        nm = nmap.PortScanner()
        nm.scan(hosts=CAMERA_IP, arguments='-sn')
        
        if CAMERA_IP in nm.all_hosts():
            if 'mac' in nm[CAMERA_IP]['addresses']:
                mac = nm[CAMERA_IP]['addresses']['mac']
                vendor = nm[CAMERA_IP]['vendor'].get(mac, "Desconhecido") if 'vendor' in nm[CAMERA_IP] else "Desconhecido"
                print(f"✅ MAC encontrado via nmap: {mac} (Fabricante: {vendor})")
                return mac
        
        print("❌ MAC não encontrado via nmap")
        return None
    except Exception as e:
        print(f"Erro ao obter MAC via nmap: {str(e)}")
        return None

def obter_mac_via_snmp():
    """Tenta obter o endereço MAC via SNMP."""
    print("\n=== Tentando obter MAC via SNMP ===")
    try:
        # OID para interfaces de rede
        interface_oid = '1.3.6.1.2.1.2.2.1.6'
        
        # Tentar community strings comuns
        community_strings = ['public', 'private', 'admin', 'camera']
        
        for community in community_strings:
            print(f"Tentando com community string: {community}")
            
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((CAMERA_IP, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(interface_oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                print(f"Erro SNMP: {errorIndication}")
                continue
            elif errorStatus:
                print(f"Erro SNMP: {errorStatus.prettyPrint()} em {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}")
                continue
            else:
                for varBind in varBinds:
                    if varBind[1].prettyPrint() != '':
                        mac_hex = varBind[1].prettyPrint()
                        # Converter formato hexadecimal para formato MAC
                        mac = ':'.join([mac_hex[i:i+2] for i in range(0, len(mac_hex), 2)])
                        print(f"✅ MAC encontrado via SNMP: {mac}")
                        return mac
        
        print("❌ MAC não encontrado via SNMP")
        return None
    except Exception as e:
        print(f"Erro ao obter MAC via SNMP: {str(e)}")
        return None

def obter_mac_via_http():
    """Tenta obter o endereço MAC através de requisições HTTP diretas à câmera."""
    print("\n=== Tentando obter MAC via HTTP ===")
    
    # URLs comuns para páginas de status/configuração de câmeras
    urls = [
        f"http://{CAMERA_IP}/status",
        f"http://{CAMERA_IP}/info",
        f"http://{CAMERA_IP}/network",
        f"http://{CAMERA_IP}/config",
        f"http://{CAMERA_IP}/settings",
        f"http://{CAMERA_IP}/system",
        f"http://{CAMERA_IP}/device_info",
        f"http://{CAMERA_IP}/api/system/info",
        f"http://{CAMERA_IP}/api/network/info",
        f"http://{CAMERA_IP}/cgi-bin/status",
        f"http://{CAMERA_IP}/cgi-bin/network"
    ]
    
    auth = (CAMERA_USER, CAMERA_PASS)
    
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

def obter_mac_via_onvif_detalhado():
    """Tenta obter o endereço MAC via ONVIF com análise detalhada."""
    print("\n=== Tentando obter MAC via ONVIF (análise detalhada) ===")
    try:
        cam = ONVIFCamera(CAMERA_IP, ONVIF_PORT, CAMERA_USER, CAMERA_PASS)
        
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

def main():
    """Função principal que tenta obter o MAC por diferentes métodos."""
    print(f"\n=== Iniciando busca por MAC da câmera {CAMERA_IP} ===")
    
    resultados = {}
    
    # Método 1: ARP
    mac_arp = obter_mac_via_arp()
    if mac_arp:
        resultados['arp'] = mac_arp
    
    # Método 2: nmap
    mac_nmap = obter_mac_via_nmap()
    if mac_nmap:
        resultados['nmap'] = mac_nmap
    
    # Método 3: SNMP
    mac_snmp = obter_mac_via_snmp()
    if mac_snmp:
        resultados['snmp'] = mac_snmp
    
    # Método 4: HTTP
    mac_http = obter_mac_via_http()
    if mac_http:
        resultados['http'] = mac_http
    
    # Método 5: ONVIF detalhado
    mac_onvif = obter_mac_via_onvif_detalhado()
    if mac_onvif:
        resultados['onvif'] = mac_onvif
    
    # Resumo dos resultados
    print("\n=== Resumo dos resultados ===")
    if resultados:
        print("Endereços MAC encontrados:")
        for metodo, mac in resultados.items():
            print(f"  Via {metodo}: {mac}")
        
        # Verificar se todos os MACs encontrados são iguais
        macs = list(resultados.values())
        if all(mac == macs[0] for mac in macs):
            print(f"\n✅ MAC confirmado: {macs[0]}")
        else:
            print("\n⚠️ Diferentes MACs encontrados. Verificar qual é o correto.")
    else:
        print("❌ Nenhum endereço MAC encontrado por nenhum método.")
    
    # Salvar resultados em arquivo
    try:
        with open(f"camera_mac_{CAMERA_IP}.json", "w") as f:
            json.dump(resultados, f, indent=4)
        print(f"\nResultados salvos em camera_mac_{CAMERA_IP}.json")
    except Exception as e:
        print(f"Erro ao salvar arquivo: {str(e)}")

if __name__ == "__main__":
    main() 