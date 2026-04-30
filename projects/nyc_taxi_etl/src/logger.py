import logging
from pathlib import Path
import os

def get_logger(name: str) -> logging.Logger:

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)

    if os.environ.get('AIRFLOW_HOME'):
        return logger
    
    logger.propagate = False

    # Set format for logger
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # File handler
    log_path = Path(__file__).parent.parent / "logs" / "pipeline.log"
    log_path.parent.mkdir(parents=True, exist_ok=True) 
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger