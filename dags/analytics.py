import os
from datetime import datetime

from airflow.sdk import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
DATASET = os.environ["BQ_DATASET"]
LOCATION = os.environ["BQ_LOCATION"]

with DAG(
    dag_id="bq_transformations",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    params={
        "project": PROJECT,
        "dataset": DATASET
    }
) as dag:

    transformations = [
        "top_customers",
        "monthly_growth",
        "logistic_performance"
    ]

    for name in transformations:
        BigQueryInsertJobOperator(
            task_id=name,
            configuration={
                "query": {
                    "query": f"sql/{name}.sql",
                    "useLegacySql": False,
                }
            },
            location=LOCATION,
            gcp_conn_id="google_cloud_default",
        )
