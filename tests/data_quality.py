import logging
import sys

# Enterprise Data Quality & Observability (Great Expectations concept)
# In a real production environment, this would run as an Airflow task 
# right before the data hits the ClickHouse 'Gold' layer.

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_fare_amounts_are_positive(df_mock):
    """Expectation: Fare amounts cannot be negative."""
    invalid_fares = [row for row in df_mock if row['fare_amount'] < 0]
    if invalid_fares:
        raise ValueError(f"Data Quality Alert: Found {len(invalid_fares)} rows with negative fares!")
    logging.info("PASS: All fare amounts are strictly positive.")

def test_trip_distance_within_bounds(df_mock):
    """Expectation: Trip distance must be between 0.1 and 200 miles."""
    invalid_distances = [row for row in df_mock if not (0.1 <= row['trip_distance'] <= 200)]
    if invalid_distances:
        raise ValueError("Data Quality Alert: Trip distances found outside physical bounds of NYC.")
    logging.info("PASS: All trip distances are within NYC boundaries.")

def test_no_null_payment_methods(df_mock):
    """Expectation: Payment method cannot be null."""
    null_payments = [row for row in df_mock if row['payment_method'] is None]
    if null_payments:
        raise ValueError("Data Quality Alert: Null payment methods detected.")
    logging.info("PASS: No null payment methods detected.")

if __name__ == "__main__":
    logging.info("Starting Data Quality checks for Gold Layer pipeline...")
    
    # Mock data representing a sample pulled from the Silver layer
    mock_silver_data = [
        {'fare_amount': 12.50, 'trip_distance': 2.3, 'payment_method': 'Credit card'},
        {'fare_amount': 45.00, 'trip_distance': 15.1, 'payment_method': 'Cash'},
        {'fare_amount': 6.00, 'trip_distance': 0.8, 'payment_method': 'Credit card'}
    ]
    
    try:
        test_fare_amounts_are_positive(mock_silver_data)
        test_trip_distance_within_bounds(mock_silver_data)
        test_no_null_payment_methods(mock_silver_data)
        logging.info("SUCCESS: All Data Quality pipelines passed. Ready for Gold layer insertion.")
        sys.exit(0)
    except ValueError as e:
        logging.error(e)
        sys.exit(1)
