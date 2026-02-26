import os
import logging
from dotenv import load_dotenv

# Load .env file into environment
load_dotenv()

def get_config() -> dict:
    """
    Load and validate all pipeline configuration from environment variables.
    Raise ValueError if a required variable is missing.
    """

    config={
        "data_filepath": os.getenv('DATA_FILEPATH'),
        "log_level": os.getenv('LOG_LEVEL', "INFO"),
        "pipeline_env": os.getenv("PIPELINE_ENV", "DEVELOPMENT")
    }

    if not config["data_filepath"]:
        raise ValueError('Missing the required env variable: DATA_FILEPATH')
    
    return config

if __name__ == "__main__":
    config = get_config()
    print(config)