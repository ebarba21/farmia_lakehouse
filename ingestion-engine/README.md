# Farmia Lakehouse — Guía de ejecución (ADLS + Databricks)

> Proyecto del módulo **Diseño de ingestas y lagos de datos (UCM)**.  
> Entorno probado con: Azure for Students (France Central), Azure Databricks Standard, DBR 14/15 LTS, ADLS Gen2 (HNS ON).

---

## 1) Arquitectura (resumen)
- **Contenedores ADLS**: `landing`, `bronze`, `silver`, `gold`, `checkpoints`, `logs`.
- **Batch**: Autoloader (CSV) `landing/logistica/inventory` → **Delta** en `bronze/logistica/inventory` con **checkpoint** y **schemaLocation** en `checkpoints`.
- **Streaming (placeholder)**: `rate` → Delta en `bronze/ventas/sales_online` (mismo patrón que Kafka).
- **Rutas ABFSS** con storage: **`strgfarmialakehouse`**.
- **Databricks**: cluster **single node**, secreto con **Account Key** (vía Secret Scope).

---

## 2) Prerrequisitos
- **Resource Group**: `rg-farmia-lakehouse` (francecentral).
- **Storage Account**: `strgfarmialakehouse` con **HNS** activado.
- **Contenedores**: `landing`, `bronze`, `silver`, `gold`, `checkpoints`, `logs`.
- **Azure Databricks**: Workspace `dbw-farmia-lakehouse` y cluster `clu-farmia-lts` (DBR 14/15 LTS, Single node).

> Recomendación de Students: VM 2 vCPU (p.ej. `Standard_D2as_v5` / `Standard_D2ads_v6`) y **Terminate after** 60–120 min.

---

## 3) Credenciales y secreto (Standard tier)
1. **PAT** (token personal): en Databricks → avatar (arriba dcha) → **User settings** → **Developer** → **Access tokens** → *Generate new token*.
2. **Databricks CLI** en tu PC:
   ```bash
   databricks configure --host https://adb-4493380183488355.15.azuredatabricks.net --token
   ```
3. **Secret scope** (Standard tier exige `--initial-manage-principal users`):
   ```bash
   databricks secrets create-scope --scope farmia-secrets --initial-manage-principal users
   databricks secrets put --scope farmia-secrets --key storage-account-key --string-value "<KEY1>"
   ```
   Donde `<KEY1>` es la **Account Key** del storage:
   ```bash
   az storage account keys list -n strgfarmialakehouse -g rg-farmia-lakehouse -o table
   ```

4. **Spark config** (en el cluster → *Edit* → *Advanced* → *Spark*):
   ```
   spark.hadoop.fs.azure.account.key.strgfarmialakehouse.dfs.core.windows.net {{secrets/farmia-secrets/storage-account-key}}
   ```
   Guarda y **Restart** del cluster.

---

## 4) Ajustes del Storage (importante)
En **Portal Azure** → Storage `strgfarmialakehouse` → **Data protection**:  
**Soft delete (blobs/containers)**, **Versioning**, **Change feed** = **OFF**.  
**Events** → **Event Subscriptions** = **0** (ninguna).

> Si no desactivas esto, el endpoint DFS devuelve 409 en escrituras.

---

## 5) Smoke test rápido
Notebook `00_smoke_adls`:
```python
stacc = "strgfarmialakehouse"
p = f"abfss://logs@{stacc}.dfs.core.windows.net/smoke/parquet"
spark.range(5).show()
spark.createDataFrame([(1,"ok")], ["id","msg"]).write.mode("overwrite").parquet(p)
display(spark.read.parquet(p))
```

---

## 6) Ingesta batch con Autoloader (inventory)
Notebook `10_autoloader_inventory` (resumen):
- **Fuente**: `abfss://landing@strgfarmialakehouse.dfs.core.windows.net/logistica/inventory`
- **Destino (Delta)**: `abfss://bronze@strgfarmialakehouse.dfs.core.windows.net/logistica/inventory`
- **Checkpoint**: `abfss://checkpoints@strgfarmialakehouse.dfs.core.windows.net/batch/logistica/inventory`
- **SchemaLocation**: `abfss://checkpoints@strgfarmialakehouse.dfs.core.windows.net/schemas/logistica/inventory`
- **Schema evolution**: `addNewColumns` (usando `cloudFiles.schemaHints` **string**)
- **Metadatos**: `ingest_ts`, `ingest_date`, `datasource`
- **Partición**: `load_date`
- **Para procesar ficheros ya existentes**:
  ```python
  .option("cloudFiles.includeExistingFiles", "true")
  .trigger(availableNow=True)
  ```

---

## 7) Validación (bronze/logistica/inventory)
Notebook `11_validate_inventory`:
- `printSchema()`, `count()`, `distinct(load_date)`, *top 10 recientes*.
- Rutas/particiones en el path (debe aparecer `load_date=YYYY-MM-DD/`).

**SQL opcional** (tabla externa):
```sql
CREATE TABLE IF NOT EXISTS bronze_logistica_inventory
USING delta
LOCATION 'abfss://bronze@strgfarmialakehouse.dfs.core.windows.net/logistica/inventory';
SELECT * FROM bronze_logistica_inventory ORDER BY ingest_ts DESC LIMIT 20;
```

---

## 8) Streaming (placeholder sin Kafka)
Notebook `20_streaming_placeholder` (fuente `rate` → Delta en `bronze/ventas/sales_online` con partición por `event_date`).  
Cuando tengas broker, cambia `.format("rate")` por `.format("kafka")` y parametriza `bootstrap.servers`, `subscribe`, etc.

---

## 9) Mantenimiento Delta (opcional)
```sql
OPTIMIZE delta.`abfss://bronze@strgfarmialakehouse.dfs.core.windows.net/logistica/inventory` ZORDER BY (sku);
VACUUM  delta.`abfss://bronze@strgfarmialakehouse.dfs.core.windows.net/logistica/inventory` RETAIN 168 HOURS;
```

---

## 10) Problemas típicos y solución
- **409 BlobStorageEvents/SoftDelete**: desactiva *Data protection* y *Event Subscriptions* (ver sección 4).
- **Quota/cores**: usa cluster **Single node** 2 vCPU (DBR LTS) o cambia de región.
- **Secret scope en Standard**: crear con `--initial-manage-principal users`.
- **Ficheros no se cargan**: Autoloader por defecto no procesa históricos → usa `includeExistingFiles` + `availableNow` o sube un nuevo fichero tras arrancar.

---

## 11) Estructura del repo sugerida
```
ingestion-engine/
├─ notebooks/
│  ├─ 00_smoke_adls.py
│  ├─ 10_autoloader_inventory.py
│  ├─ 11_validate_inventory.py
│  └─ 20_streaming_placeholder.py
├─ conf/
│  ├─ batch/inventory.yaml
│  └─ streaming/sales_online.yaml
├─ schemas/      # (si defines esquemas fijos)
└─ README.md     # este archivo
```

---

## 12) Créditos
Máster Big Data & Data Engineering (UCM) — Módulo *Diseño de ingestas y data lakes*.
