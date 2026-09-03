CREATE OR REPLACE TABLE `{{ params.project }}.{{ params.dataset }}.monthly_growth` AS

WITH

cte_base AS (
  SELECT
    CAST(order_date AS DATETIME) order_date
    ,CAST(total_amount AS NUMERIC) total_amount
  FROM `{{ params.project }}.{{ params.dataset }}.orders` 
)

,cte_orders_by_month AS (
  SELECT
    DATE_TRUNC(DATE(order_date), MONTH) AS month_start
    ,SUM(total_amount) AS monthly_amount
  FROM cte_base
  GROUP BY month_start
)

,cte_order_past AS (
  SELECT
    c.month_start,
    c.monthly_amount,
    p.monthly_amount AS monthly_amount_prev
  FROM cte_orders_by_month AS c
  LEFT JOIN cte_orders_by_month AS p
    ON p.month_start = DATE_SUB(c.month_start, INTERVAL 1 MONTH)
  ORDER BY c.month_start
)

SELECT
  month_start
  ,monthly_amount
  ,monthly_amount_prev
  ,ROUND(((monthly_amount - monthly_amount_prev) / monthly_amount_prev) * 100, 2) AS mom_pct
FROM cte_order_past
