import pytest
import pandas as pd
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path


SOURCE_YEAR = 1990
SOURCE_MONTH = 1
VALID_FILENAME = f"yellow_tripdata_{SOURCE_YEAR}-{SOURCE_MONTH:02d}.parquet"


@pytest.fixture
def source_period() -> tuple[int, int]:
    return SOURCE_YEAR, SOURCE_MONTH

@pytest.fixture
def test_source_file() -> str:
    return VALID_FILENAME

@pytest.fixture
def valid_row() -> dict:
    """
    One clean, valid taxi trip row.
    All business rules pass.
    Baseline across all test files.
    """
    return {
        "VendorID"              : 1,
        "tpep_pickup_datetime"  : pd.Timestamp(f"{SOURCE_YEAR}-{SOURCE_MONTH:02d}-02 08:00:00"),
        "tpep_dropoff_datetime" : pd.Timestamp(f"{SOURCE_YEAR}-{SOURCE_MONTH:02d}-02 08:30:00"),
        "passenger_count"       : 1.0,
        "trip_distance"         : 3.5,
        "RatecodeID"            : 1.0,
        "store_and_fwd_flag"    : "N",
        "PULocationID"          : 100,
        "DOLocationID"          : 200,
        "payment_type"          : 1,
        "fare_amount"           : 15.0,
        "extra"                 : 4.5,
        "mta_tax"               : 0.5,
        "tip_amount"            : 3.0,
        "tolls_amount"          : 0.0,
        "improvement_surcharge" : 1.0,
        "total_amount"          : 24.0,
        "congestion_surcharge"  : 2.5,
        "Airport_fee"           : 0.0,
        "cbd_congestion_fee"    : 0.50
    }

@pytest.fixture
def valid_dataframe(valid_row) -> pd.DataFrame:
    """
    A single-row Dataframe built from valid_row fixture.
    Used when a test needs a DataFrame directly, not a dict
    """
    return pd.DataFrame([valid_row])


# --- Integration test to PSQL
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

@pytest.fixture
def valid_transformed_row() -> dict:
    """
    A single row matching staging.yellow_trips schema exactly.
    """
    return {
        "pickup_at":              pd.Timestamp(f"{SOURCE_YEAR}-{SOURCE_MONTH:02d}-01 08:00:00"),
        "dropoff_at":             pd.Timestamp(f"{SOURCE_YEAR}-{SOURCE_MONTH:02d}-01 08:30:00"),
        "passenger_count":        pd.NA,
        "trip_distance":          3.5,
        "pickup_zone_id":         100,
        "dropoff_zone_id":        200,
        "fare_amount":            15.0,
        "tip_amount":             3.0,
        "total_amount":           24.0,
        "payment_type":           pd.NA,
        "trip_duration_minutes":  30.0,
    }

@pytest.fixture
def valid_transformed_dataframe(valid_transformed_row) -> pd.DataFrame:
    """
    A single row matching staging.yellow_trips schema exactly.
    """
    return pd.DataFrame([valid_transformed_row])



@pytest.fixture
def test_db_config() -> dict:
    """
    Database config pointing to taxi_db_test [NOT PRODUCTION]
    """
    return{
        "source_file": os.getenv("SOURCE_FILE"),
        "db_host":     os.getenv("DB_HOST"),
        "db_port":     os.getenv("DB_PORT", "5432"),
        "db_name":     os.getenv("TEST_DB_NAME"),
        "db_user":     os.getenv("DB_USER"),
        "db_password": os.getenv("DB_PASSWORD"),
        "batch_size":  5000,
    }

@pytest.fixture
def invalid_db_config() -> dict:
    """
    Invalid Database config
    """
    return {
        "db_host":     "localhost",
        "db_port":     "5432",
        "db_name":     "database_that_does_not_exist",
        "db_user":     "invalid_user",
        "db_password": "invalid_password",
        "batch_size":  5000,
    }


@pytest.fixture
def db_connection(test_db_config):
    """
    Live connection to taxi_db_test.
    Truncates staging.yellow_trips after every test automatically.
    """
    conn = psycopg2.connect(
        host=test_db_config["db_host"],
        port = test_db_config["db_port"],
        dbname = test_db_config["db_name"],
        user = test_db_config["db_user"],
        password = test_db_config["db_password"]
    )

    yield conn

    # Teardown which runs after every test, regardless of pass/fail
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw.yellow_trips, staging.yellow_trips RESTART IDENTITY")
    conn.commit()
    conn.close()    