# WEPPpyo3-Only Interchange Cutover

**Status**: Open 2026-07-15
**Timezone**: UTC

## Overview

WEPPpy currently attempts native WEPP-output conversion first and then silently
continues the job through large legacy Python parsers after a logged warning.
During AgFields generated acceptance, that compatibility behavior hid a broken
native deployment and consumed hours plus tens of gigabytes of worker memory.
This package retires production Python format parsing and makes the owned
`wepppyo3.wepp_interchange` release a required runtime dependency.

The public WEPPpy orchestration entrypoints remain stable. Python may still own
run-path discovery, version metadata, DuckDB aggregation, DSS export, and job
orchestration; it may not parse a WEPP text report, assemble its record batches,
or write its primary interchange Parquet as a production compatibility path.

## Objectives

- Make native module and per-operation API availability an explicit precondition.
- Remove production Python parser/writer fallbacks for every covered hillslope
  and watershed interchange format.
- Preserve public return values, Parquet schemas/metadata, ordering, atomic
  publication, and cleanup behavior.
- Fail missing, stale, or faulting native releases with one stable, actionable
  error contract.
- Rebuild and install the Python 3.12 native release, restart the local WEPPpy
  stack, and prove native-only generated output.
- Complete independent code and QA reviews before closure.

## Scope

### Included

- `wepppy/wepp/interchange/_rust_interchange.py` required-native contract.
- Hillslope PASS/HBP, EBE, ELEMENT, LOSS, SOIL, and WAT conversion wrappers and
  new direct multi-file native writers for the five formats that currently
  return Python column dictionaries.
- Watershed PASS, SOIL, LOSS, channel peak, EBE, CHANWB, and CHNWB wrappers.
- Watershed `tc_out.txt` conversion through a new native direct writer.
- Removal of the watershed EBE raw-`chan.out` Python parser; its audit/inference
  must use native output or a native helper.
- Native catalog scan dispatch when used by interchange publication.
- Removal of dead production Python report parsers and fallback-oriented tests.
- Native release API/provenance checks in `/home/workdir/wepppyo3`.
- WEPPpy/interchange documentation, operator diagnostics, ADR-0020, and exact
  regression coverage.
- Local stack restart and a generated smoke using the installed release artifact.

### Explicitly Out of Scope

- Moving `totalwatsed3`, DSS export, report querying, or generic Parquet reads to
  Rust solely because they are implemented in Python.
- Changing WEPP model formulas, routing schemes, schemas, units, row order, or
  user-facing result paths.
- Adding a feature flag, retry, alternate parser, or automatic release downgrade.
- Removing the stable `wepppy.wepp.interchange` public import surface; it becomes
  a thin required-native orchestration facade.
- Production deployment beyond the authorized local development/forest stack.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`.
- **Authoritative source paths**:
  `wepppy/wepp/interchange/*_interchange.py`,
  `/home/workdir/wepppyo3/wepp_interchange/src/`, and the installed
  `/home/workdir/wepppyo3/release/linux/py312/` package.
- **Cutover proof required**: the restarted stack imports the exact rebuilt
  release; all production wrappers call required native writer APIs; a forced
  missing/stale API fails before output publication; generated conversion emits
  no Python-parser fallback warning.
- **Acceptance evidence type**: `both` fixture and generated output.

## Stakeholders

- **Decision owner**: Roger Lew, WEPPpy maintainer.
- **Implementer**: Codex with delegated discovery and review agents.
- **Reviewers**: two independent review passes, one code-focused and one
  QA/runtime-focused.
- **Informed**: WEPPpy/wepppyo3 maintainers and WEPPcloud operators.

## Success Criteria

- [x] No production interchange path catches native import/API/parse/write errors
  and continues with a WEPPpy text parser.
- [x] Missing module, missing required symbol, and native execution failure each
  produce a stable explicit exception with operation context and chained cause.
- [x] Dead Python report parser/writer implementations and the shared Python
  Parquet fan-in are removed from production modules; test-only parity fixtures
  do not become runtime dependencies.
- [x] All public wrapper return/path/schema/order/metadata contracts pass focused
  regression and native release tests.
- [x] The installed Python 3.12 release exposes every required symbol and records
  reproducible provenance.
- [x] The authorized stack is restarted and generated interchange completes
  through the installed native release with no fallback telemetry.
- [ ] Focused and broad WEPPpy gates pass, plus wepppyo3 Rust/release gates.
- [ ] Independent code and QA reviews have no unresolved medium/high findings.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`; the missing/failing-native fallback
  rule changes from Python recovery to explicit failure.
- **ADR required**: `yes`.
- **ADR link**:
  [ADR-0020: Require WEPPpyo3 for WEPP Interchange](../../adrs/ADR-0020-require-wepppyo3-interchange.md).
- **Decision provenance captured**: `yes`; Codex API conversation, Roger Lew and
  Codex, 2026-07-15 10:05 PDT.

## Security Impact and Review Gate

- **Security impact triage**: `low`.
- **Dedicated security review required**: `no`.
- **Triage rationale**: the cutover narrows an internal worker implementation and
  adds no route, auth, path, network, secret, or queue capability. Normal code and
  QA reviews must still verify exception redaction and atomic output behavior.

## Hardening and Callus Softening

- **Failure signatures**: `Rust module unavailable ... falling back to Python`,
  `Rust ... failed; falling back to Python`, and WAT's fallback to
  source-ordered Python table conversion.
- **Observed impact**: Hybrid WAT conversion reached 46,695,247,872 bytes sampled
  anonymous memory on the Python table-handoff path; the native direct writer
  completed the same 108,308,610 rows at 489,709,568 bytes. A broken UTF-8 native
  writer also ran a 22,002,030-row Python PASS fallback instead of failing.
- **Scope boundary**: remove confirmed compatibility-parser calluses without
  moving unrelated query/export/aggregation logic to Rust.
- **Softening hypothesis**: if the compatibility calluses are removed and native
  API presence is checked before writes, deployment drift fails quickly and no
  job can enter the unbounded Python parser path.
- **Health signals**: native provenance logged, zero fallback messages, explicit
  pre-publication failure for missing symbols, and stable schema/value tests.
- **Danger signals**: a new alternate parser, swallowed native exception,
  partially published target, or stack importing an unrecorded shared object.
- **Observation window**: through 2026-08-14.
- **Temporary calluses introduced**: none.

## Related Packages

- [WEPPpyo3 interchange plan](../../../wepppy/wepp/interchange/wepppyo3-interchange-plan.md)
  established the original native-first compatibility policy.
- [AgFields Routing Scheme Suite](../20260714_ag_fields_routing_scheme_suite/package.md)
  provides the generated failure and memory evidence that triggered retirement.
- [WEPP Interchange Dependency Race Guard](../20260428_wepp_interchange_dependency_race_guard/package.md)
  provides atomic/dependency publication precedent.
- [Hardening lifecycle standard](../../standards/hardening-lifecycle-standard.md)
  governs this callus-softening cutover.

## Deliverables

To be completed at closure.

## Follow-up Work

Only evidence-backed opportunities discovered during execution will be recorded.
