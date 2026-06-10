from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.fivetran.operators.fivetran import FivetranOperator

# Default arguments for the DAG
default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    'nyc_taxi_medallion_pipeline',
    default_args=default_args,
    description='Enterprise ETL Pipeline: Fivetran -> dbt -> ClickHouse',
    schedule_interval='@daily',
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['enterprise', 'medallion', 'clickhouse'],
) as dag:

    start_pipeline = DummyOperator(task_id='start_pipeline')

    # Step 1: Trigger Fivetran to extract raw data and load into Bronze layer
    # Note: connector_id is a placeholder for the actual Fivetran connector ID
    fivetran_sync_raw = FivetranOperator(
        task_id='fivetran_sync_raw_taxi_data',
        connector_id='taxi_raw_ingestion_123',
        poke_interval=60,
    )

    # Step 2: Run dbt to clean data (Bronze -> Silver)
    dbt_run_silver = BashOperator(
        task_id='dbt_run_silver_layer',
        bash_command='cd /opt/airflow/dbt && dbt run --models silver',
    )

    # Step 3: Run dbt to aggregate data (Silver -> Gold)
    dbt_run_gold = BashOperator(
        task_id='dbt_run_gold_layer',
        bash_command='cd /opt/airflow/dbt && dbt run --models gold',
    )

    # Step 4: Run dbt tests to ensure data quality
    dbt_test = BashOperator(
        task_id='dbt_test_quality',
        bash_command='cd /opt/airflow/dbt && dbt test',
    )

    end_pipeline = DummyOperator(task_id='end_pipeline')

    # Define DAG dependencies
    start_pipeline >> fivetran_sync_raw >> dbt_run_silver >> dbt_run_gold >> dbt_test >> end_pipeline
