import os
from dotenv import load_dotenv

load_dotenv()

# Configurações de produção
PRODUCTION_LINES = {
    "linha_1": [
        {
            "type": "usb",
            "id": 0,
            "name": "Webcam Principal",
            "resolution": (1280, 960),
            "position": "entrada"
        },
        # {
        #     "type": "usb",
        #     "id": 1,
        #     "name": "Webcam Secundária",
        #     "resolution": (1280, 720),
        #     "position": "saida"
        # }
    ],
    # "linha_2": [
    #     {
    #         "type": "usb",
    #         "id": 0,
    #         "name": "Webcam Principal",
    #         "resolution": (1280, 960),
    #         "position": "entrada"
    #     },
    #     {
    #         "type": "usb",
    #         "id": 1,
    #         "name": "Webcam Secundária",
    #         "resolution": (1280, 720),
    #         "position": "saida"
    #     }
    # ]
}

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
CAPTURE_INTERVAL = int(os.getenv('CAPTURE_INTERVAL', '5'))  # Intervalo em segundos entre capturas (12 imagens/minuto com valor 5)
FACE_RECOGNITION_TOLERANCE = float(os.getenv('FACE_RECOGNITION_TOLERANCE', '0.6'))
MIN_BLUR_THRESHOLD = float(os.getenv('MIN_BLUR_THRESHOLD', '100'))

# Face Detection
FACE_DETECTION_MODEL = "hog"  # ou "cnn" para GPU
ENABLE_PREPROCESSING = bool(os.getenv('ENABLE_PREPROCESSING', 'True'))  # Flag para controlar pré-processamento