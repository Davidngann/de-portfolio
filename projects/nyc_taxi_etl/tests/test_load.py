import pandas as pd
import pytest 
from unittest.mock import MagicMock, mock_open, patch
import psycopg2
from src.load import load, execute_sql_file, validate_row_counts
from src.exceptions import LoadError


def test_load_inserts_correct_row_count_to_raw_schema(db_connection, test_db_config, valid_row, test_source_file):
    df = pd.DataFrame([valid_row]*3)

    load(df, test_db_config, target_schema="raw", source_file = test_source_file)

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw.yellow_trips WHERE source_file=%s", (test_source_file,))
        count = cur.fetchone()[0]

    assert count == 3


def test_load_inserts_correct_row_count_to_staging(db_connection, test_db_config, valid_transformed_row, test_source_file):
    df = pd.DataFrame([valid_transformed_row]*3)

    load(df, test_db_config, "staging", source_file = test_source_file)

    with db_connection.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM staging.yellow_trips WHERE source_file=%s", (test_source_file,))
        count = cur.fetchone()[0]

    assert count == 3
    

def test_load_raises_on_bad_connection_config(invalid_db_config, valid_row, test_source_file):
    df = pd.DataFrame([valid_row])
    with pytest.raises(LoadError, match="Database connection failed"):
        load(df, invalid_db_config, "raw", source_file = test_source_file)


@pytest.mark.parametrize("batch_size", [1,2,5000])
def test_load_correct_count_across_batch_sizes_to_staging(db_connection, test_db_config, valid_transformed_row, batch_size, test_source_file):
    df = pd.DataFrame([valid_transformed_row]*5)

    config = {**test_db_config, "batch_size": batch_size}
    load(df, config, "staging", source_file = test_source_file)

    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM staging.yellow_trips WHERE source_file=%s", (test_source_file,))
        count = cur.fetchone()[0]

    assert count == 5


def test_load_raises_on_invalid_schema(valid_transformed_dataframe, test_db_config, test_source_file):
    with pytest.raises(LoadError, match="faulty"):
        load(valid_transformed_dataframe, test_db_config, "invalid_schema", source_file = test_source_file)


def test_batch_insert_raises_load_error_on_psycopg2_error(valid_transformed_dataframe, test_db_config, test_source_file):
    with patch("psycopg2.extras.execute_values", side_effect=psycopg2.Error("mocked db error")):
        with pytest.raises(LoadError, match="rolled back"):
            load(valid_transformed_dataframe, test_db_config, "staging", source_file = test_source_file)


def test_execute_sql_file_raises_load_error_on_invalid_filepath(test_db_config):
    with pytest.raises(LoadError, match="invalid_file.sql"):
        execute_sql_file('invalid_file.sql', test_db_config)


def test_execute_sql_file_raises_load_error_on_bad_connection(invalid_db_config):
    with pytest.raises(LoadError, match="Database connection failed"):
        execute_sql_file('staging_to_reporting.sql', invalid_db_config)


@pytest.mark.parametrize(
        "target_schema, df_fixture",
        [
            ("raw", "valid_dataframe"),
            ("staging", "valid_transformed_dataframe"),
        ],
)
def test_validate_row_counts_passes_after_load(db_connection, test_db_config, request, target_schema, df_fixture, test_source_file):
    df = request.getfixturevalue(df_fixture)
    load(df, test_db_config, target_schema, source_file = test_source_file)
    validate_row_counts(db_connection, len(df), target_schema, source_file = test_source_file)



@pytest.mark.parametrize("target_schema", ["raw", "staging"])
def test_validate_row_counts_raises_load_error_on_mismatch(target_schema, test_source_file):   
    mock_cursor  = MagicMock()
    mock_cursor.fetchone.return_value = (5,)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    with pytest.raises(LoadError, match="count mismatch"):
        validate_row_counts(mock_conn, 3, target_schema, source_file = test_source_file)

    