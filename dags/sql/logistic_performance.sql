CREATE OR REPLACE TABLE `project-951ccd40-2ae1-482a-a13.falabella_gcp_demo.logistic_performance` AS

WITH

cte_base_shipments AS (
  SELECT
    order_id
    ,DATE(delivery_date) AS delivery_date
  FROM `project-951ccd40-2ae1-482a-a13.falabella_gcp_demo.shipments`
  WHERE status = "Delivered"
)

,cte_base_orders AS (
  SELECT
    order_id
    ,DATE(order_date) AS order_date
  FROM `project-951ccd40-2ae1-482a-a13.falabella_gcp_demo.orders` 
)

,cte_days_to_deliver AS (
  SELECT
    order_id
    ,order_date
    ,delivery_date
    ,DATE_DIFF(delivery_date, order_date, DAY) AS days_to_deliver
  FROM cte_base_shipments
  LEFT JOIN cte_base_orders
    USING (order_id)
)

SELECT
  order_id
  ,order_date
  ,delivery_date
  ,days_to_deliver
  ,ROUND(AVG(days_to_deliver) OVER(), 2) AS avg_days_to_deliver
  ,IF(days_to_deliver <= 5, "A tiempo", "Atrasado") AS deivery_time_status
FROM cte_days_to_deliver
