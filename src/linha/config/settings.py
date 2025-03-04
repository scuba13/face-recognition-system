import os
from dotenv import load_dotenv

load_dotenv()

# Configurações de produção
PRODUCTION_LINES = {
    "linha_1": [
        {
            "type": "ip",
            # "id": "rtsp://192.168.0.141:554/0/av0",
            # "id": "rtsp://192.168.0.141:554/0/av1", # Preview (640x360) - Útil para visualização em tempo real
            "id": "rtsp://192.168.0.141:554/stream", 
            "name": "Câmera IP Principal",
            # Usando resolução máxima para melhor detecção e reconhecimento facial
            # O sistema usa abordagem híbrida:
            # 1. Captura em alta resolução (2304x1296)
            # 2. Redimensiona para detecção rápida
            # 3. Processa faces detectadas em alta resolução
            "resolution": (2304, 1296),
            "position": "entrada",
            "rtsp_transport": "tcp"  # Protocolo de transporte RTSP (tcp ou udp)
        },
        # {
        #     "type": "ip",
        #     "id": "rtsp://192.168.0.134:554/0/av0",
        #     "name": "Câmera IP Secundária",
        #     "resolution": (1280, 720),
        #     "position": "saida"
        # }
    ],
    # "linha_2": [
    #     {
    #         "type": "ip",
    #         "id": "rtsp://192.168.0.135:554/0/av0",
    #         "name": "Câmera IP Principal",
    #         "resolution": (1280, 960),
    #         "position": "entrada"
    #     },
    #     {
    #         "type": "ip",
    #         "id": "rtsp://192.168.0.136:554/0/av0",
    #         "name": "Câmera IP Secundária",
    #         "resolution": (1280, 720),
    #         "position": "saida"
    #     }
    # ]
}

# Configurações alternativas para testes
# Descomente uma das opções abaixo para testar

# Opção 1: Usar webcam local como teste
# PRODUCTION_LINES = {
#     "linha_1": [
#         {
#             "type": "usb",
#             "id": 0,  # ID da webcam (geralmente 0 para a webcam padrão)
#             "name": "Webcam Local",
#             "resolution": (1280, 720),
#             "position": "entrada"
#         }
#     ]
# }

# Opção 2: Usar arquivo de vídeo local para testes
# PRODUCTION_LINES = {
#     "linha_1": [
#         {
#             "type": "video",
#             "id": "samples/test_video.mp4",  # Caminho para um arquivo de vídeo
#             "name": "Vídeo de Teste",
#             "resolution": (1280, 720),
#             "position": "entrada"
#         }
#     ]
# }

# Opção 3: Usar stream RTSP público para testes
# PRODUCTION_LINES = {
#     "linha_1": [
#         {
#             "type": "ip",
#             "id": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4",  # Stream RTSP público
#             "name": "Stream RTSP Público",
#             "resolution": (1280, 720),
#             "position": "entrada",
#             "rtsp_transport": "tcp"
#         }
#     ]
# }

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data')
BASE_IMAGE_DIR = os.path.join(DATA_DIR, 'captured_images')
FAILED_BATCHES_DIR = os.path.join(DATA_DIR, 'failed_batches')
EMPLOYEES_DIR = os.path.join(DATA_DIR, 'employees')

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB = os.getenv('MONGODB_DB', 'face_recognition_db')
MONGODB_TIMEOUT_MS = 5000
MONGODB_MAX_POOL_SIZE = 100
BATCH_LOCK_TIMEOUT = 300  # 5 minutos em segundos

# Configurações de captura
CAPTURE_INTERVAL = int(os.getenv('CAPTURE_INTERVAL', '5'))  # Intervalo em segundos entre capturas
FACE_RECOGNITION_TOLERANCE = float(os.getenv('FACE_RECOGNITION_TOLERANCE', '0.6'))
MIN_BLUR_THRESHOLD = float(os.getenv('MIN_BLUR_THRESHOLD', '100'))

# Configurações de detecção de movimento
MOTION_DETECTION_ENABLED = bool(os.getenv('MOTION_DETECTION_ENABLED', 'True'))
MOTION_THRESHOLD = float(os.getenv('MOTION_THRESHOLD', '20000'))  # Limiar para detecção de movimento
MOTION_MIN_AREA = float(os.getenv('MOTION_MIN_AREA', '500'))  # Área mínima para considerar movimento
MOTION_DRAW_CONTOURS = bool(os.getenv('MOTION_DRAW_CONTOURS', 'True'))  # Desenhar contornos nos frames
MOTION_CAPTURE_FRAMES = int(os.getenv('MOTION_CAPTURE_FRAMES', '5'))  # Número de frames a capturar quando detectar movimento
MOTION_CAPTURE_INTERVAL = float(os.getenv('MOTION_CAPTURE_INTERVAL', '0.1'))  # Intervalo entre frames em segundos (100ms)

# Tipo de captura: 'interval' (intervalo fixo) ou 'motion' (baseado em movimento)
CAPTURE_TYPE = os.getenv('CAPTURE_TYPE', 'interval')

# Face Detection
FACE_DETECTION_MODEL = "hog"  # ou "cnn" para GPU
ENABLE_PREPROCESSING = bool(os.getenv('ENABLE_PREPROCESSING', 'True'))  # Flag para controlar pré-processamento

# Configurações de processamento paralelo
FACE_PROCESSOR_MAX_WORKERS = int(os.getenv('FACE_PROCESSOR_MAX_WORKERS', '4'))  # Número de threads para processamento paralelo de imagens
CAPTURE_MAX_WORKERS = int(os.getenv('CAPTURE_MAX_WORKERS', '4'))  # Número de workers para processamento de captura
MOTION_DETECTION_MAX_WORKERS = int(os.getenv('MOTION_DETECTION_MAX_WORKERS', '4'))  # Número de workers para detecção de movimento

# Flags para habilitar/desabilitar componentes do sistema
ENABLE_CAPTURE = bool(os.getenv('ENABLE_CAPTURE', 'True'))  # Flag para habilitar/desabilitar a captura de imagens
ENABLE_PROCESSING = bool(os.getenv('ENABLE_PROCESSING', 'True'))  # Flag para habilitar/desabilitar o processamento de faces