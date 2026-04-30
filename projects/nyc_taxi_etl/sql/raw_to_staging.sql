DELETE FROM staging.yellow_trips
WHERE source_file = (
    SELECT source_file
    FROM raw.yellow_trips
    ORDER BY loaded_at DESC
    LIMIT 1
);

INSERT INTO staging.yellow_trips (
    pickup_at,             
    dropoff_at,            
    passenger_count,       
    trip_distance,         
    pickup_zone_id,        
    dropoff_zone_id,       
    fare_amount,
    tip_amount,            
    total_amount,          
    payment_type,          
    trip_duration_minutes,
    source_file
)
SELECT 
    tpep_pickup_datetime::TIMESTAMP AT TIME ZONE 'America/New_York',
    tpep_dropoff_datetime::TIMESTAMP AT TIME ZONE 'America/New_York',
    passenger_count::NUMERIC::SMALLINT,
    trip_distance::FLOAT,
    PULocationID::NUMERIC::SMALLINT,
    DOLocationID::NUMERIC::SMALLINT,
    fare_amount::NUMERIC(8, 2),
    tip_amount::NUMERIC(8, 2),
    total_amount::NUMERIC(8, 2),
    payment_type::NUMERIC::SMALLINT,
    EXTRACT(EPOCH FROM(tpep_dropoff_datetime::TIMESTAMP -  tpep_pickup_datetime::TIMESTAMP))/60,
    source_file
FROM raw.yellow_trips
 WHERE source_file = (
    SELECT source_file
    FROM raw.yellow_trips
    ORDER BY loaded_at DESC
    LIMIT 1
    )
    AND fare_amount ~ '^-?[0-9]+\.?[0-9]*$' 
    AND fare_amount::NUMERIC > 0
    AND total_amount ~ '^-?[0-9]+\.?[0-9]*$'
    AND total_amount::NUMERIC > 0
    AND trip_distance ~ '^-?[0-9]+\.?[0-9]*$'
    AND trip_distance::FLOAT > 0
    AND (passenger_count IS NULL OR passenger_count ~ '^-?[0-9]+\.?[0-9]*$')
    AND (tip_amount IS NULL OR tip_amount ~ '^-?[0-9]+\.?[0-9]*$')
    AND (payment_type IS NULL OR payment_type ~ '^-?[0-9]+\.?[0-9]*$')
    AND EXTRACT(EPOCH FROM(tpep_dropoff_datetime::TIMESTAMP - tpep_pickup_datetime::TIMESTAMP))/60 > 0
    AND EXTRACT(EPOCH FROM(tpep_dropoff_datetime::TIMESTAMP - tpep_pickup_datetime::TIMESTAMP))/60 <= 1440;
