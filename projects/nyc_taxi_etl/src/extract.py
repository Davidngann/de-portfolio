import pandas as pd
from pathlib import Path
from src.exceptions import ExtractionError
from src.logger import get_logger
import re

logger = get_logger(__name__)

# Set expected columns from data source
EXPECTED_SOURCE_RAW_COLUMNS = {
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "store_and_fwd_flag",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "Airport_fee",
    "cbd_congestion_fee"
}



def extract(source_file: str) -> tuple[pd.DataFrame, int, int]:
    """
    Read the source Parquet file and validate the schema contract.
    
    Return a raw, unmodified DataFrame containing only the expected columns.
    Raises ExtractionError if the file is missing, unreadable,
    schema validation fails, or the file contains zero rows.
    """
    
    data_dir = Path(__file__).parent.parent / "data"
    filepath = data_dir / source_file

    # Validate filename pattern
    FILENAME_PATTERN = re.compile(r'^yellow_tripdata_(\d{4})-(\d{2})\.parquet$')
    match = FILENAME_PATTERN.match(source_file)
    if not match:
        msg = f"Invalid source filename: {source_file}. Expected format: yellow_tripdata_YYYY-MM.parquet"
        logger.error(msg)
        raise ExtractionError(msg)
    year, month = int(match.group(1)), int(match.group(2))
    logger.info(f"Filename validation passed for period: {year}-{month:02d}")

    logger.info(f"Starting extraction from {filepath}")

    # Check file existence
    if not filepath.exists():
        msg = f"Source file not found: {filepath}"
        logger.error(msg)
        raise ExtractionError(msg)
    
    # Read file
    try:
        df = pd.read_parquet(filepath)
    except Exception as e:
        msg = f"Failed to read Parquet file: {e}"
        logger.error(msg)
        raise ExtractionError(msg)
    
    logger.info(f"Raw file loaded: {len(df):,}, rows, {len(df.columns)} columns")

    # Validate Schema
    actual_columns = set(df.columns)
    missing_columns = EXPECTED_SOURCE_RAW_COLUMNS - actual_columns
    if missing_columns:
        msg =  f"Schema validation failed. Missing columns {missing_columns}"
        logger.error(msg)
        raise ExtractionError(msg)
    logger.info("Schema validation passed")

    # Check empty file
    if len(df) == 0:
        msg = "Source file contains zero rows"
        logger.error(msg)
        raise ExtractionError(msg)
    
    logger.info(f"Extraction complete: {len(df):,} rows returned")

    return df, year, month