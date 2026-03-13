import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file into environment
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

def get_config() -> dict:
    """
    Load and validate all pipeline configuration from environment variables.
    Raise ValueError if a required variable is missing.
    """
    
    # Get the source data filepath
    base_dir = Path(__file__).parent
    raw_path = os.getenv('DATA_FILEPATH')
    full_path = base_dir / raw_path if raw_path else None

    config={
        "data_filepath": str(full_path),
        "log_level": os.getenv('LOG_LEVEL', "INFO"),
        "pipeline_env": os.getenv("PIPELINE_ENV", "DEVELOPMENT")
    }

    if not config["data_filepath"]:
        raise ValueError('Missing the required env variable: DATA_FILEPATH')
    
    return config

if __name__ == "__main__":
    config = get_config()
    print(config)