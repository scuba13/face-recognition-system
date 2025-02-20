# Configuração das linhas de produção
PRODUCTION_LINES = {
    "linha_1": [
        {
            "type": "usb",
            "id": 0,  # Câmera USB detectada
            "name": "Webcam Principal",
            "resolution": (1280, 960),
            "fps": 5
        }
    ],
    "linha_2": [
        {
            "type": "usb",
            "id": 0,  # Mesma câmera USB
            "name": "Webcam Principal",
            "resolution": (1280, 960),
            "fps": 5
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

# Configurações de armazenamento (caminhos locais)
BASE_IMAGE_DIR = "captured_images"  # Pasta local
BACKUP_FAILED_BATCHES = True
FAILED_BATCHES_DIR = "failed_batches"  # Pasta local
EMPLOYEES_PHOTOS_DIR = "fotos"  # Pasta local

# Configurações de monitoramento
ENABLE_METRICS = True
METRICS_INTERVAL = 60

# Configurações de validação de imagem
MIN_IMAGE_SIZE = 640
MAX_IMAGE_SIZE = 4096
MIN_BLUR_THRESHOLD = 100

# Configurações de circuit breaker
CB_FAILURE_THRESHOLD = 5
CB_RESET_TIMEOUT = 60

# Configurações de câmeras IP
IP_CAMERAS_CONFIG = {
    "retry_interval": 5,  # segundos entre tentativas de reconexão
    "connection_timeout": 10,  # timeout para conexão
    "auth": {
        "default": {
            "username": "admin",
            "password": "admin123"
        },
        # Configurações específicas por câmera
        "linha_1_camera_ip_1": {
            "username": "admin",
            "password": "senha123"
        },
        "linha_1_camera_ip_2": {
            "username": "admin",
            "password": "senha456"
        },
        "linha_2_camera_ip_1": {
            "username": "admin",
            "password": "senha789"
        },
        "linha_2_camera_ip_2": {
            "username": "admin",
            "password": "senha012"
        }
    }
} 