import cv2
import time
import os
from datetime import datetime

def test_camera():
    print("Iniciando teste da câmera...")
    
    # Tentar diferentes índices de câmera
    for camera_id in [0, 1]:
        print(f"\nTestando câmera {camera_id}")
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            print(f"Não foi possível abrir câmera {camera_id}")
            continue
            
        # Tentar algumas capturas
        for i in range(5):
            ret, frame = cap.read()
            if ret:
                print(f"Frame {i+1} capturado com sucesso - Shape: {frame.shape}")
                # Salvar frame para verificar
                cv2.imwrite(f"test_frame_{camera_id}_{i}.jpg", frame)
            else:
                print(f"Falha ao capturar frame {i+1}")
            time.sleep(1)
            
        cap.release()
        
    print("\nTeste finalizado")

def simple_camera_test():
    print("Iniciando teste simples da câmera 0...")
    
    # Criar pasta para fotos se não existir
    os.makedirs("fotos_teste", exist_ok=True)
    
    # Abrir câmera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro: Não foi possível abrir a câmera 0")
        return
        
    print("\nControles:")
    print("- ESC: Sair")
    print("- ESPAÇO: Capturar foto")
    print("- R: Mostrar resolução e FPS")
    
    try:
        while True:
            # Capturar frame
            ret, frame = cap.read()
            if not ret:
                print("Erro ao capturar frame")
                break
                
            # Mostrar frame
            cv2.imshow('Camera Test (ESC para sair, ESPACO para foto)', frame)
            
            # Capturar tecla
            key = cv2.waitKey(1) & 0xFF
            
            # ESC para sair
            if key == 27:
                break
                
            # ESPAÇO para salvar foto
            elif key == 32:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"fotos_teste/foto_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Foto salva: {filename}")
                
            # R para mostrar info
            elif key == ord('r'):
                height, width = frame.shape[:2]
                fps = cap.get(cv2.CAP_PROP_FPS)
                print(f"\nInformações da câmera:")
                print(f"Resolução: {width}x{height}")
                print(f"FPS: {fps}")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\nTeste finalizado")

if __name__ == "__main__":
    test_camera()
    simple_camera_test() 