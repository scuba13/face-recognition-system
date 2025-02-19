import cv2
import time
import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

class BaseCamera(ABC):
    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def release(self):
        pass

    @abstractmethod
    def is_opened(self):
        pass

    @abstractmethod
    def get_info(self):
        pass

class USBCamera(BaseCamera):
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.cap = None

    def open(self):
        self.cap = cv2.VideoCapture(self.camera_id)
        return self.cap.isOpened()

    def read(self):
        if self.cap:
            return self.cap.read()
        return False, None

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def get_info(self):
        if not self.is_opened():
            return {"status": "Não conectada"}
        
        info = {
            "type": "USB",
            "id": self.camera_id,
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "resolution": f"{int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
        }
        return info

class IPCamera(BaseCamera):
    def __init__(self, url, auth=None, retry_interval=5, connection_timeout=10):
        self.url = url
        self.auth = auth
        self.retry_interval = retry_interval
        self.connection_timeout = connection_timeout
        self.cap = None
        self.last_retry = 0

    def open(self):
        try:
            # Testar conexão primeiro (para URLs HTTP)
            if self.url.startswith('http'):
                response = requests.get(self.url, timeout=self.connection_timeout, 
                                     auth=self.auth if self.auth else None)
                if response.status_code != 200:
                    raise Exception(f"Erro de conexão: {response.status_code}")

            self.cap = cv2.VideoCapture(self.url)
            if not self.cap.isOpened():
                raise Exception("Não foi possível abrir o stream")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar à câmera IP {self.url}: {str(e)}")
            return False

    def read(self):
        if not self.is_opened():
            current_time = time.time()
            if current_time - self.last_retry > self.retry_interval:
                self.last_retry = current_time
                if self.open():
                    return self.cap.read()
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def get_info(self):
        if not self.is_opened():
            return {"status": "Não conectada"}
        
        parsed_url = urlparse(self.url)
        info = {
            "type": "IP",
            "url": f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}",
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "resolution": f"{int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
        }
        return info

def create_camera(camera_config):
    """Factory para criar câmera baseado na configuração"""
    if camera_config["type"] == "usb":
        return USBCamera(camera_config["id"])
    elif camera_config["type"] == "ip":
        return IPCamera(
            url=camera_config["url"],
            auth=camera_config.get("auth"),
            retry_interval=camera_config.get("retry_interval", 5),
            connection_timeout=camera_config.get("connection_timeout", 10)
        )
    else:
        raise ValueError(f"Tipo de câmera não suportado: {camera_config['type']}") 