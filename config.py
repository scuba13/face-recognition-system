# Configuração das linhas de produção
PRODUCTION_LINES = {
    "linha_1": [
        {
            "type": "usb",
            "id": 0,  # Primeira câmera USB
            "name": "Webcam Principal",
            "resolution": (1280, 960),
            "fps": 5,
            "position": "entrada"
        },
        {
            "type": "usb",
            "id": 1,  # Segunda câmera USB
            "name": "Webcam Secundária",
            "resolution": (1280, 960),
            "fps": 5,
            "position": "saida"
        }
    ],
    # Linha 2 comentada para testes
    "linha_2": [
        {
            "type": "usb", 
            "id": 0,
            "name": "Webcam Principal",
            "resolution": (1280, 960),
            "fps": 5,
            "position": "entrada"
        },
        {
            "type": "usb",
            "id": 1,  # Segunda câmera USB
            "name": "Webcam Secundária",
            "resolution": (1280, 960),
            "fps": 5,
            "position": "saida"
        }
    ]
}

# Configurações gerais
CAPTURE_INTERVAL = 5  # intervalo entre capturas em segundos
DELETE_AFTER_PROCESS = True  # apagar imagens após processamento

# Configurações de MongoDB
MONGODB_URI = "mongodb://localhost:27017/"
MONGODB_TIMEOUT_MS = 5000
MONGODB_MAX_POOL_SIZE = 100
MONGODB_RETRY_WRITES = True
MONGODB_RETRY_READS = True

# Configurações de processamento
FACE_RECOGNITION_TOLERANCE = 0.6
BATCH_LOCK_TIMEOUT = 5
MIN_IMAGES_PER_BATCH = 3
MAX_PROCESSING_WORKERS = 4
BATCH_PROCESSING_TIMEOUT = 300
FACE_DETECTION_MODEL = "hog"

# Configurações de armazenamento
BASE_IMAGE_DIR = "captured_images"
BACKUP_FAILED_BATCHES = True
FAILED_BATCHES_DIR = "failed_batches"
EMPLOYEES_PHOTOS_DIR = "fotos"

# Configurações de monitoramento
ENABLE_METRICS = True
METRICS_INTERVAL = 60

# Configurações de validação de imagem
MIN_IMAGE_SIZE = 640    # Tamanho mínimo em pixels
MAX_IMAGE_SIZE = 4096   # Tamanho máximo em pixels
MIN_BLUR_THRESHOLD = 100  # Valor mínimo do Laplaciano para considerar imagem nítida

# Configurações de circuit breaker
CB_FAILURE_THRESHOLD = 5
CB_RESET_TIMEOUT = 60

# Configurações de câmeras IP (mantidas para referência futura)
IP_CAMERAS_CONFIG = {
    "retry_interval": 5,
    "connection_timeout": 10,
    "auth": {
        "default": {
            "username": "admin",
            "password": "admin123"
        }
    }
} 