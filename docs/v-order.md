# V-Order

## What It Is

V-Order is a write-time optimisation applied to Parquet files. It reorganises row-group distribution, encoding, and compression to improve read efficiency across Fabric engines — particularly for read-heavy patterns such as dashboarding, interactive analytics, and repeated scans.

The trade-off is write overhead: V-Order adds roughly **15% on average** to write time (up to 33% in some workloads).

**Read performance gains:**
- Power BI Direct Lake: 40–60% cold-cache improvement
- SQL Analytics Endpoint: ~10% improvement
- Spark: No inherent read benefit — V-Order is aimed at VertiPaq-compatible engines

## Fabric Default

**V-Order is OFF by default for all newly created Fabric workspaces.**
`spark.sql.parquet.vorder.default = false`

This changed in recent Fabric runtimes (confirmed on Runtime 1.3 / Spark 3.5.1 via `spark.conf.get("spark.sql.parquet.vorder.default")` returning `false`). Earlier documentation stated it was on by default — that is no longer accurate.

> **Documentation inconsistency:** The [Lakehouse and Delta Tables](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-and-delta-tables) defaults comparison table still lists V-Order as `true` in the Fabric Default column as of March 2026. The dedicated [Delta Optimization and V-Order](https://learn.microsoft.com/en-us/fabric/data-engineering/delta-optimization-and-v-order) page contradicts this, explicitly stating it is off by default for newly created workspaces. Trust the dedicated page and verify against your own environment.

## Recommendations by Layer

| Layer | Recommendation | Action Required |
|---|---|---|
| Bronze | **Off** | No action — already off by default |
| Silver | **Selective** | Explicitly enable via table property on tables feeding Direct Lake or SQL Endpoint; leave off for Spark-only tables |
| Gold | **On** | Explicitly enable at session level or via table property |

## Three Control Levels

V-Order can be controlled at three levels, in descending order of precedence:

### 1. Write operation (highest precedence)

Overrides both session and table property settings for that specific write:

```python
df.write \
  .format("delta") \
  .mode("append") \
  .option("parquet.vorder.enabled", "true") \
  .saveAsTable("my_catalog.gold.my_table")
```

### 2. Session level

Applies to all Parquet writes in the session, including non-Delta tables:

```python
# Enable for Gold notebooks
spark.conf.set("spark.sql.parquet.vorder.default", "true")

# Explicitly disable (already the default — use where you want to be explicit)
spark.conf.set("spark.sql.parquet.vorder.default", "false")
```

### 3. Table property (lowest precedence for writes; persists across sessions)

```sql
-- Enable on a specific Silver or Gold table
ALTER TABLE my_catalog.silver.my_table
SET TBLPROPERTIES ('delta.parquet.vorder.enabled' = 'true');

-- Disable on a specific table
ALTER TABLE my_catalog.silver.my_table
SET TBLPROPERTIES ('delta.parquet.vorder.enabled' = 'false');
```

**Note:** Session-level and write-level settings take precedence over table properties. A session with `vorder.default = true` will apply V-Order even if the table property is set to `false`.

## Applying V-Order to Existing Files

V-Order only applies to newly-written Parquet files. To re-encode existing files — for example when first enabling V-Order on a Gold table — run `OPTIMIZE VORDER`. This applies V-Order regardless of session and table property settings:

```sql
OPTIMIZE my_catalog.gold.my_table VORDER;
```

You can combine with Z-Order:

```sql
OPTIMIZE my_catalog.gold.my_table ZORDER BY (customer_id) VORDER;
```

## Note on the Session Config Notebook

V-Order is set explicitly to `false` as a baseline in `dopt_utility_session_config`. Since it is off by default in new workspaces, the explicit set establishes a known baseline regardless of workspace age or history. Enable it on top of this baseline:
- As a session config override at the top of Gold notebooks
- As a table property on individual Silver/Gold tables that are Direct Lake or SQL Endpoint sources

## References

- [Delta Optimization and V-Order — Microsoft Learn (official)](https://learn.microsoft.com/en-us/fabric/data-engineering/delta-optimization-and-v-order)
- [Cross-Workload Table Maintenance and Optimization — Microsoft Learn](https://learn.microsoft.com/en-us/fabric/fundamentals/table-maintenance-optimization)
- [Understand Direct Lake Query Performance — Microsoft Learn](https://learn.microsoft.com/en-us/fabric/fundamentals/direct-lake-understand-storage)
