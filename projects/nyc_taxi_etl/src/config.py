import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

def get_config() -> dict:
    """
    Load and validate pipeline configuration from environment variables.
    Raises ValueError if a required variable is missing.
    """

    config={
        "source_file":  os.getenv("SOURCE_FILE"),
        "db_host":      os.getenv("DB_HOST"),
        "db_port":      os.getenv("DB_PORT", "5432"),
        "db_name":      os.getenv("DB_NAME"),
        "db_user":      os.getenv("DB_USER"),
        "db_password":  os.getenv("DB_PASSWORD"),
        "batch_size":   int(os.getenv("BATCH_SIZE", "5000")),
    }

    required = ["source_file", "db_host", "db_name", "db_user", "db_password"]
    for key in required:
        if not config[key]:
            raise ValueError(f"Missing required environment variables: {key.upper()}")
        
    return config

if __name__ == "__main__":
    config = get_config()