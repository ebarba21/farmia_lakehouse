# Motor de Ingesta Streaming - Placeholder Kafka
from pyspark.sql import functions as F

def ingesta_streaming_rate(target_path, checkpoint_path):
    df_stream = (spark.readStream
        .format("rate")
        .option("rowsPerSecond", 2)
        .load()
        .withColumn("event_ts", F.col("timestamp"))
        .withColumn("event_date", F.to_date("event_ts"))
        .withColumn("order_id", F.concat(F.lit("demo-order-"), F.col("value").cast("string")))
        .withColumn("customer_id", F.concat(F.lit("customer-"), (F.col("value") % 10).cast("string")))
        .withColumn("amount", (F.col("value") % 100 + 1).cast("double"))
        .withColumn("currency", F.lit("EUR"))
        .withColumn("ingest_ts", F.current_timestamp())
        .withColumn("datasource", F.lit("streaming_rate_demo")))
    
    query = (df_stream.writeStream
        .format("delta")
        .option("checkpointLocation", checkpoint_path)
        .partitionBy("event_date")
        .outputMode("append")
        .start(target_path))
    
    return query