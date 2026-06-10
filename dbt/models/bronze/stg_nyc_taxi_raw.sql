-- Bronze Layer: Raw Data Ingestion (Simulating Fivetran sync)
-- Best Practice: Never mutate bronze data. Just cast and rename.

WITH source AS (
    SELECT *
    FROM {{ source('raw', 'nyc_taxi_2015') }}
)

SELECT
    vendor_id::VARCHAR AS vendor_id,
    tpep_pickup_datetime::TIMESTAMP AS pickup_datetime,
    tpep_dropoff_datetime::TIMESTAMP AS dropoff_datetime,
    passenger_count::INT AS passenger_count,
    trip_distance::FLOAT AS trip_distance,
    payment_type::INT AS payment_type,
    fare_amount::FLOAT AS fare_amount,
    tip_amount::FLOAT AS tip_amount,
    (tip_amount / NULLIF(fare_amount, 0))::FLOAT AS tip_pct,
    total_amount::FLOAT AS total_amount
FROM source
