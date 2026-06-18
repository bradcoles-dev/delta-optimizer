# Deployment Validation Guide

A structured set of acceptance tests to validate that delta-optimizer is working correctly in your Fabric workspace before using it in production. Run through each section in order — each notebook is tested in isolation before the orchestrators are validated.

## Prerequisites

- All six notebooks are imported into your Fabric workspace
- At least one Lakehouse with Delta tables exists in the same workspace
- The Lakehouse GUID is ready (see [Getting Started](../README.md#getting-started) for how to find it)
- All notebooks reside in the same Fabric workspace as the target Lakehouse

## Test Environment

**Minimum setup:** One Lakehouse with 3–5 Delta tables, at least one of which has multiple small files (a few sequential writes will create this naturally).

If you need test tables, run the following in a Fabric notebook attached to your Lakehouse:

```python
# Creates two tables with fragmentation for realistic test results
for i in range(5):
    spark.range(10000).write.format("delta").mode("append").saveAsTable("dopt_test_table_a")
for i in range(3):
    spark.range(5000).write.format("delta").mode("append").saveAsTable("dopt_test_table_b")
```

**Optional:** A schema-enabled Lakehouse for [Section 7](#7-schema-enabled-lakehouse-validation-optional).

---

## 1. dopt_utility_session_config

Validates layer-driven Spark session configuration.

### 1.1 — Bronze
| Parameter | Value |
|---|---|
| `layer` | `bronze` |

**Expected:**
```
Layer: bronze
Baseline configuration applied.
Bronze override applied: Optimize Write disabled (append-only batch loads).

Session configuration complete for layer: bronze
```

### 1.2 — Silver
| Parameter | Value |
|---|---|
| `layer` | `silver` |

**Expected:**
```
Layer: silver
Baseline configuration applied.
Silver: no overrides - baseline is correct for this layer.

Session configuration complete for layer: silver
```

### 1.3 — Gold
| Parameter | Value |
|---|---|
| `layer` | `gold` |

**Expected:**
```
Layer: gold
Baseline configuration applied.
Gold override applied: V-Order enabled (Direct Lake and SQL Endpoint consumers).

Session configuration complete for layer: gold
```

### 1.4 — Custom
| Parameter | Value |
|---|---|
| `layer` | `custom` |
| `custom_optimize_write` | `true` |
| `custom_v_order` | `false` |

**Expected:**
```
Layer: custom
Baseline configuration applied.
Custom override applied: Optimize Write = true, V-Order = false.

Session configuration complete for layer: custom
```

### 1.5 — Invalid layer
| Parameter | Value |
|---|---|
| `layer` | `platinum` |

**Expected:** `ValueError` raised listing valid layer values.

---

## 2. dopt_utility_table_health

Validates table enumeration, health metrics, and status classification. This is read-only — safe to run at any time.

### 2.1 — Basic scan
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `layer` | `silver` |

**Expected:**
- One row per Delta table in the Lakehouse
- `num_files`, `avg_file_mb`, `size_gb` populated for all tables
- `status` is one of: `Healthy`, `Review`, `Needs OPTIMIZE`, `Skip - single file`, `Skip - empty table` (zero-file tables), `No target set` (custom mode without a target MB specified)
- `schema` column is empty (non-schema Lakehouse)
- Run completes in seconds — no data scan

### 2.2 — Layer target effect
Re-run with `layer = "bronze"` then `layer = "gold"`. Verify that `status` values shift as expected — more tables show `Healthy` at the Bronze (128 MB) target than at the Gold (400 MB) target.

### 2.3 — Custom mode with target
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `layer` | `custom` |
| `custom_target_mb` | `200` |

**Expected:** Status classification uses 200 MB as the threshold.

### 2.4 — Custom mode without target
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `layer` | `custom` |
| `custom_target_mb` | `0` |

**Expected:** All rows show `No target set` in the `status` column; all other metrics populated normally.

### 2.5 — Missing lakehouse_guid
| Parameter | Value |
|---|---|
| `lakehouse_guid` | `""` |

**Expected:** `ValueError` raised immediately — no scan attempted.

---

## 3. dopt_utility_set_table_properties

Validates that Delta table properties are applied correctly per layer.

### 3.1 — Silver layer
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | Any table from your Lakehouse |
| `layer` | `silver` |

**Expected output lists all five properties:**
```
delta.enableDeletionVectors = true
delta.autoOptimize.autoCompact = true
delta.autoOptimize.optimizeWrite = true
delta.parquet.vorder.enabled = false
delta.targetFileSize = 268435456
```

**Verify:** Re-run `dopt_utility_table_health` — the table should now show `deletion_vectors = true`.

### 3.2 — Gold layer
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | Any table |
| `layer` | `gold` |

**Expected:** `delta.parquet.vorder.enabled = true` and `delta.targetFileSize = 419430400`.

### 3.3 — Liquid clustering
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | A non-partitioned table |
| `layer` | `gold` |
| `cluster_by` | A column name that exists in the table |

**Expected:** Properties set, followed by (note two leading spaces on the clustering lines):
```
  liquid clustering enabled on: {column}
  Note: clustering is applied physically on the next OPTIMIZE run.
```

**Verify:** Re-run `dopt_utility_table_health` — the table should show `liquid_clustering = true`.

### 3.4 — Custom mode (selective)
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | Any table |
| `layer` | `custom` |
| `custom_deletion_vectors` | `true` |
| `custom_auto_compact` | `""` |
| `custom_optimize_write` | `""` |
| `custom_v_order` | `""` |
| `custom_target_file_size_mb` | `0` |

**Expected:** Only `delta.enableDeletionVectors` is set. All skipped properties are unchanged.

### 3.5 — Missing parameters
Run with empty `lakehouse_guid` or empty `table_name`. **Expected:** `ValueError` raised immediately.

---

## 4. dopt_utility_set_properties_orchestrator

Validates that all tables in a Lakehouse receive the correct properties in a single run.

### 4.1 — Full Lakehouse configuration
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `layer` | `silver` |

**Expected:**
- One line per table: `{table}: properties set`
- Summary: `updated: N | errors: 0`
- N matches the table count from `dopt_utility_table_health`

**Verify:** Re-run `dopt_utility_table_health` — all tables should show `deletion_vectors = true`.

### 4.2 — Error resilience
If any table in the Lakehouse cannot accept properties (permissions, external table, etc.):
- That table logs `{table}: ERROR — {message}`
- The run continues to completion
- The summary error count reflects the failure

---

## 5. dopt_utility_table_maintenance

Validates OPTIMIZE gating, before/after metrics, and VACUUM scheduling.

### 5.1 — Fragmented table (OPTIMIZE expected)
Select a table showing `Needs OPTIMIZE` in the `dopt_utility_table_health` output.

| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | A fragmented table |
| `layer` | `silver` |

**Expected:**
- OPTIMIZE runs
- `files: X → Y (Z compacted)` — Y is meaningfully lower than X
- `avg size: A MB → B MB` — B is closer to the target

### 5.2 — Healthy table (OPTIMIZE expected to skip)
Select a table showing `Healthy` in the health report.

| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | A healthy table |
| `layer` | `silver` |

**Expected:** `{table}: skipped — avg XMB is within tolerance of 256MB target`

### 5.3 — Forced VACUUM
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | Any table |
| `layer` | `silver` |
| `force_vacuum` | `True` |

**Expected:** VACUUM runs regardless of day. Output: `{table}: VACUUM ran — retained 168h`

### 5.4 — Schema-enabled table *(if applicable)*
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your schema-enabled Lakehouse GUID |
| `table_name` | Table name without schema prefix |
| `schema_name` | The schema the table lives in |
| `layer` | `silver` |

**Expected:** Same behaviour as 5.1–5.3. The ABFSS path in the notebook output will include the schema segment.

### 5.5 — Custom layer
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `table_name` | Any table |
| `layer` | `custom` |
| `custom_target_mb` | `300` |

**Expected:** Same OPTIMIZE gating behaviour as 5.1–5.2 using 300 MB as the threshold.

**Error case:** Set `custom_target_mb = 0` with `layer = "custom"`. **Expected:** `ValueError` raised immediately — `custom_target_mb` is required for custom mode.

---

## 6. dopt_utility_maintenance_orchestrator

Validates Lakehouse-wide maintenance, summary accuracy, and error resilience.

### 6.1 — Full Lakehouse run
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `layer` | `silver` |
| `force_vacuum` | `False` |

**Expected:**
- `Tables found: N` matches the count from `dopt_utility_table_health`
- Each table logs `skipped` or `OPTIMIZE ran` with file counts
- Summary: `optimized: X | skipped: Y | vacuumed: 0 | errors: 0 | files compacted: Z` (if not run on a Sunday — on Sunday VACUUM fires automatically and `vacuumed` will equal N)
- X + Y = N

**Cross-check:** Re-run `dopt_utility_table_health` — previously fragmented tables should now show `Healthy` or `Review`.

### 6.2 — Forced VACUUM pass
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your Lakehouse GUID |
| `layer` | `silver` |
| `force_vacuum` | `True` |

**Expected:** Summary shows `vacuumed: N` where N equals total tables.

---

## 7. Schema-Enabled Lakehouse Validation *(Optional)*

Validates the `list_delta_tables()` schema detection logic used by `dopt_utility_table_health`, `dopt_utility_maintenance_orchestrator`, and `dopt_utility_set_properties_orchestrator`. Only required if your environment uses schema-enabled Lakehouses.

### 7.1 — Health scan across schemas
| Parameter | Value |
|---|---|
| `lakehouse_guid` | Your schema-enabled Lakehouse GUID |
| `layer` | `silver` |

**Expected:**
- All tables across all schemas are listed
- `schema` column is populated with the correct schema name for each row
- No tables are missed or duplicated across schema boundaries

### 7.2 — Orchestrator across schemas
Run `dopt_utility_maintenance_orchestrator` with the schema-enabled Lakehouse GUID.

**Expected:**
- All tables across all schemas are processed
- Log lines use the schema-prefixed display name: `{schema}.{table}: ...`
- Summary counts match the total found in Test 7.1

---

## Sign-Off Checklist

| # | Area | Tests | Pass |
|---|---|---|---|
| 1 | Session config | Four layers + invalid input | ☐ |
| 2 | Table health | Scan, layer targets, custom mode, missing param | ☐ |
| 3 | Set table properties | All layers, clustering, custom mode, missing param | ☐ |
| 4 | Set properties orchestrator | Full run, error resilience | ☐ |
| 5 | Table maintenance | OPTIMIZE triggers, skip, forced VACUUM, custom layer | ☐ |
| 6 | Maintenance orchestrator | Full run, forced VACUUM | ☐ |
| 7 | Schema-enabled Lakehouses *(optional)* | Health scan, orchestrator | ☐ |
