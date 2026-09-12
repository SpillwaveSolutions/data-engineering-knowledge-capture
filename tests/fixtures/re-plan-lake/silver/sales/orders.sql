CREATE OR REPLACE TABLE silver.orders AS
SELECT order_id, amount FROM bronze.orders_raw;
