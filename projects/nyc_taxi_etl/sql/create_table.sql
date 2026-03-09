CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.yellow_trips (
    trip_id         BIGSERIAL PRIMARY KEY,
    pickup_at       TIMESTAMP NOT NULL,
    dropoff_at      TIMESTAMP NOT NULL,
    passenger_count SMALLINT,
    trip_distance   NUMERIC(8, 2) NOT NULL,
    pickup_zone_id  SMALLINT NOT NULL,
    dropoff_zone_id SMALLINT NOT NULL,
    fare_amount     NUMERIC(8, 2) NOT NULL,
    tip_amount      NUMERIC(8, 2),
    total_amount    NUMERIC(8, 2) NOT NULL,
    payment_type    SMALLINT,
    trip_duration_minutes NUMERIC(6, 2),
    loaded_at       TIMESTAMP DEFAULT NOW()
);
