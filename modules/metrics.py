import time
import psutil
import logging
from threading import Thread
from datetime import datetime
from config import METRICS_INTERVAL

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, db_handler):
        self.db_handler = db_handler
        self.running = False
        self.metrics_thread = None

    def start(self):
        self.running = True
        self.metrics_thread = Thread(target=self._collect_metrics)
        self.metrics_thread.daemon = True
        self.metrics_thread.start()

    def _collect_metrics(self):
        while self.running:
            try:
                # Métricas de performance
                performance_metrics = {
                    'processing_rate': self._calculate_processing_rate(),
                    'recognition_accuracy': self._calculate_recognition_accuracy(),
                    'average_processing_time': self._calculate_avg_processing_time(),
                    'error_rate': self._calculate_error_rate()
                }
                
                # Métricas de recursos
                resource_metrics = {
                    'cpu_usage': psutil.cpu_percent(),
                    'memory_usage': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent
                }
                
                metrics = {
                    'timestamp': datetime.now(),
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'process_metrics': {
                        'cpu_percent': psutil.Process().cpu_percent(),
                        'memory_info': dict(psutil.Process().memory_info()._asdict())
                    },
                    'performance_metrics': performance_metrics,
                    'resource_metrics': resource_metrics
                }
                
                # Coletar métricas do MongoDB
                db_stats = self.db_handler.get_processing_stats()
                metrics.update(db_stats)
                
                # Salvar métricas
                self.db_handler.save_metrics(metrics)
                
            except Exception as e:
                logger.error(f"Erro ao coletar métricas: {str(e)}")
            
            time.sleep(METRICS_INTERVAL)

    def stop(self):
        self.running = False
        if self.metrics_thread:
            self.metrics_thread.join() 