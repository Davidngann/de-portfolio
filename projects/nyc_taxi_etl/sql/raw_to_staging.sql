WITH get_source_file AS(
    SELECT 
        %(source_file)s::TEXT AS source_file,
        TO_DATE(SUBSTRING(%(source_file)s FROM '\d{4}-\d{2}'), 'YYYY-MM') AS month_start
),
deleted AS(
DELETE FROM staging.yellow_trips s
USING get_source_file g
WHERE s.source_file = g.source_file
)
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
    r.source_file
FROM raw.yellow_trips r
JOIN get_source_file g USING (source_file)
WHERE tpep_pickup_datetime IS NOT NULL
    AND tpep_dropoff_datetime IS NOT NULL
    AND PULocationID IS NOT NULL
    AND DOLocationID IS NOT NULL
    AND trip_distance IS NOT NULL
    AND fare_amount IS NOT NULL
    AND total_amount IS NOT NULL
    AND tpep_pickup_datetime::TIMESTAMP AT TIME ZONE 'America/New_York' >= g.month_start - INTERVAL '1 day'
    AND tpep_pickup_datetime::TIMESTAMP AT TIME ZONE 'America/New_York' < g.month_start + INTERVAL '1 month' + INTERVAL '1 day'
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
