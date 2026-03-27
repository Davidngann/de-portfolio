import pandas as pd
import pytest
import psycopg2
from src.load import load
from src.exceptions import LoadError

def test_load_inserts_correct_row_count_to_raw_schema(db_connection, test_db_config, valid_row):
    df = pd.DataFrame([valid_row]*3)

    load(df, test_db_config, target_schema="raw")

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw.yellow_trips")
        count = cur.fetchone()[0]

    assert count == 3

def test_load_inserts_correct_row_count_to_staging(db_connection, test_db_config, valid_transformed_row):
    df = pd.DataFrame([valid_transformed_row]*3)

    load(df, test_db_config, "staging")

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM staging.yellow_trips")
        count = cur.fetchone()[0]

    assert count == 3
    

def test_load_raises_on_bad_connection_config(valid_row):
    bad_config={
        "db_host":     "localhost",
        "db_port":     "5432",
        "db_name":     "database_that_does_not_exist",
        "db_user":     "invalid_user",
        "db_password": "invalid_password",
        "batch_size":  5000,
    }

    df = pd.DataFrame([valid_row])
    with pytest.raises(LoadError, match="Database connection failed"):
        load(df, bad_config, "raw")

@pytest.mark.parametrize("batch_size", [1,2,5000])
def test_load_correct_count_across_batch_sizes_to_staging(db_connection, test_db_config, valid_transformed_row, batch_size):
    df = pd.DataFrame([valid_transformed_row]*5)

    config = {**test_db_config, "batch_size": batch_size}
    load(df, config, "staging")

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM staging.yellow_trips")
        count = cur.fetchone()[0]

    assert count == 5