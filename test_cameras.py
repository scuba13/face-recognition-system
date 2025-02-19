import cv2
import time
import logging
from modules.cameras import IPCamera

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cameras(max_cameras=10):
    """Testa todas as câmeras conectadas"""
    print("\n=== Testando Câmeras USB ===")
    available_cameras = []
    
    print("================================")
    
    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                height, width = frame.shape[:2]
                print(f"\n✓ Câmera USB {i}:")
                print(f"  - Status: Funcionando")
                print(f"  - Resolução: {width}x{height}")
                
                # Tentar obter mais informações da câmera
                fps = cap.get(cv2.CAP_PROP_FPS)
                brightness = cap.get(cv2.CAP_PROP_BRIGHTNESS)
                contrast = cap.get(cv2.CAP_PROP_CONTRAST)
                
                print(f"  - FPS: {fps:.1f}")
                print(f"  - Brilho: {brightness}")
                print(f"  - Contraste: {contrast}")
                
                available_cameras.append({
                    'type': 'usb',
                    'id': i,
                    'resolution': f"{width}x{height}",
                    'fps': fps,
                    'status': 'OK'
                })
            else:
                print(f"\n✗ Câmera USB {i}:")
                print(f"  - Status: Erro na captura")
                available_cameras.append({
                    'type': 'usb',
                    'id': i,
                    'status': 'Erro na captura'
                })
            cap.release()
        else:
            print(f"\n✗ Câmera USB {i} não disponível")
    
    print("\n=== Testando Câmeras IP ===")
    # Testar câmeras IP de exemplo
    test_ip_cameras = [
        "rtsp://192.168.1.100:554/stream1",
        "http://192.168.1.101:8080/video"
    ]
    
    for url in test_ip_cameras:
        try:
            camera = IPCamera(url)
            if camera.open():
                info = camera.get_info()
                print(f"\n✓ Câmera IP:")
                print(f"  - URL: {url}")
                print(f"  - Status: Conectada")
                print(f"  - Resolução: {info['resolution']}")
                print(f"  - FPS: {info['fps']}")
                
                available_cameras.append({
                    'type': 'ip',
                    'url': url,
                    'resolution': info['resolution'],
                    'fps': info['fps'],
                    'status': 'OK'
                })
            else:
                print(f"\n✗ Câmera IP:")
                print(f"  - URL: {url}")
                print(f"  - Status: Não conectada")
            camera.release()
        except Exception as e:
            print(f"\n✗ Erro ao testar câmera IP {url}: {str(e)}")
    
    print("\n================================")
    print(f"Total de câmeras encontradas: {len(available_cameras)}")
    return available_cameras

def preview_camera(camera_id, duration=5):
    """Mostra preview de uma câmera específica"""
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"Erro: Não foi possível acessar a câmera {camera_id}")
        return
    
    print(f"\nMostrando preview da câmera {camera_id}")
    print("Pressione 'Q' para sair")
    
    start_time = time.time()
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if ret:
            cv2.imshow(f'Camera {camera_id}', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Erro na captura do frame")
            break
    
    cap.release()
    cv2.destroyAllWindows()

def test_ip_camera(url):
    """Testa uma câmera IP específica"""
    camera = IPCamera(url)
    if not camera.open():
        print(f"Erro: Não foi possível conectar à câmera IP {url}")
        return
    
    print(f"\nMostrando preview da câmera IP")
    print("Pressione 'Q' para sair")
    
    start_time = time.time()
    while time.time() - start_time < 5:
        ret, frame = camera.read()
        if ret:
            cv2.imshow('Camera IP', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Erro na captura do frame")
            break
    
    camera.release()
    cv2.destroyAllWindows()

def main():
    while True:
        print("\n=== Menu de Teste de Câmeras ===")
        print("1. Listar câmeras disponíveis")
        print("2. Testar câmera USB específica")
        print("3. Testar câmera IP")
        print("0. Sair")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            test_cameras()
        elif opcao == "2":
            camera_id = int(input("Digite o ID da câmera USB: "))
            preview_camera(camera_id)
        elif opcao == "3":
            url = input("Digite a URL da câmera IP: ")
            test_ip_camera(url)
        elif opcao == "0":
            break
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    main() 