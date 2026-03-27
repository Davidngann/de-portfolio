import pandas as pd
import pytest
from unittest.mock import patch
from src.extract import extract, EXPECTED_SOURCE_RAW_COLUMNS
from src.exceptions import ExtractionError


def test_extract_returns_expected_columns(valid_dataframe):
    with patch("src.extract.Path.exists") as mock_exists, \
    patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value = True
        mock_read.return_value = valid_dataframe
        result = extract("mock_file.parquet")

    assert set(result.columns) == EXPECTED_SOURCE_RAW_COLUMNS


def test_extract_raises_on_missing_file():
    with pytest.raises(ExtractionError, match="not found"):
        extract("missing_file.parquet")

def test_reading_non_existant_file():
    with patch("src.extract.Path.exists") as mock_exists,\
        patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value = True
        mock_read.side_effect = Exception("disk read error")
        with pytest.raises(ExtractionError, match="Failed to read Parquet file"):
            extract("unreadable.parquet")


def test_extract_raises_on_missing_column(valid_dataframe):
    broken_df = valid_dataframe.drop(columns=["fare_amount"])
    
    with patch("src.extract.Path.exists") as mock_exists, \
        patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value = True
        mock_read.return_value = broken_df
        with pytest.raises(ExtractionError, match="Missing columns"):
            extract("missing_column.parquet")


def test_extract_raises_on_empty_file(valid_dataframe):
    empty_df = valid_dataframe.iloc[0:0]

    with patch("src.extract.Path.exists") as mock_exists,\
        patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value=True
        mock_read.return_value=empty_df
        with pytest.raises(ExtractionError, match="contains zero rows"):
            extract("empty_file.parquet")
