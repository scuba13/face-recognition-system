import cv2
import time
import logging
import numpy as np
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

def test_usb_camera(camera_id, test_duration=5):
    """Testa uma câmera USB específica de forma detalhada"""
    print(f"\nTestando câmera USB {camera_id}...")
    
    # Tentar abrir a câmera
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"❌ Câmera USB {camera_id} não pôde ser aberta")
        return False
        
    try:
        # Testar captura de frames
        frames_captured = 0
        frames_failed = 0
        start_time = time.time()
        
        while time.time() - start_time < test_duration:
            ret, frame = cap.read()
            if ret:
                frames_captured += 1
                
                # Mostrar frame
                cv2.imshow(f'Camera {camera_id} Test', frame)
                cv2.waitKey(1)
                
                # Análise do frame
                if frames_captured == 1:
                    height, width = frame.shape[:2]
                    print(f"\n✓ Câmera USB {camera_id}:")
                    print(f"  - Status: Funcionando")
                    print(f"  - Resolução: {width}x{height}")
                    print(f"  - FPS: {cap.get(cv2.CAP_PROP_FPS):.1f}")
                    print(f"  - Brilho: {cap.get(cv2.CAP_PROP_BRIGHTNESS)}")
                    print(f"  - Contraste: {cap.get(cv2.CAP_PROP_CONTRAST)}")
                    
                    # Verificar qualidade da imagem
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
                    print(f"  - Nitidez (Laplacian): {blur:.2f}")
                    
                    # Salvar frame de teste
                    test_file = f"camera_{camera_id}_test.jpg"
                    cv2.imwrite(test_file, frame)
                    print(f"  - Frame de teste salvo: {test_file}")
            else:
                frames_failed += 1
            
            time.sleep(0.1)  # Pequena pausa para não sobrecarregar
            
        # Calcular FPS real
        actual_fps = frames_captured / test_duration
        print(f"\nResultados do teste ({test_duration}s):")
        print(f"  - Frames capturados: {frames_captured}")
        print(f"  - Frames falhos: {frames_failed}")
        print(f"  - FPS real: {actual_fps:.1f}")
        
        return frames_captured > 0
        
    except Exception as e:
        print(f"❌ Erro durante teste: {str(e)}")
        return False
        
    finally:
        cap.release()
        cv2.destroyAllWindows()

def main():
    print("\n=== Teste de Câmeras USB ===")
    
    # Testar câmeras de 0 a 3
    for camera_id in range(4):
        if test_usb_camera(camera_id):
            print(f"\n✓ Câmera {camera_id} está funcionando")
            
            # Perguntar se quer testar mais
            resp = input(f"\nTestar próxima câmera? (s/n): ")
            if resp.lower() != 's':
                break
        else:
            print(f"\n❌ Câmera {camera_id} não está disponível")

if __name__ == "__main__":
    main() 