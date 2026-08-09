CREATE OR REPLACE TABLE silver.orders AS
SELECT
  order_id,
  customer_id,
  order_ts,
  status,
  gross_amount,
  currency
FROM bronze.orders_raw
WHERE status IS NOT NULL;
