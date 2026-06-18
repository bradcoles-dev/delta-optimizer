## What does this PR do?
A clear description of the change and why it's being made.

## Which notebook(s) does it affect?
e.g. `dopt_utility_table_maintenance`, `dopt_utility_table_health`, docs only

## How was it tested?
Describe what you tested and against what — Fabric Runtime version, table configuration, workload type. Remember: testing must be done against a real Fabric Lakehouse, not a local environment.

## Checklist
- [ ] Tested against a real Fabric Lakehouse
- [ ] Print output covers every table-level decision (skipped / ran / error)
- [ ] No hardcoded Lakehouse GUIDs, table names, or paths
- [ ] Relevant documentation in `docs/` updated if behaviour changed
- [ ] `docs/medallion-recommendations.md` updated if any settings changed
