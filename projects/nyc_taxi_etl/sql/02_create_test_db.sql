CREATE DATABASE taxi_db_test;

\c taxi_db_test

-- RAW LAYER
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.yellow_trips(
    trip_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    VendorID              TEXT,
    tpep_pickup_datetime  TEXT,
    tpep_dropoff_datetime TEXT,
    passenger_count       TEXT,
    trip_distance         TEXT,
    RatecodeID            TEXT,
    store_and_fwd_flag    TEXT,
    PULocationID          TEXT,
    DOLocationID          TEXT,
    payment_type          TEXT,
    fare_amount           TEXT,
    extra                 TEXT,
    mta_tax               TEXT,
    tip_amount            TEXT,
    tolls_amount          TEXT,
    improvement_surcharge TEXT,
    total_amount          TEXT,
    congestion_surcharge  TEXT,
    airport_fee           TEXT,
    cbd_congestion_fee    TEXT,
    loaded_at             TIMESTAMPTZ DEFAULT NOW()
);



-- STAGING LAYER
CREATE SCHEMA IF NOT EXISTS staging;
CREATE TABLE IF NOT EXISTS staging.yellow_trips (
    trip_id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pickup_at               TIMESTAMPTZ NOT NULL,
    dropoff_at              TIMESTAMPTZ NOT NULL,
    passenger_count         SMALLINT,
    trip_distance           FLOAT NOT NULL,
    pickup_zone_id          SMALLINT NOT NULL,
    dropoff_zone_id         SMALLINT NOT NULL,
    fare_amount             NUMERIC(8, 2) NOT NULL,
    tip_amount              NUMERIC(8, 2),
    total_amount            NUMERIC(8, 2) NOT NULL,
    payment_type            SMALLINT,
    trip_duration_minutes   NUMERIC(6, 2) NOT NULL,
    loaded_at               TIMESTAMPTZ DEFAULT NOW()
);


-- REPORTING LAYER
CREATE SCHEMA IF NOT EXISTS reporting;
CREATE TABLE IF NOT EXISTS reporting.daily_metrics(
    metric_date                 DATE PRIMARY KEY,
    total_trips                 INT NOT NULL,
    total_revenue               NUMERIC(10,2) NOT NULL,
    min_trip_distance           FLOAT NOT NULL,
    max_trip_distance           FLOAT NOT NULL,
    avg_trip_distance           FLOAT NOT NULL,
    min_fare_amount             NUMERIC(8,2) NOT NULL,
    max_fare_amount             NUMERIC(8,2) NOT NULL,
    avg_fare_amount             NUMERIC(8,2) NOT NULL,
    min_trip_duration_minutes   NUMERIC(8,2) NOT NULL,
    max_trip_duration_minutes   NUMERIC(8,2) NOT NULL,
    avg_trip_duration_minutes   NUMERIC(8,2) NOT NULL,
    loaded_at                   TIMESTAMPTZ DEFAULT NOW() NOT NULL 
);  