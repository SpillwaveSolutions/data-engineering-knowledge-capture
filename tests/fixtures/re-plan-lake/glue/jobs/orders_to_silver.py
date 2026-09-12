from awsglue.context import GlueContext
from pyspark.context import SparkContext

glue = GlueContext(SparkContext.getOrCreate())
# lands bronze.orders_raw → silver.orders (fiction)
