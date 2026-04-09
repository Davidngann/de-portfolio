import pandas as pd
import pytest 
from unittest.mock import MagicMock, mock_open, patch
import psycopg2
from src.load import load, _execute_sql_file
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
    

def test_load_raises_on_bad_connection_config(invalid_db_config, valid_row):
    df = pd.DataFrame([valid_row])
    with pytest.raises(LoadError, match="Database connection failed"):
        load(df, invalid_db_config, "raw")

@pytest.mark.parametrize("batch_size", [1,2,5000])
def test_load_correct_count_across_batch_sizes_to_staging(db_connection, test_db_config, valid_transformed_row, batch_size):
    df = pd.DataFrame([valid_transformed_row]*5)

    config = {**test_db_config, "batch_size": batch_size}
    load(df, config, "staging")

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM staging.yellow_trips")
        count = cur.fetchone()[0]

    assert count == 5


def test_load_raises_on_invalid_schema(valid_transformed_dataframe, test_db_config):
    with pytest.raises(LoadError, match="faulty"):
        load(valid_transformed_dataframe, test_db_config, "invalid_schema")


def test_batch_insert_raises_load_error_on_psycopg2_error(valid_transformed_dataframe, test_db_config):
    with patch("psycopg2.extras.execute_values", side_effect=psycopg2.Error("mocked db error")):
        with pytest.raises(LoadError, match="rolled back"):
            load(valid_transformed_dataframe, test_db_config, "staging")


def test_execute_sql_file_raises_load_error_on_invalid_filepath(test_db_config):
    with pytest.raises(LoadError, match="invalid_file.sql"):
        _execute_sql_file('invalid_file.sql', test_db_config)

def test_execute_sql_file_raises_load_error_on_bad_connection(invalid_db_config):
    with pytest.raises(LoadError, match="Database connection failed"):
        _execute_sql_file('staging_to_reporting.sql', invalid_db_config)