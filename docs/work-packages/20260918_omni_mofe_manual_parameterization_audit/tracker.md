# Tracker: Omni MOFE versus manual landuse audit

Status: Active

| Milestone | State | Evidence |
| --- | --- | --- |
| Production identity and read-only inventory | Complete | `artifacts/raw/parent.omni.nodb`, scenario files, host hashes |
| Source-path comparison | Complete | `audit.md`, `wepppy/nodb/core/landuse.py`, `wepppy/nodb/mods/omni/README.md` |
| Metric and MOFE assignment comparison | Complete | `scripts/audit_compare.py`, `artifacts/omni_manual_comparison.csv` |
| Findings/dispositions and validation | Complete | `audit.md`; four `wctl doc-lint` passes |

No production mutation, rerun, or deployment is part of this package.
