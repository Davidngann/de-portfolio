import pandas as pd
import pytest
from unittest.mock import patch
from src.extract import extract, EXPECTED_SOURCE_RAW_COLUMNS
from src.exceptions import ExtractionError


def test_extract_raises_on_intest_source_file():
    with pytest.raises(ExtractionError, match="Invalid source filename:"):
        extract("random_file.parquet")

def test_extract_raises_on_wrong_naming_convention():
    with pytest.raises(ExtractionError, match="Invalid source filename:"):
        extract("yellow_tripdata_190101.parquet")

def test_extract_raises_on_reading_file(test_source_file):
    with patch("src.extract.Path.exists") as mock_exists, \
        patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value = True
        mock_read.side_effect = Exception("corrupt file")
        with pytest.raises(ExtractionError, match="Failed to read Parquet file"):
            extract(test_source_file)


def test_extract_returns_correct_source_period(valid_dataframe, test_source_file, source_period):
    with patch("src.extract.Path.exists") as mock_exists, \
        patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value = True
        mock_read.return_value = valid_dataframe
        _, year, month = extract(test_source_file)

    test_year, test_month = source_period
    assert year == test_year
    assert month == test_month


def test_extract_returns_expected_columns(valid_dataframe, test_source_file):
    with patch("src.extract.Path.exists") as mock_exists, \
    patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value = True
        mock_read.return_value = valid_dataframe
        result, _, _ = extract(test_source_file)

    assert set(result.columns) == EXPECTED_SOURCE_RAW_COLUMNS


def test_extract_raises_on_missing_column(valid_dataframe, test_source_file):
    broken_df = valid_dataframe.drop(columns=["fare_amount"])
    
    with patch("src.extract.Path.exists") as mock_exists, \
        patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value = True
        mock_read.return_value = broken_df
        with pytest.raises(ExtractionError, match="Missing columns"):
            extract(test_source_file)


def test_extract_raises_on_empty_file(valid_dataframe, test_source_file):
    empty_df = valid_dataframe.iloc[0:0]

    with patch("src.extract.Path.exists") as mock_exists,\
        patch("src.extract.pd.read_parquet") as mock_read:
        mock_exists.return_value=True
        mock_read.return_value=empty_df
        with pytest.raises(ExtractionError, match="contains zero rows"):
            extract(test_source_file)

def test_extract_raises_on_missing_file(test_source_file):
    with pytest.raises(ExtractionError, match="Source file not found:"):
        extract(test_source_file)
