# Medallion Layer Recommendations

Quick reference for recommended settings by layer. Links to detail files for the reasoning behind each decision.

**Important:** Fabric has different defaults from what many practitioners expect. `optimizeWrite` is **on by default** in Fabric. V-Order is **off by default** for new Fabric workspaces (Runtime 1.3+) — actions at Silver/Gold are explicit *enables*, not disables. See [spark-config-utility.md](./spark-config-utility.md) and [v-order.md](./v-order.md).

## Bronze (Landing / Raw)

Purpose: ingest raw source data as fast as possible with minimal transformation.

| Setting | Action | Notes |
|---|---|---|
| `autoCompact.enabled` | Enable (`true`) | Prevent small file accumulation from frequent intraday loads |
| `targetFileSize.adaptive.enabled` | Enable (`true`) | Let ATFS tune compaction target |
| `optimizeWrite.enabled` | **Disable (`false`)** for append-only loads | On by default — leave at default for MERGE notebooks; disable for append-only batch loads |
| `optimize.fast.enabled` | Enable (`true`) | No downside |
| `optimize.fileLevelTarget.enabled` | Enable (`true`) | Officially recommended by Microsoft |
| V-Order | No action needed | Off by default in new Fabric workspaces — no Direct Lake/SQL Endpoint consumers at Bronze; write penalty not justified if enabled |
| Deletion Vectors | Enable for tables with MERGE patterns | See [deletion-vectors.md](./deletion-vectors.md) |
| Scheduled OPTIMIZE | Not needed for append-only loads; run after MERGE-heavy loads | Auto-compaction sufficient for simple appends |
| VACUUM | Weekly, retain 168h | High write volume |

---

## Silver (Curated / Conformed)

Purpose: cleansed, joined, business-rule-applied data. May feed Direct Lake semantic models directly.

| Setting | Action | Notes |
|---|---|---|
| `autoCompact.enabled` | Enable (`true`) | |
| `targetFileSize.adaptive.enabled` | Enable (`true`) | |
| `optimizeWrite.enabled` | **Leave default (`true`)** for MERGE notebooks; **disable (`false`)** for append-only batch loads | MERGE/UPDATE/DELETE operations benefit from pre-write bin packing; append-only batch loads don't |
| `optimize.fast.enabled` | Enable (`true`) | |
| `optimize.fileLevelTarget.enabled` | Enable (`true`) | |
| V-Order | **Selective** | Off by default — explicitly enable via table property for tables feeding Direct Lake/SQL Endpoint. Leave off for Spark-only Silver tables |
| Deletion Vectors | Enable for tables with frequent updates | |
| Liquid Clustering | **Recommended** | Preferred over partitioning for new Silver tables; use Z-Order only on already-partitioned tables |
| Scheduled OPTIMIZE | **Run aggressively** | Auto-compaction alone is insufficient for SQL/BI consumers; run after each load or on a schedule |
| VACUUM | Weekly, retain 168h | |

---

## Gold (Analytics / Consumption)

Purpose: aggregated, presentation-ready data. Primary source for Power BI Direct Lake and SQL Endpoint.

| Setting | Action | Notes |
|---|---|---|
| `autoCompact.enabled` | Enable (`true`) | |
| `targetFileSize.adaptive.enabled` | Enable (`true`) | |
| `optimizeWrite.enabled` | **Leave default (`true`)** for MERGE notebooks; **disable (`false`)** for append-only batch loads | Same rule as Silver — MERGE notebooks exist at every layer |
| `optimize.fast.enabled` | Enable (`true`) | Has no effect on Liquid Clustered tables — full OPTIMIZE always runs there |
| `optimize.fileLevelTarget.enabled` | Enable (`true`) | |
| V-Order | **Enable** | Off by default in new Fabric workspaces — explicitly enable at session level for all Gold notebooks; use `OPTIMIZE VORDER` to re-encode existing files |
| Deletion Vectors | Enable; minimise accumulation via regular compaction | Accumulated deletion vectors add overhead to Direct Lake cold-state loading |
| Liquid Clustering | **Required** | Optimal file skipping for Gold consumers; data is only clustered when OPTIMIZE runs |
| Scheduled OPTIMIZE | **Run aggressively** | Required for Liquid Clustering to take effect, Direct Lake deletion vector cleanup, and hitting 400 MB–1 GB file size targets |
| VACUUM | Weekly, retain 168h | Respect Direct Lake framing window before running |

### Gold File Size Targets by Consumption Engine

| Engine | Target file size | Row group size |
|---|---|---|
| SQL Analytics Endpoint | ~400 MB | ~2 million rows |
| Power BI Direct Lake | 400 MB to 1 GB | 8+ million rows |
| Spark | 128 MB to 1 GB (ATFS-managed) | 1–2 million rows |

---

## Session Config by Layer

### Shared utility (all layers)

```python
spark.conf.set("spark.sql.caseSensitive", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
spark.conf.set("spark.microsoft.delta.targetFileSize.adaptive.enabled", "true")
spark.conf.set("spark.microsoft.delta.optimize.fast.enabled", "true")
spark.conf.set("spark.microsoft.delta.optimize.fileLevelTarget.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")   # explicit baseline
spark.conf.set("spark.sql.parquet.vorder.default", "false")               # explicit baseline
```

### Bronze notebooks (add after calling session config)

```python
# Disable optimizeWrite for append-only Bronze ingest — shuffle overhead not justified
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "false")
# V-Order: no action needed — off by default; no Direct Lake consumers at Bronze
```

### Gold notebooks (add after calling session config)

```python
# Enable V-Order — consumer-facing layer; read performance gains fully realised
spark.conf.set("spark.sql.parquet.vorder.default", "true")
```

### Append-only batch notebooks at Silver — any layer

```python
# Disable optimizeWrite for append-only batch loads — shuffle overhead not justified
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "false")
# V-Order: enable via table property on tables feeding Direct Lake/SQL Endpoint (see v-order.md)
```

### MERGE / UPDATE / DELETE notebooks — any layer

```python
# Leave optimizeWrite at default (true) — pre-write bin packing reduces compaction pressure
# No override needed
```

---

## Detail Files

- [spark-config-utility.md](./spark-config-utility.md) — full setting reference, Fabric defaults, and optimizeWrite guidance
- [v-order.md](./v-order.md) — V-Order trade-offs, Fabric default, and when to disable
- [compaction-and-file-management.md](./compaction-and-file-management.md) — auto-compaction and ATFS explained
- [optimize-vacuum.md](./optimize-vacuum.md) — when to run OPTIMIZE/VACUUM, table health diagnostics
- [liquid-clustering.md](./liquid-clustering.md) — why partitioning is discouraged and how liquid clustering works
- [deletion-vectors.md](./deletion-vectors.md) — deletion vectors, compaction and Direct Lake implications
