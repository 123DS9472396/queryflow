-- Gold Layer: Aggregated Data Mart (Ready for LangChain / Power BI)
-- Best Practice: Aggregated for low-latency BI dashboards.

WITH cleaned_data AS (
    SELECT *
    FROM {{ ref('int_trips_cleaned') }}
)

SELECT
    toDate(pickup_datetime) AS pickup_date,
    toHour(pickup_datetime) AS pickup_hour,
    toDayOfWeek(pickup_datetime) AS day_of_week,
    payment_method,
    
    -- Aggregations
    count(*) AS total_trips,
    sum(total_amount) AS total_revenue,
    avg(trip_distance) AS avg_distance,
    avg(duration_min) AS avg_duration_min,
    avg(tip_pct) AS avg_tip_pct,
    sum(passenger_count) AS total_passengers

FROM cleaned_data
GROUP BY 
    pickup_date,
    pickup_hour,
    day_of_week,
    payment_method
ORDER BY 
    pickup_date DESC, 
    pickup_hour DESC
