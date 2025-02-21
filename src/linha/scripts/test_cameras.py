import cv2
import time
import logging
import numpy as np
from linha.utils.camera import init_camera
from linha.config.settings import PRODUCTION_LINES

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
            cap.release()
        else:
            print(f"\n✗ Câmera USB {i} não disponível")
    
    print("\n================================")
    print(f"Total de câmeras encontradas: {len(available_cameras)}")
    return available_cameras

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
    
    # Testar câmeras configuradas no settings.py
    for line_id, cameras in PRODUCTION_LINES.items():
        print(f"\nTestando câmeras da {line_id}")
        for camera in cameras:
            if camera['type'] == 'usb':
                test_usb_camera(camera['id'])

if __name__ == "__main__":
    main() 