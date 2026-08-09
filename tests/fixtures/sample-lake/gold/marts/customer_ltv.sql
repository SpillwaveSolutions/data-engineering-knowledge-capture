CREATE OR REPLACE VIEW gold.customer_ltv AS
SELECT
  customer_id,
  SUM(gross_amount) AS lifetime_value,
  COUNT(*) AS order_count
FROM silver.orders
GROUP BY customer_id;
