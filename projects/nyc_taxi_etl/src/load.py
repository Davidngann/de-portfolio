import psycopg2
import psycopg2.extras
import pandas as pd
from src.exceptions import LoadError
from src.logger import get_logger

logger = get_logger(__name__)

# Set a list that matched both DataFrame from
# transformation stage and database
COLUMNS_FOR_STAGING = [
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

# Insert the raw columns 
COLUMNS_FOR_RAW = [
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
        msg = f"Database connection failed: {e}"
        logger.error(msg)
        raise LoadError(msg)
    
def _build_insert_sql(target_schema: str, target_table: str, columns_to_insert: list) -> str:
    """
    Build the INSERT statement for execute_values().
    execute_values() replace %s with the batch values automatically.
    """
    columns = ", ".join(columns_to_insert)
    return f"INSERT INTO {target_schema}.{target_table} ({columns}) VALUES %s"

def _to_python_scalar(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v

def _execute_sql_file(filepath:str, config:dict) -> None:
    conn = _get_connection(config)
    try:
        with conn:
            with conn.cursor() as cur:  
                logger.info(f"Starting SQL script: {filepath}")
                with open(filepath, "r", encoding="utf-8") as sql_file:
                    sql_script = sql_file.read()
                cur.execute(sql_script)
                logger.info(f"SQL script executed: {filepath} | PSQL Status: {cur.statusmessage} | Rows affected: {cur.rowcount:,}")
                logger.info(f"Successfully executed sql script: {filepath}")
    except (OSError, psycopg2.Error) as e:
        msg = f"Error during executing SQL Script from {filepath}: {e}"
        logger.error(msg)
        raise LoadError(msg)
    finally:
        conn.close()
        logger.info("Database connection closed")


def _batch_insert(conn, insert_sql: str, records: list, batch_size: int, target_schema: str) -> None:
    """
    Core batching loop.
    Each batch is its own transaction.
    A failed batch rolls back only to that batch
    """
    total_rows = len(records)
    total_batches = (total_rows + batch_size - 1) // batch_size
    rows_loaded = 0
    batches_completed = 0
    
    logger.info(
        f"[{target_schema}] starting load: {total_rows:,} rows | Batch size: {batch_size:,} | Total batches: {total_batches:,}"
    )

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
                f"Batch for {target_schema}: {batches_completed:,}/{total_batches:,} | Rows loaded: {rows_loaded:,}/{total_rows:,}"
            )

        except psycopg2.Error as e:
            msg = f"Batch for {target_schema}: {batches_completed+1:,} failed | rows {i:,} to {i+len(batch):,} rolled back | Error: {e}"
            logger.error(msg)
            raise LoadError(msg)
    logger.info(
        f"Load complete | {rows_loaded:,} rows inserted across {batches_completed:,} batches"
    )

def load(df: pd.DataFrame, config:dict, target_schema: str)-> None:
    """
    Insert the clean DataFrame into the target schema's table in batches

    IF 
    target_schema == "raw" -> load the data into raw.yellow_trips
    target_schema == "staging -> load data into staging.yellow_trips 

    Each batch is wrapped in a transaction
    A failed batch rolls back that batch only (prior committed batches are not affected)

    Raise LoadError if the connection fails or a batch cannot be inserted.
    """

    batch_size = config["batch_size"]

    if target_schema == "raw":
        INSERT_COLUMNS = COLUMNS_FOR_RAW
    elif target_schema == "staging":
        INSERT_COLUMNS = COLUMNS_FOR_STAGING
    else:
        msg = f"{target_schema} schema is faulty, input the valid target schema ['raw'] or ['staging']"
        logger.error(msg)
        raise LoadError(msg)

    insert_sql = _build_insert_sql(target_schema, "yellow_trips", INSERT_COLUMNS)

    total_rows = len(df)
    records = []

    logger.info(f"Preparing {total_rows:,} rows, ensuring compatibility for insert into {target_schema}...")

    for i, row in enumerate(df[INSERT_COLUMNS].itertuples(index=False, name=None)):
        records.append(tuple(_to_python_scalar(v) for v in row))
        if (i + 1 ) % 500_000 == 0:
            logger.info(f"Scalar conversion: {i + 1:,}/{total_rows:,} rows converted")

    logger.info(f"Row preparation complete: {len(records):,} records ready")

    conn = _get_connection(config)


    # --- Start loading process
    try:
        _batch_insert(conn, insert_sql, records, batch_size, target_schema)
    finally:
        conn.close()
        logger.info("Database connection closed")