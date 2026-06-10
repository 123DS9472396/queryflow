-- Silver Layer: Cleansed and Filtered Data
-- Best Practice: Filter outliers, map enums, standardize formats.

WITH raw_data AS (
    SELECT *
    FROM {{ ref('stg_nyc_taxi_raw') }}
)

SELECT
    pickup_datetime,
    dropoff_datetime,
    date_diff('minute', pickup_datetime, dropoff_datetime) AS duration_min,
    passenger_count,
    trip_distance,
    -- Map payment type codes to readable strings
    CASE payment_type
        WHEN 1 THEN 'Credit card'
        WHEN 2 THEN 'Cash'
        WHEN 3 THEN 'No charge'
        WHEN 4 THEN 'Dispute'
        ELSE 'Other'
    END AS payment_method,
    fare_amount,
    tip_pct,
    total_amount
FROM raw_data
WHERE 
    trip_distance > 0 
    AND trip_distance < 100
    AND passenger_count > 0
    AND total_amount > 0
