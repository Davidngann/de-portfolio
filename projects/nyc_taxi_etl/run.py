from src.config import get_config
from src.extract import extract
from src.transform import transform
from src.load import load, execute_sql_file
from src.validate import validate_dataframe
from src.logger import get_logger
import argparse

logger = get_logger(__name__)

def parse_args():
    parser=argparse.ArgumentParser(description="NYC Taxi ETL Pipeline")
    parser.add_argument(
        "--target-schema",
        choices=["raw","staging"],
        default="raw",
        help="Target schema to load into (default: raw)" 
    )
    return parser.parse_args()

def main():
    args = parse_args()
    config = get_config()
    target_schema = args.target_schema.lower()
    source_file = config['source_file']
    logger.info(f"Pipeline starting | ENV: {config.get('pipeline_env', 'DEVELOPMENT')} | Target Schema: {target_schema}")

    df_raw, source_year, source_month = extract(source_file)

    if target_schema == "raw":
        # Loading the raw data source into db directly, skipping transfor layer from python.
        load(df_raw, config, target_schema, source_file)
        # validate_row_counts(config, df_raw, target_schema)
        execute_sql_file('sql/raw_to_staging.sql', config)
        

    elif target_schema == "staging":
        df_clean = transform(df_raw, source_year, source_month)
        # Validate transform, before loading
        validate_dataframe(df_clean, stage="transform")
        load(df_clean, config, target_schema, source_file)
        # validate_row_counts(config, df_clean, target_schema)

    execute_sql_file('sql/staging_to_reporting.sql', config)

    logger.info("Pipeline complete")

if __name__ == "__main__":
    main()