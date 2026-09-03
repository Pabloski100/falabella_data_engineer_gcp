CREATE OR REPLACE TABLE `project-951ccd40-2ae1-482a-a13.falabella_gcp_demo.top_customers` AS

WITH

cte_base_orders AS (
  SELECT
    customer_id
    ,CAST(total_amount AS NUMERIC) total_amount
  FROM `project-951ccd40-2ae1-482a-a13.falabella_gcp_demo.orders` 
)

,cte_base_customers AS (
  SELECT
    customer_id
    ,name
    ,country
    ,email
  FROM `project-951ccd40-2ae1-482a-a13.falabella_gcp_demo.customers` 
)

,cte_amount_by_customer AS (
  SELECT
    customer_id
    ,SUM(total_amount) customer_amount
  FROM cte_base_orders
  GROUP BY customer_id
)

,cte_customer_amount AS (
  SELECT
    name
    ,country
    ,email
    ,customer_amount
  FROM cte_base_customers
  LEFT JOIN cte_amount_by_customer
    USING (customer_id)
)

SELECT
  name
  ,email
  ,country
  ,customer_amount
FROM cte_customer_amount
QUALIFY ROW_NUMBER() OVER (PARTITION BY country ORDER BY customer_amount DESC) <= 3
