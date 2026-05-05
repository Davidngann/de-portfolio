import pandas as pd
from src.exceptions import TransformationError
from src.logger import get_logger
from datetime import datetime, timedelta

logger = get_logger(__name__)

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

# --- Handle Null ---
# DROP if null:
# pickup_at, dropoff_at     - Duration cannot be derived without both
# trip_distance             - Core business metric
# fare_amount               - Core business metric
# total_amount              - Core business metric
# pickup_zone_id            - Not nullable in destination schema
# dropoff_zone_id           - Not nullable in destination schema

# KEEP if null:
# passenger_count           - Self-reported, often missing, but still usable
# tip_amount                - Missing tip means $0 tip in many cases
# payment_type              - Useful row overall without payment method

DROP_IF_NULL = [
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "trip_distance",
    "fare_amount",
    "total_amount",
    "PULocationID",
    "DOLocationID",
]



def transform(df: pd.DataFrame, source_year:int, source_month: int) -> pd.DataFrame:
    """
    Clean and reshape the raw extraction DataFrame
    to match the destination schema precisely.

    Raises TransformationError if the result is empty
    or a required transformation step fails
    """

    logger.info(f"Starting transformation: {len(df):,}, rows received")
    len_initial = len(df)

    try:
        # Validate & subset
        actual_columns = set(df.columns)
        missing_columns = EXPECTED_COLUMNS - actual_columns
        if missing_columns:
            msg = f"Schema validation for transformation failed. Missing columns {missing_columns}"
            logger.error(msg)
            raise TransformationError(msg)
        logger.info("Schema validation for transformation passed")

        df = df[list(EXPECTED_COLUMNS)].copy()


        # Drop nulls
        df = df.dropna(subset=DROP_IF_NULL)
        len_after_null_drop = len(df)
        len_dropped_nulls = len_initial - len_after_null_drop
        pct_null_dropped = (len_dropped_nulls/len_initial*100) if len_initial else 0
        logger.info(
            f"Null drop complete: {len_dropped_nulls:,} rows removed, {len_after_null_drop:,} remaining | dropped percentage: {pct_null_dropped:.1f}%")
        
        # Business filters
        len_before_business = len(df)
        df = df[df['trip_distance'] > 0]
        df = df[df['fare_amount'] > 0]
        df = df[df['total_amount'] > 0]
        len_after_dropped_business = len(df)
        len_dropped_business = len_before_business - len_after_dropped_business 
        pct_dropped_business = (len_dropped_business/len_before_business*100) if len_before_business else 0

        logger.info(f"Business rule filter complete: {len_dropped_business:,} rows removed, {len_after_dropped_business:,} remaining | dropped percentage: {pct_dropped_business:.1f}% ")
        

        # Cast type explicitly
        df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime']).dt.tz_localize('America/New_York', nonexistent='shift_forward', ambiguous='NaT')
        df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime']).dt.tz_localize('America/New_York', nonexistent='shift_forward', ambiguous='NaT')
        df['trip_distance'] = df['trip_distance'].astype("float64")
        df['fare_amount'] = df['fare_amount'].astype("float64")
        df['tip_amount'] = df['tip_amount'].astype("Float64")
        df['total_amount'] = df['total_amount'].astype("float64")
        df["PULocationID"] = df['PULocationID'].astype("int16")
        df['DOLocationID'] = df['DOLocationID'].astype("int16")

        # Int8 is pandas nullable integer — handles NaN without upcasting to float
        df['passenger_count'] = df['passenger_count'].astype("Int8")
        df['payment_type'] = df['payment_type'].astype("Int8")

        logger.info("Type casting complete")


        # Check timeframe plausibility
        # Includes 1 day before and after the specific year and month.

        len_before_timeframe_filter = len(df)
        lower_bound_date = datetime(source_year, source_month, 1) - timedelta(days=1)

        next_month = source_month + 1 if source_month < 12 else 1
        next_year = source_year if source_month < 12 else source_year + 1
        upper_bound_date = datetime(next_year, next_month, 1)

        pickup_naive = df['tpep_pickup_datetime'].dt.tz_convert(None)
        df = df[(pickup_naive >= lower_bound_date) & (pickup_naive <= upper_bound_date)]

        len_after_timeframe_filter = len(df)
        len_dropped_timeframe = len_before_timeframe_filter - len_after_timeframe_filter 
        pct_dropped_timeframe = (len_dropped_timeframe/len_before_timeframe_filter*100) if len_before_timeframe_filter else 0

        logger.info(f"Timeframe plausibility filter complete: {len_dropped_timeframe:,} rows removed, {len_after_timeframe_filter:,} remaining | dropped percentage: {pct_dropped_timeframe:.1f}% ")


        # Derive trip_duration_minutes
        df['trip_duration_minutes'] = (
            (df['tpep_dropoff_datetime'] - df['tpep_pickup_datetime']).dt.total_seconds()/60
        ).round(2)

        # Filter trip_duration_minutes outliers
        # Drop rows with unreasonably below or equal to zero and long duration <= 1440 minutes (24 hours)
        len_before_duration = len(df)
        df = df[(df['trip_duration_minutes'] > 0) & (df['trip_duration_minutes'] <= 1440)]
        len_after_dropped_duration = len(df)
        len_dropped_duration = len_before_duration - len_after_dropped_duration
        pct_dropped_duration = (len_dropped_duration/len_before_duration*100) if len_before_duration else 0

        logger.info(f"Duration filter complete: {len_dropped_duration:,} rows removed, {len_after_dropped_duration:,} remaining | dropped percentage: {pct_dropped_duration:.1f}% ")

        # Rename columns to match the destination table
        df = df.rename(columns={
            "tpep_pickup_datetime":  "pickup_at",
            "tpep_dropoff_datetime": "dropoff_at",
            "PULocationID":          "pickup_zone_id",
            "DOLocationID":          "dropoff_zone_id",
        })


        # --- Final empty check ---
        if len(df) == 0:
            msg = "Transformation produced zero rows - all rows where dropped during cleaning"
            logger.error(msg)
            raise TransformationError(msg)
        
        total_dropped = len_initial - len(df)
        pct_total_dropped = (total_dropped/len_initial*100) if len_initial else 0
        logger.info(f"Transformation complete: {len(df):,} rows ready for load | total dropped: {total_dropped:,}  | % dropped from initial: {pct_total_dropped:.1f}%")
    
        return df

    except TransformationError as e:
        raise
    except Exception as e:
        msg = f"Unexpected error during transformation: {e}"
        logger.error(msg)
        raise TransformationError(msg)
    