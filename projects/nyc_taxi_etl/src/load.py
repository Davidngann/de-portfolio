import psycopg2
import psycopg2.extras
import pandas as pd
from src.exceptions import LoadError
from src.logger import get_logger

logger = get_logger(__name__)

# Set destination table
TARGET_SCHEMA = "staging"
TARGET_TABLE = "yellow_trips"

# Set a list that matched both DataFrame from
# transformation stage and database
INSERT_COLUMNS = [
    "pickup_at",
    "dropoff_at",
    "passenger_count",
    "trip_distance",
    "pickup_zone_id",
    "dropoff_zone_id",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "payment_type",
    "trip_duration_minutes",
]

# Establish connection to PSQL
def _get_connection(config: dict):
    """
    Create and return a psycopg2 connection.
    Raises LoadError if the connection cannot be established.
    """
    try:
        conn = psycopg2.connect(
            host = config["db_host"],
            port = config["db_port"],
            dbname = config["db_name"],
            user = config["db_user"],
            password = config["db_password"]
        )
        return conn
    except psycopg2.OperationalError as e:
        raise LoadError(f"Database connection failed: {e}")
    
def _build_insert_sql() -> str:
    """
    Build the INSERT statement for execute_values().
    execute_values() replace %s with the batch values automatically.
    """
    columns = ", ".join(INSERT_COLUMNS)
    return f"INSERT INTO {TARGET_SCHEMA}.{TARGET_TABLE} ({columns}) VALUES %s"

def _to_python_scalar(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v

def load(df: pd.DataFrame, config:dict) -> None:
    """
    Insert the clean DataFrame into the destination table in batches

    Each batch is wrapped in a transaction
    A failed batch rolls back that batch only (prior committed batches are not affected)

    Raise LoadError if the connection fails or a batch cannot be inserted.
    """
    total_rows = len(df)
    batch_size = config["batch_size"]
    total_batches = (total_rows //batch_size) + 1

    logger.info(
        f"Starting load with: {total_rows:,} rows | Batch size: {batch_size:,} | Total batches: {total_batches:,}"
    )

    insert_sql = _build_insert_sql()
    conn = _get_connection(config)

    # Convert DataFrame to list of tuples once — not per batch
    # None handles pandas NA → psycopg2 sends NULL to Postgres
    records = [
        tuple(_to_python_scalar(v) for v in row)
        for row in df[INSERT_COLUMNS].itertuples(index=False, name=None)
    ]

    # --- Start loading process
    rows_loaded = 0
    batches_completed = 0

    try:
        for i in range(0, total_rows, batch_size):
            batch = records[i: i+batch_size]

            try:
                with conn:
                    with conn.cursor() as cur:
                        psycopg2.extras.execute_values(
                            cur, insert_sql, batch, page_size=batch_size
                        )

                rows_loaded += len(batch)
                batches_completed += 1

                logger.info(
                    f" Batch {batches_completed:,}/{total_batches:,} | Rows loaded: {rows_loaded:,}/{total_rows:,}"
                )

            except psycopg2.Error as e:
                logger.error(
                    f"Batch: {batches_completed+1:,} failed | rows {i:,} to {i+len(batch):,} rolled back | Error: {e}"
                )
                raise LoadError(f"Batch insert failed: {e}")
            
    finally:
        conn.close()
        logger.info("Database connection closed")

    logger.info(
        f"Load complete | {rows_loaded:,} rows inserted across {batches_completed:,} batches"
    )

                