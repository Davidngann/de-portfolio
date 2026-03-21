from src.config import get_config
from src.extract import extract
from src.transform import transform
from src.load import load
from src.validate import validate_dataframe
from src.logger import get_logger

logger = get_logger(__name__)

def main():
    config = get_config()
    logger.info(f"Pipeline starting | ENV: {config.get('pipeline_env', 'DEVELOPMENT')}")

    df_raw = extract(config['source_file'])
    df_clean = transform(df_raw)

    # Validate transform, before loading
    validate_dataframe(df_clean, stage="transform")

    load(df_clean, config)
    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()