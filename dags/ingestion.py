import os
from datetime import datetime
from airflow.sdk import DAG
from airflow.providers.google.cloud.transfers.postgres_to_gcs import PostgresToGCSOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator

BUCKET = os.environ["GCS_BUCKET"]
PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
DATASET = "falabella_gcp_demo"

with DAG(
    dag_id="ingest_to_bigquery",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    pg_customer_dump = PostgresToGCSOperator(
        task_id="dump_customers_to_gcs",
        postgres_conn_id="input_db",
        sql="SELECT * FROM customers",
        bucket=BUCKET,
        filename="staging/customers/{{ ds }}/part_{}.parquet",
        export_format="parquet",
        gzip=False,
        gcp_conn_id="google_cloud_default",
    )

    pg_orders_dump = PostgresToGCSOperator(
        task_id="dump_orders_to_gcs",
        postgres_conn_id="input_db",
        sql="""
            SELECT order_id,
                   customer_id,
                   order_date::text   AS order_date,
                   total_amount::text AS total_amount
            FROM orders
        """,
        bucket=BUCKET,
        filename="staging/orders/{{ ds }}/part_{}.parquet",
        export_format="parquet",
        gzip=False,
        gcp_conn_id="google_cloud_default",
    )

    load_customers = GCSToBigQueryOperator(
        task_id="load_customers",
        bucket=BUCKET,
        source_objects=["staging/customers/{{ ds }}/part_*.parquet"],
        destination_project_dataset_table=f"{PROJECT}.{DATASET}.customers",
        source_format="PARQUET",
        write_disposition="WRITE_TRUNCATE",
        gcp_conn_id="google_cloud_default",
    )

    load_orders = GCSToBigQueryOperator(
        task_id="load_orders",
        bucket=BUCKET,
        source_objects=["staging/orders/{{ ds }}/part_*.parquet"],
        destination_project_dataset_table=f"{PROJECT}.{DATASET}.orders",
        source_format="PARQUET",
        write_disposition="WRITE_TRUNCATE",
        gcp_conn_id="google_cloud_default",
    )

    load_shipments = GCSToBigQueryOperator(
        task_id="load_shipments_csv",
        bucket=BUCKET,
        source_objects=["source/shipments.csv"],
        destination_project_dataset_table=f"{PROJECT}.{DATASET}.shipments",
        source_format="CSV",
        skip_leading_rows=1,
        field_delimiter=",",
        encoding="UTF-8",
        write_disposition="WRITE_TRUNCATE",
        autodetect=False,
        schema_fields=[
            {"name": "shipment_id",   "type": "STRING",   "mode": "REQUIRED"},
            {"name": "order_id",      "type": "INTEGER",  "mode": "REQUIRED"},
            {"name": "status",        "type": "STRING",   "mode": "REQUIRED"},
            {"name": "shipped_date",  "type": "DATETIME", "mode": "NULLABLE"},
            {"name": "delivery_date", "type": "DATETIME", "mode": "NULLABLE"},
        ],
        gcp_conn_id="google_cloud_default",
    )


    pg_customer_dump >> load_customers
    pg_orders_dump >> load_orders
    