# Validación de Datos - Batch y Streaming
import pyspark.sql.functions as F

def validar_datos_bronze(inventory_path, sales_path):
    # Validar inventory
    df_inventory = spark.read.format("delta").load(inventory_path)
    inventory_count = df_inventory.count()
    
    # Validar sales
    df_sales = spark.read.format("delta").load(sales_path) 
    sales_count = df_sales.count()
    
    return {
        "inventory": {"count": inventory_count, "columns": len(df_inventory.columns)},
        "sales_online": {"count": sales_count, "columns": len(df_sales.columns)}
    }