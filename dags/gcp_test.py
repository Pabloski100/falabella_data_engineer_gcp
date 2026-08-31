from datetime import datetime
from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator

with DAG(
    dag_id="bq_impersonation_smoke_test",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    whoami = BigQueryInsertJobOperator(
        task_id="whoami",
        gcp_conn_id="google_cloud_default",
        configuration={
            "query": {
                "query": "SELECT SESSION_USER() AS running_as, CURRENT_TIMESTAMP() AS ts",
                "useLegacySql": False,
            }
        },
        location="US",
    )