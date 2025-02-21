import logging
from colorama import init, Fore, Style

init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Formatador personalizado com cores e símbolos"""
    
    COLORS = {
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
        'DEBUG': Fore.BLUE
    }
    
    SYMBOLS = {
        'INFO': '✓',
        'WARNING': '⚠',
        'ERROR': '✗',
        'CRITICAL': '☠',
        'DEBUG': '⚙'
    }
    
    def format(self, record):
        # Adicionar cor e símbolo ao nível do log
        color = self.COLORS.get(record.levelname, '')
        symbol = self.SYMBOLS.get(record.levelname, '')
        
        # Formatar diferentes tipos de mensagem
        if "Iniciando" in record.msg:
            record.msg = f"▶ {record.msg}"
        elif "Finalizando" in record.msg:
            record.msg = f"⏹ {record.msg}"
        elif "Erro" in record.msg:
            record.msg = f"✗ {record.msg}"
            
        record.levelname = f"{color}{symbol} {record.levelname}{Style.RESET_ALL}"
        return super().format(record)

def setup_colored_logging(level=logging.INFO):
    """Configura logging colorido"""
    formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para console
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remover handlers existentes
    root_logger.handlers = []
    root_logger.addHandler(console) 