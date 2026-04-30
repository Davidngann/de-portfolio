INSERT INTO reporting.daily_metrics (
    metric_date,
    total_trips,
    total_revenue,
    min_trip_distance,
    max_trip_distance,
    avg_trip_distance,
    min_fare_amount,
    max_fare_amount,
    avg_fare_amount,
    min_trip_duration_minutes,
    max_trip_duration_minutes,
    avg_trip_duration_minutes
)
SELECT 
    DATE(pickup_at AT TIME ZONE 'America/New_York'),
    COUNT(*),
    SUM(total_amount),
    MIN(trip_distance),
    MAX(trip_distance),
    AVG(trip_distance),
    MIN(fare_amount),
    MAX(fare_amount),
    AVG(fare_amount),
    MIN(trip_duration_minutes),
    MAX(trip_duration_minutes),
    AVG(trip_duration_minutes)
FROM staging.yellow_trips
GROUP BY DATE(pickup_at AT TIME ZONE 'America/New_York')
ON CONFLICT(metric_date) DO UPDATE SET
    total_trips                 = EXCLUDED.total_trips,
    total_revenue               = EXCLUDED.total_revenue,
    min_trip_distance           = EXCLUDED.min_trip_distance,
    max_trip_distance           = EXCLUDED.max_trip_distance,
    avg_trip_distance           = EXCLUDED.avg_trip_distance,
    min_fare_amount             = EXCLUDED.min_fare_amount,
    max_fare_amount             = EXCLUDED.max_fare_amount,
    avg_fare_amount             = EXCLUDED.avg_fare_amount,
    min_trip_duration_minutes   = EXCLUDED.min_trip_duration_minutes,
    max_trip_duration_minutes   = EXCLUDED.max_trip_duration_minutes,
    avg_trip_duration_minutes   = EXCLUDED.avg_trip_duration_minutes,
    loaded_at                   = NOW()
;