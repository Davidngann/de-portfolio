import pytest
import pandas as pd
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

@pytest.fixture
def valid_row() -> dict:
    """
    One clean, valid taxi trip row.
    All business rules pass.
    Baseline across all test files.
    """
    return {
        "VendorID"              : 1,
        "tpep_pickup_datetime"  : pd.Timestamp("2025-04-01 08:00:00"),
        "tpep_dropoff_datetime" : pd.Timestamp("2025-04-01 08:30:00"),
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
def valid_transformed_row(valid_row) -> dict:
    """
    A single row built from valid_row.
    Then, transformed following src.transform() rules for Load test purposes. 
    """
    updates={
        "tpep_pickup_datetime":  "pickup_at",
        "tpep_dropoff_datetime": "dropoff_at",
        "PULocationID":          "pickup_zone_id",
        "DOLocationID":          "dropoff_zone_id",
    }
    renamed_valid_row = {updates.get(k,k): v for k, v in valid_row.items()}

    renamed_valid_row["trip_duration_minutes"] = 30.0
    renamed_valid_row["passenger_count"]=pd.NA

    return renamed_valid_row


@pytest.fixture
def test_db_config() -> dict:
    """
    Database config pointing to taxi_db_test [NOT PRODUCTION]
    """
    return{
        "db_host":     os.getenv("DB_HOST"),
        "db_port":     os.getenv("DB_PORT", "5432"),
        "db_name":     os.getenv("TEST_DB_NAME"),
        "db_user":     os.getenv("DB_USER"),
        "db_password": os.getenv("DB_PASSWORD"),
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