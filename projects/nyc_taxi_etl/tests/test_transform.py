import pandas as pd
import pytest
from src.transform import transform
from src.exceptions import TransformationError


def _make_valid_row() -> dict:
    """
    Return a dictionary representing one clean, valid taxi trip.
    All business rules pass. Used as the baseline across tests
    """
    return{
        "tpep_pickup_datetime":  pd.Timestamp("2025-04-01 08:00:00"),
        "tpep_dropoff_datetime": pd.Timestamp("2025-04-01 08:30:00"),
        "passenger_count":       1.0,
        "trip_distance":         3.5,
        "PULocationID":          100,
        "DOLocationID":          200,
        "fare_amount":           15.0,
        "tip_amount":            3.0,
        "total_amount":          18.0,
        "payment_type":          1.0,
    }

# --- Test 1: A valid row passes through transform unchanged in count
def test_valid_row_survives():
    df = pd.DataFrame([_make_valid_row()])
    result = transform(df)
    assert len(result) == 1

# --- Test 2: Zero fare_amount is dropped
def test_zero_fare_is_dropped():
    good_row = _make_valid_row()
    bad_row = _make_valid_row()
    bad_row["fare_amount"] = 0.0
    df = pd.DataFrame([good_row, bad_row])
    result = transform(df)

    assert len(result) == 1
    assert (result["fare_amount"] > 0).all()

# --- Test 3: Zero trip_distance is dropped
def test_zero_distance_raises_transformation_error():
    good_row = _make_valid_row()
    bad_row = _make_valid_row()
    bad_row["trip_distance"] = 0.0
    df = pd.DataFrame([good_row, bad_row])

    result = transform(df)

    assert len(result) == 1
    assert (result["trip_distance"] > 0).all()

# --- Test 4: All rows are dropped
def test_all_rows_dropped_raises_transformation_error():
    row = _make_valid_row()
    row["fare_amount"] = 0.0
    df = pd.DataFrame([row])

    with pytest.raises(TransformationError, match = "zero rows"):
        transform(df)