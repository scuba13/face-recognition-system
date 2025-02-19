# Configuração das linhas de produção
PRODUCTION_LINES = {
    "linha_1": [
        {"type": "usb", "id": 0},  # Câmera USB frontal
        {"type": "usb", "id": 1},  # Câmera USB lateral
        {"type": "ip", "url": "rtsp://192.168.1.100:554/stream1"},  # Câmera IP fixa
        {"type": "ip", "url": "http://192.168.1.101:8080/video"}  # Câmera IP móvel (celular)
    ],
    "linha_2": [
        {"type": "usb", "id": 2},  # Câmera USB frontal
        {"type": "usb", "id": 3},  # Câmera USB lateral
        {"type": "ip", "url": "rtsp://192.168.1.102:554/stream1"},  # Câmera IP fixa
        {"type": "ip", "url": "http://192.168.1.103:8080/video"}  # Câmera IP móvel (celular)
    ]
}

# Configurações gerais
CAPTURE_INTERVAL = 5  # intervalo entre capturas em segundos
DELETE_AFTER_PROCESS = True  # apagar imagens após processamento

# Configurações de MongoDB
MONGODB_URI = "mongodb://localhost:27017/"  # URI de conexão com o MongoDB
MONGODB_TIMEOUT_MS = 5000
MONGODB_MAX_POOL_SIZE = 100
MONGODB_RETRY_WRITES = True
MONGODB_RETRY_READS = True

# Configurações de processamento
FACE_RECOGNITION_TOLERANCE = 0.6  # Tolerância para reconhecimento facial (menor = mais restritivo)
BATCH_LOCK_TIMEOUT = 5  # Tempo em minutos para considerar um lock como expirado
MIN_IMAGES_PER_BATCH = 3
MAX_PROCESSING_WORKERS = 4
BATCH_PROCESSING_TIMEOUT = 300  # 5 minutos
FACE_DETECTION_MODEL = "hog"  # ou "cnn" para GPU

# Configurações de armazenamento
BASE_IMAGE_DIR = "/app/captured_images"  # Diretório base para armazenar imagens
BACKUP_FAILED_BATCHES = True
FAILED_BATCHES_DIR = "/app/failed_batches"
EMPLOYEES_PHOTOS_DIR = "/app/fotos"  # Novo: diretório para fotos dos funcionários

# Configurações de monitoramento
ENABLE_METRICS = True
METRICS_INTERVAL = 60  # segundos

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