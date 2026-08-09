CREATE OR REPLACE TABLE bronze.orders_raw AS
SELECT * FROM landing.orders_api;
