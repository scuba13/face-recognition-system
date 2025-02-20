import cv2
import time
import os
from datetime import datetime

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
    simple_camera_test() 