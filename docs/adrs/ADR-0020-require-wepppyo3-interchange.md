# ADR-0020: Require WEPPpyo3 for WEPP Interchange

Status: Accepted
Date: 2026-07-15

## Context

WEPPpy historically retained complete Python parsers for WEPP text reports and
used them when the owned `wepppyo3.wepp_interchange` module was unavailable or
raised. The fallback was logged, but it still converted a deployment defect into
a long-running worker job with a different memory/performance profile.

AgFields routing-suite acceptance demonstrated the cost. A multi-OFE Hybrid WAT
corpus reached 46,695,247,872 bytes sampled anonymous memory through Python table
handoff; direct native writing completed the same 108,308,610 rows at
489,709,568 bytes. An earlier native UTF-8 writer mismatch also continued through
a 22,002,030-row Python PASS fallback instead of making the stale/broken release
an explicit deployment failure.

## Decision

`wepppyo3.wepp_interchange` is a required runtime dependency for production WEPP
report conversion. Native import, required-symbol, parse, I/O, and write failures
are terminal. WEPPpy must not catch them and continue with a Python WEPP text
parser, Python record-batch assembly, or alternate primary Parquet writer.

WEPPpy retains stable public orchestration wrappers, version/calendar argument
resolution, cleanup, DuckDB aggregation, DSS export, and query helpers. These
responsibilities do not authorize a second report parser or primary writer. An
absent climate resource continues to
select established Gregorian behavior; an existing corrupt calendar resource is
an explicit failure.

Workers must install a paired native release exposing the complete required API
before startup. Rollback means restoring the prior paired WEPPpy and wepppyo3
release, not enabling a runtime parser switch.

## Decision Provenance

- **Decision Venue**: Codex API conversation, 2026-07-15 10:05 PDT.
- **Participants Present**: Roger Lew, Codex.
- **Decision Owner**: Roger Lew, WEPPpy maintainer.
- **Implementers**: Codex and delegated WEPPpy/wepppyo3 agents.
- **Change Summary**: native-first with logged Python recovery becomes
  native-required with explicit terminal failure.

## Rationale

WEPPpy and wepppyo3 are an owned paired stack. Maintaining a second production
parser does not provide a trustworthy availability boundary when it hides release
drift, changes resource behavior, and receives less exercised coverage. A fast,
actionable deployment failure is safer than completing through an implementation
whose cost and behavior differ materially.

## Alternatives Considered

1. Keep the logged fallback. Rejected because logging did not prevent the
   half-day diagnostic and high-memory execution.
2. Add an environment flag to disable fallback. Rejected because it creates two
   production contracts and allows deployments to drift silently.
3. Retry or auto-downgrade the native release. Rejected because shared-object and
   schema/API mismatch are deployment integrity failures, not transient inputs.
4. Move every aggregation/export/query function to Rust. Rejected as unrelated;
   the duplicated risk is WEPP report parsing and conversion.

## Consequences

- Old or incomplete native releases fail before conversion and must be upgraded.
- Native errors remain visible with operation/cause context.
- Production Python parser code and fallback tests can be deleted.
- Five hillslope bulk writers and the TC_OUT writer become native release APIs;
  the shared Python primary-Parquet fan-in can be deleted.
- Release symbol/provenance tests become mandatory before stack restart.
- WEPPpy public wrapper imports remain stable for callers.

## Evidence and Rollback

Evidence is maintained in
`docs/work-packages/20260715_wepppyo3_only_interchange/` and the completed
[AgFields routing package](../work-packages/20260714_ag_fields_routing_scheme_suite/package.md).
Rollback restores the preceding paired repository commits and native artifact,
then restarts every importing service. Reintroducing the Python fallback requires
a new ADR with measured need, parity, and resource evidence.

## Review Date

Review native symbol/provenance and fallback telemetry after 2026-08-14. Any
Python production parser reintroduction is a danger signal, not routine recovery.
