CREATE OR REPLACE TABLE gold.order_daily AS
SELECT
  CAST(order_ts AS DATE) AS order_date,
  currency,
  COUNT(*) AS order_count,
  SUM(gross_amount) AS gross_revenue
FROM silver.orders
GROUP BY 1, 2;
