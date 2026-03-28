import pandas as pd
import pytest
from src.transform import transform
from src.transform import DROP_IF_NULL
from src.exceptions import TransformationError

def test_valid_row_survives(valid_dataframe):
    result = transform(valid_dataframe)
    assert len(result) == 1

def test_zero_fare_is_dropped(valid_row):
    bad_row = {**valid_row, "fare_amount": 0.0}
    df = pd.DataFrame([valid_row, bad_row])
    result = transform(df)

    assert len(result) == 1
    assert (result["fare_amount"] > 0).all()

def test_zero_total_amount_is_dropped(valid_row):
    bad_row = {**valid_row, "total_amount": 0.0}
    df = pd.DataFrame([valid_row, bad_row])
    result = transform(df)

    assert len(result) == 1
    assert (result["total_amount"] > 0).all()


def test_zero_distance_is_dropped(valid_row):
    bad_row = {**valid_row, "trip_distance": 0.0}
    df = pd.DataFrame([valid_row, bad_row])
    result = transform(df)

    assert len(result) == 1
    assert (result["trip_distance"] > 0).all()

def test_all_rows_dropped_raises_transformation_error(valid_row):
    row = {**valid_row, "fare_amount": 0.0}
    df = pd.DataFrame([row])

    with pytest.raises(TransformationError, match = "zero rows"):
        transform(df)

def test_output_columns_are_renamed(valid_dataframe):
    result = transform(valid_dataframe)

    assert "pickup_at" in result.columns
    assert "dropoff_at" in result.columns
    assert "pickup_zone_id" in result.columns
    assert "dropoff_zone_id" in result.columns

    assert "tpep_pickup_datetime" not in result.columns
    assert "tpep_dropoff_datetime" not in result.columns
    assert "PULocationID" not in result.columns
    assert "DOLocationID" not in result.columns


def test_columns_datatype_is_correct(valid_dataframe):
    result = transform(valid_dataframe)

    assert result['pickup_at'].dtype == "datetime64[us]"
    assert result['dropoff_at'].dtype == "datetime64[us]"
    assert result['trip_distance'].dtype == "float64"
    assert result['fare_amount'].dtype == "float64"
    assert result['tip_amount'].dtype == "Float64"
    assert result['total_amount'].dtype == "float64"
    assert result['pickup_zone_id'].dtype == "int16"
    assert result['dropoff_zone_id'].dtype == "int16"
    assert result['passenger_count'].dtype == "Int8"
    assert result['payment_type'].dtype == "Int8"

def test_transform_raises_on_missing_columns(valid_dataframe):
    broken_df = valid_dataframe.drop(columns=["fare_amount"])
    with pytest.raises(TransformationError, match="Missing columns"):
        transform(broken_df)

def test_row_is_dropped_when_required_columns_are_null(valid_row):
    bad_row = {**valid_row, **{col: pd.NA for col in DROP_IF_NULL}}
    df = pd.DataFrame([valid_row, bad_row])
    result = transform(df)
    
    assert len(result) == 1


def test_row_is_kept_when_nullable_columns_are_null(valid_row):
    NOT_DROP_IF_NULL = ['passenger_count', 'tip_amount', 'payment_type']
    row = {**valid_row, **{col: pd.NA for col in NOT_DROP_IF_NULL}}
    df = pd.DataFrame([row])
    result = transform(df)

    assert len(result) == 1
    assert pd.isna(result['passenger_count'].iloc[0])
    assert pd.isna(result['tip_amount'].iloc[0])
    assert pd.isna(result['payment_type'].iloc[0])

def test_trip_duration_is_calculated_correctly(valid_dataframe):
    result = transform(valid_dataframe)

    assert result["trip_duration_minutes"].iloc[0] == 30.0
    

def test_negative_trip_duration_minutes_is_dropped(valid_row):
    bad_row = {**valid_row, "tpep_pickup_datetime": pd.Timestamp("2025-04-01 08:30:00"),
            "tpep_dropoff_datetime": pd.Timestamp("2025-04-01 08:00:00")}
    df = pd.DataFrame([valid_row, bad_row])
    result = transform(df)

    assert len(result) == 1
    assert (result["trip_duration_minutes"] > 0).all()


def test_excess_trip_duration_minutes_is_dropped(valid_row):
    bad_row = {**valid_row, "tpep_pickup_datetime": pd.Timestamp("2025-04-01 08:00:00"),
            "tpep_dropoff_datetime": pd.Timestamp("2025-04-02 08:01:00")}
    df = pd.DataFrame([valid_row, bad_row])
    result = transform(df)

    assert len(result) == 1
    assert (result["trip_duration_minutes"] <= 1440).all()


def test_rows_counted_correctly(valid_row):
    rows = [
        valid_row,                                                          # survives       
        {**valid_row, "fare_amount": 0.0},                                  # dropped — business rule
        {**valid_row, "trip_distance": 0.0},                                # dropped — business rule
        {**valid_row, "tpep_pickup_datetime": pd.NaT},                      # dropped — must not null required column 
        {**valid_row,                                                       # dropped — negative duration
            "tpep_pickup_datetime":  pd.Timestamp("2025-04-01 08:30:00"),
            "tpep_dropoff_datetime": pd.Timestamp("2025-04-01 08:00:00")},
        {**valid_row, "passenger_count": pd.NA},                            # survives
    ]
    df = pd.DataFrame(rows)
    result = transform(df)

    assert len(result) == 2


