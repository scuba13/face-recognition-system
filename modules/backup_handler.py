import os
import shutil
from datetime import datetime
import logging
from config import FAILED_BATCHES_DIR, BACKUP_FAILED_BATCHES

logger = logging.getLogger(__name__)

class BackupHandler:
    def __init__(self):
        if BACKUP_FAILED_BATCHES:
            os.makedirs(FAILED_BATCHES_DIR, exist_ok=True)

    def backup_failed_batch(self, batch_folder, error_message):
        """Faz backup de um lote que falhou no processamento"""
        if not BACKUP_FAILED_BATCHES:
            return

        try:
            # Criar estrutura de backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                FAILED_BATCHES_DIR,
                f"{os.path.basename(batch_folder)}_{timestamp}"
            )

            # Copiar pasta
            shutil.copytree(batch_folder, backup_path)

            # Criar arquivo de metadados
            with open(f"{backup_path}_error.txt", "w") as f:
                f.write(f"Error: {error_message}\n")
                f.write(f"Original path: {batch_folder}\n")
                f.write(f"Timestamp: {timestamp}\n")

            logger.info(f"Backup criado em: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Erro ao fazer backup do lote {batch_folder}: {str(e)}")
            return None 