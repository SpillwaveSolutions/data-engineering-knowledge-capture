-- duckdb local extract
SELECT * FROM read_parquet('lake/orders/*.parquet');
