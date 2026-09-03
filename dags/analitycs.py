import os
from datetime import datetime
from pathlib import Path

from airflow.sdk import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
DATASET = "falabella_gcp_demo"
SQL_DIR = Path("/opt/airflow/dags/sql")

with DAG(
    dag_id="bq_transformations",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    top_customers = BigQueryInsertJobOperator(
        task_id="top_customers",
        configuration={
            "query": {
                "query": (SQL_DIR / "top_customers.sql").read_text(),
                "useLegacySql": False,
            }
        },
        gcp_conn_id="google_cloud_default",
    )

    monthly_growth = BigQueryInsertJobOperator(
        task_id="monthly_growth",
        configuration={
            "query": {
                "query": (SQL_DIR / "monthly_growth.sql").read_text(),
                "useLegacySql": False,
            }
        },
        gcp_conn_id="google_cloud_default",
    )

    logistic_performance = BigQueryInsertJobOperator(
        task_id="logistic_performance",
        configuration={
            "query": {
                "query": (SQL_DIR / "logistic_performance.sql").read_text(),
                "useLegacySql": False,
            }
        },
        gcp_conn_id="google_cloud_default",
    )