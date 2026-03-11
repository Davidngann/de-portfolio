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
# passenger_count           - self-reported, often missing, but still useable
# tip_amount                - missing tip means $0 tip in many cases
# payment_type              - useful row overall without payment method

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
        len_dropped_nulls = len_after_null_drop - len_initial

        logger.info(
            f"Null drop complete: {len_dropped_nulls:,} rows removed, {len_after_null_drop:,} remaining | dropped percentage: {len_dropped_nulls/len_after_null_drop*100:.1f}%")
        
        # --- Step 2: Drop invalid business values ---
        len_before_business = len(df)
        df = df[df['trip_distance'] > 0]
        df = df[df['fare_amount'] > 0]
        len_after_dropped_business = len(df)
        len_dropped_business = len_before_business - len_after_dropped_business 

        logger.info(f"Business rule filter complete: {len_dropped_business:,} rows removed, {len_after_dropped_business:,} remaining | dropped percentage: {len_dropped_business/len_after_dropped_business*100:.1f}% ")
        
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

        logger.info(f"Duration filter complete: {len_dropped_duration:,} rows removed, {len_after_dropped_duration:,} remaining | dropped percentage: {len_dropped_duration/len_after_dropped_duration*100:.1f}% ")

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
        logger.info(f"Transformation complete: {len(df):,} rows ready for load | total dropped: {total_dropped:,}  | % dropped from initial: {total_dropped/len_initial*100:.1f}%")

        return df
    
    except TransformationError:
        raise 
    
    except Exception as e:
        raise TransformationError(f"Unexpected error during transformation: {e}")
    