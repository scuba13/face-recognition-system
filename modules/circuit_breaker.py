import time
from functools import wraps
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = None
        self.lock = Lock()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                if self.state == "open":
                    if time.time() - self.last_failure_time > self.reset_timeout:
                        logger.info("Circuit breaker entering half-open state")
                        self.state = "half-open"
                    else:
                        raise Exception("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                
                with self.lock:
                    if self.state == "half-open":
                        logger.info("Circuit breaker closing")
                        self.state = "closed"
                        self.failures = 0
                
                return result

            except Exception as e:
                with self.lock:
                    self.failures += 1
                    self.last_failure_time = time.time()
                    
                    if self.failures >= self.failure_threshold:
                        logger.warning("Circuit breaker opening")
                        self.state = "open"
                
                raise e

        return wrapper 