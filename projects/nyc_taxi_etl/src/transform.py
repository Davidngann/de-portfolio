import pandas as pd
from src.exceptions import TransformationError
from src.logger import get_logger

logger = get_logger(__name__)

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


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and reshape the raw extraction DataFrame
    to match the destination schema precisely.

    Raises TransformationError if the result is empty
    or a required transformation step fails
    """

    logger.info(f"Starting transformation: {len(df):,}, rows received")
    len_initial = len(df)

    try:
        # --- Step 1: Drop nulls on required columns ---
        df = df.dropna(subset=DROP_IF_NULL)
        len_after_null_drop = len(df)
        len_dropped_nulls = len_initial - len_after_null_drop
        pct_null_dropped = (len_dropped_nulls/len_initial*100) if len_initial else 0
        logger.info(
            f"Null drop complete: {len_dropped_nulls:,} rows removed, {len_after_null_drop:,} remaining | dropped percentage: {pct_null_dropped:.1f}%")
        
        # --- Step 2: Drop invalid business values ---
        len_before_business = len(df)
        df = df[df['trip_distance'] > 0]
        df = df[df['fare_amount'] > 0]
        len_after_dropped_business = len(df)
        len_dropped_business = len_before_business - len_after_dropped_business 
        pct_dropped_business = (len_dropped_business/len_before_business*100) if len_before_business else 0

        logger.info(f"Business rule filter complete: {len_dropped_business:,} rows removed, {len_after_dropped_business:,} remaining | dropped percentage: {pct_dropped_business:.1f}% ")
        
        # --- Step 3: Cast type explicitly ---
        df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'])
        df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'])
        df['trip_distance'] = df['trip_distance'].astype("float64")
        df['fare_amount'] = df['fare_amount'].astype("float64")
        df['tip_amount'] = df['tip_amount'].astype("float64")
        df['total_amount'] = df['total_amount'].astype("float64")
        df["PULocationID"] = df['PULocationID'].astype("int16")
        df['DOLocationID'] = df['DOLocationID'].astype("int16")

        # Int8 is pandas nullable integer — handles NaN without upcasting to float
        df['passenger_count'] = df['passenger_count'].astype("Int8")
        df['payment_type'] = df['payment_type'].astype("Int8")

        logger.info("Type casting complete")

        # --- Step 4: Derive trip_duration_minutes ---
        df['trip_duration_minutes'] = (
            (df['tpep_dropoff_datetime'] - df['tpep_pickup_datetime']).dt.total_seconds()/60
        ).round(2)

        # Drop rows where duration is <= 0
        len_before_duration = len(df)
        df = df[df['trip_duration_minutes'] > 0]
        len_after_dropped_duration = len(df)
        len_dropped_duration = len_before_duration - len_after_dropped_duration
        pct_dropped_duration = (len_dropped_duration/len_before_duration*100) if len_before_duration else 0

        logger.info(f"Duration filter complete: {len_dropped_duration:,} rows removed, {len_after_dropped_duration:,} remaining | dropped percentage: {pct_dropped_duration:.1f}% ")

        # Drop rows with unreasonably long duration
        # 1440 minutes = 24 hours
        len_before_max_duration = len(df)
        df = df[df['trip_duration_minutes'] <= 1440]
        len_after_dropped_max_duration = len(df)
        len_dropped_max_duration = len_before_max_duration - len_after_dropped_max_duration
        pct_dropped_max_duration = (len_dropped_max_duration/len_before_max_duration*100) if len_before_max_duration else 0
        logger.info(f"Max duration filter complete: {len_dropped_max_duration:,} rows removed, {len_after_dropped_max_duration:,} remaining | dropped percentage: {pct_dropped_max_duration:.1f}% ")


        # --- Step 5: Rename columns to match destination schema ---
        df = df.rename(columns={
            "tpep_pickup_datetime":  "pickup_at",
            "tpep_dropoff_datetime": "dropoff_at",
            "PULocationID":          "pickup_zone_id",
            "DOLocationID":          "dropoff_zone_id",
        })


        # --- Step 6: Final empty check ---
        if len(df) == 0:
            raise TransformationError(
                "Transformation produced zero rows - all rows where dropped during cleaning"
            )
        
        total_dropped = len_initial - len(df)
        pct_total_dropped = (total_dropped/len_initial*100) if len_initial else 0
        logger.info(f"Transformation complete: {len(df):,} rows ready for load | total dropped: {total_dropped:,}  | % dropped from initial: {pct_total_dropped:.1f}%")

        return df
    
    except TransformationError:
        raise 
    
    except Exception as e:
        raise TransformationError(f"Unexpected error during transformation: {e}")
    