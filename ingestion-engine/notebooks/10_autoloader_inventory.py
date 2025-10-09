# Motor de Ingesta Batch - Autoloader
from pyspark.sql import functions as F

def ingesta_batch_autoloader(source_path, target_path, checkpoint_path, schema_path):
    df_raw = (spark.readStream
              .format("cloudFiles")
              .option("cloudFiles.format", "csv")
              .option("cloudFiles.schemaLocation", schema_path)
              .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
              .option("header", "true")
              .option("cloudFiles.schemaHints", "sku STRING, qty INT, warehouse STRING, load_date DATE")
              .load(source_path))
    
    df_enriched = (df_raw
        .withColumn("ingest_ts", F.current_timestamp())
        .withColumn("ingest_date", F.to_date("ingest_ts"))
        .withColumn("datasource", F.lit("inventory_csv")))
    
    query = (df_enriched.writeStream
             .format("delta")
             .option("checkpointLocation", checkpoint_path)
             .option("mergeSchema", "true")
             .partitionBy("load_date")
             .outputMode("append")
             .start(target_path))
    
    return query