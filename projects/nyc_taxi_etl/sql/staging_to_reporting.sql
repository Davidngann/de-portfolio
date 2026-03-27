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
    DATE(pickup_at),
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
GROUP BY DATE(pickup_at)
ON CONFLICT(metric_date) DO NOTHING;