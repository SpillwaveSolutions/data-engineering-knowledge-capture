CREATE TABLE gold.order_daily AS
SELECT order_date, SUM(amount) AS gmv FROM silver.orders GROUP BY 1;
