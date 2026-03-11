import pandas as pd
from pathlib import Path
from src.exceptions import ExtractionError
from src.logger import get_logger

logger = get_logger(__name__)

# Set expected columns from data source
EXPECTED_COLUMNS = {
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "PULocationID",
    "DOLocationID",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "payment_type",
}


def extract(source_file: str) -> pd.DataFrame:
    """
    Read the source Parquet file and validate the schema contract.
    
    Return a raw, unmodified DataFrame containing only the expected columns.
    Raises ExtractionError if the file is missing, unreadable,
    schema validation fails, or the file contains zero rows.
    """
    \
    data_dir = Path(__file__).parent.parent / "data"
    filepath = data_dir / source_file

    logger.info(f"Starting extraction from {filepath}")

    # Check file existence
    if not filepath.exists():
        raise ExtractionError(f"Source file not found: {filepath}")
    
    # Read file
    try:
        df = pd.read_parquet(filepath)
    except Exception as e:
        raise ExtractionError(f"Failed to read Parquet file: {e}")
    
    logger.info(f"Raw file loaded: {len(df):,}, rows, {len(df.columns)} columns")

    # Validate Schema
    actual_columns = set(df.columns)
    missing_columns = EXPECTED_COLUMNS - actual_columns

    if missing_columns:
        raise ExtractionError(
            f"Schema validation failed. Missing columns {missing_columns}"
        )
    
    logger.info("Schema validation passed")

    # Check empty file
    if len(df) == 0:
        raise ExtractionError("Source file contains zero rows")
    
    # Select only the required columns for pipeline
    df = df[list(EXPECTED_COLUMNS)]

    logger.info(f"Extraction complete: {len(df):,} rows returned")

    return df