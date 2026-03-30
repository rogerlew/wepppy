# Code Review - Roads Peridot Trace Core (2026-03-27)

## Scope Reviewed

- `/workdir/peridot/Cargo.toml`
- `/workdir/peridot/src/lib.rs`
- `/workdir/peridot/src/roads_trace/mod.rs`
- `/workdir/peridot/src/roads_trace/trace_downslope.rs`
- `/workdir/peridot/src/bin/trace_downslope_flowpath.rs`
- `/workdir/peridot/tests/roads_trace_downslope.rs`
- `/workdir/wepppyo3/Cargo.toml`
- `/workdir/wepppyo3/roads_flowpath/Cargo.toml`
- `/workdir/wepppyo3/roads_flowpath/src/lib.rs`
- `/workdir/wepppyo3/tests/roads_flowpath/test_trace_downslope_flowpath.py`
- `/workdir/wepppyo3/release/linux/py312/wepppyo3/roads_flowpath/__init__.py`
- `/workdir/wepppyo3/README.md`

## Findings

| ID | Severity | Finding | Status | Resolution |
|---|---|---|---|---|
| CR-01 | Medium | CLI and `pyo3` wrappers could drift from core termination labels/keys if wrappers implement independent logic. | Resolved | Both wrappers call `peridot::roads_trace::trace_downslope_flowpath` directly; `wepppyo3` parity test compares selected fields to CLI JSON output from the same seed/raster fixture. |
| CR-02 | Low | Channel-mask truth semantics were ambiguous (`mask > 0` vs non-zero). | Resolved | Contract text updated in Roads spec to document v1 rule explicitly: channel when mask value is `> 0`. |

## Medium/High Closure

- Unresolved medium findings: **0**
- Unresolved high findings: **0**

## Reviewer Verdict

- Shared-core architecture is correctly enforced (no duplicate downslope algorithm in CLI or `pyo3`).
- Termination behavior, vector shape invariants, and channel-hit paths are covered by deterministic tests.
