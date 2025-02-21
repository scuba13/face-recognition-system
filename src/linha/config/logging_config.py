import logging
import os
from datetime import datetime

def setup_logging(log_level=logging.INFO):
    """Configura logging da aplicação"""
    
    # Criar diretório de logs se não existir
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Nome do arquivo de log com timestamp
    log_file = os.path.join(
        log_dir, 
        f'linha_{datetime.now().strftime("%Y%m%d")}.log'
    )
    
    # Configuração básica
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Reduzir verbosidade de alguns loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING) 