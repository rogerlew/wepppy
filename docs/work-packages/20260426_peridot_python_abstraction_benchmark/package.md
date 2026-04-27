# Peridot vs WEPPpy Python Abstraction Benchmark

**Status**: Backlog
**Timezone**: UTC

## Overview

This package scopes an evidence-backed benchmark between Peridot watershed abstraction and the legacy WEPPpy Python-based abstraction path. The benchmark target is the WEPPpy Python abstraction because it has not been used recently and must be rediscovered, smoke-tested, and treated as a comparator with uncertain health before any performance claim is made.

The goal is not to prove a predetermined speedup. The goal is to produce a reproducible benchmark harness and a disciplined validation record that says what was measured, what outputs matched, what failed, and which claims are confirmed versus inferred or still hypothetical.

## Objectives

- Identify the callable WEPPpy Python abstraction path and the exact backend settings needed to exercise it.
- Smoke-test the legacy Python abstraction before using it as a benchmark target.
- Build an isolated benchmark workflow that does not mutate canonical run directories under `/wc1/runs`, `/geodata/weppcloud_runs`, or other operator-managed roots.
- Compare Peridot and Python abstraction outputs for schema, row counts, identifiers, slope-file presence, and core watershed/network products before comparing timings.
- Measure wall-clock runtime and, where practical, peak memory or process resource usage for both abstraction paths.
- Record all claims with explicit evidence labels: `confirmed`, `inference`, or `hypothesis`.
- Produce artifacts that can support future Peridot communication without overstating unmeasured performance or parity.

## Scope

### Included

- WEPPpy benchmark package documentation, tracker, active ExecPlan, and artifacts.
- Discovery of the legacy Python abstraction entrypoints, currently expected around:
  - `/workdir/wepppy/wepppy/topo/watershed_abstraction/watershed_abstraction.py`
  - `/workdir/wepppy/wepppy/nodb/core/watershed.py::_topaz_abstract_watershed`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py::abstract_watershed`
- Discovery of Peridot abstraction entrypoints, currently expected around:
  - `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py`
  - `/home/workdir/peridot/src/bin/abstract_watershed.rs`
  - `/home/workdir/peridot/src/bin/wbt_abstract_watershed.rs`
- Benchmark fixture selection from in-repo fixtures where possible, with copied or staged run data only when needed.
- A reproducible command or script for running both abstraction paths on the same input workload.
- Output parity checks before performance comparisons.
- Validation artifacts summarizing benchmark commands, hardware/context, result tables, and claim classifications.

### Explicitly Out of Scope

- Changing Peridot algorithms to improve benchmark results.
- Changing WEPPpy production backend defaults.
- Mutating live or historical run directories in place.
- Rebuilding or deploying Peridot release binaries unless a separate deployment package requests it.
- Publishing universal speedup claims without representative workload evidence.
- Removing the Python abstraction path, even if it is stale or broken.

## Stakeholders

- **Primary**: WEPPpy and Peridot maintainers responsible for watershed abstraction behavior and evidence-backed performance claims.
- **Reviewers**: Topology/Watershed maintainers, Peridot maintainers, documentation maintainers.
- **Security Reviewer**: Not required unless the benchmark harness adds new external ingress, route surfaces, secrets handling, or production-host mutation.
- **Informed**: Operators who may provide representative run directories, downstream data-table/query consumers, and future Peridot documentation authors.

## Success Criteria

- [ ] The package identifies the exact legacy Python abstraction invocation path and records whether it currently runs.
- [ ] If the Python path fails, the failure is captured with command, fixture, traceback, and a scoped remediation recommendation.
- [ ] At least one small smoke fixture runs through both Peridot and Python abstraction paths, or the package records why no safe fixture was available.
- [ ] Benchmark inputs are copied into isolated temporary or artifact directories; source run directories are not mutated.
- [ ] Output parity checks compare required file presence, table schemas, key row counts, topaz/wepp IDs, and slope-file presence.
- [ ] Runtime measurements include enough environment context to be reproducible: command, repo commit, CPU count, thread settings, and input size summary.
- [ ] Benchmark artifacts classify each claim as `confirmed`, `inference`, or `hypothesis`.
- [ ] WEPPpy package docs pass `wctl doc-lint`.

## Benchmark Framing

The comparison is Peridot versus the WEPPpy Python watershed abstraction path. The Python path is the benchmark target/comparator, not an assumed source of truth. It is expected to be stale, so the first benchmark milestone is health discovery. Performance measurements are invalid until the package has either shown comparable outputs or explicitly documented the parity gap.

The initial target is TOPAZ-derived abstraction because the legacy Python path `_topaz_abstract_watershed()` constructs `WatershedAbstraction` instances over TOPAZ outputs. WBT-derived Peridot benchmarking can be added after the Python comparator is proven usable or after a separate comparator is defined.

## Metrics Definitions

- **Scalability**: Wall-clock runtime and resource growth as input workload size increases, where workload size is recorded using available proxies such as raster cell count, hillslope count, channel count, and flowpath count. A scalability claim is only `confirmed` for the measured workload sizes.
- **Topology flexibility/correctness**: Ability to produce structurally valid watershed outputs for the same input topology, checked by required file presence, network/structure consistency, unique IDs, parent-child relationships, and schema-compatible hillslope/channel/flowpath tables. Correctness claims require parity evidence, not just successful process exit.
- **Parallelization potential**: Observable use of concurrency knobs and workload partitioning, measured by thread/process settings, CPU utilization if collected, and runtime change across controlled worker counts. Potential speedups remain `hypothesis` unless measured with controlled worker-count runs.

## Claim Discipline

Every benchmark note and final summary must use the following labels:

- `confirmed`: directly measured or verified in this package with command output, generated artifacts, or table comparisons.
- `inference`: reasonable conclusion from confirmed observations, with the assumptions stated.
- `hypothesis`: plausible but unmeasured claim that must not be used as a public performance statement.

No package output should claim universal Peridot speedups. Acceptable wording is workload-bound, for example: `confirmed: Peridot completed fixture X in N seconds versus Python in M seconds on host H with settings S`.

## Dependencies

### Prerequisites

- Peridot runtime contract hardening is closed and Peridot full `cargo test` passes after commit `e09f54c`.
- WEPPpy checkout has `wctl` and the local virtualenv available.
- Peridot binaries used by WEPPpy are identifiable and their versions or commit provenance can be recorded before measurement.

### Blocks

- Evidence-backed Peridot benchmark claims.
- Any decision to retire, preserve, or remediate the stale WEPPpy Python abstraction comparator.
- Future documentation that wants to quantify Peridot performance against the historical Python implementation.

## Related Packages

- **Depends on**: [20260426_peridot_runtime_contract_hardening](../20260426_peridot_runtime_contract_hardening/package.md).
- **Related**: [20260426_peridot_documentation_repositioning](../20260426_peridot_documentation_repositioning/package.md).
- **Related**: [20260321_peridot_watershed_parquet_manifest](../20260321_peridot_watershed_parquet_manifest/package.md).
- **Related**: [20260422_peridot_side_hillslope_length_capping](../20260422_peridot_side_hillslope_length_capping/package.md).

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions if the Python path still runs; longer if comparator remediation is required.
- **Complexity**: Medium-high, because the comparator is stale and benchmark results depend on safe fixture selection.
- **Risk level**: Medium, with the main risk being stale Python abstraction failures rather than Peridot test health.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Planned work is local benchmark discovery, isolated fixture copying, and documentation/artifact generation. It does not add public routes, auth/session changes, secrets handling, queue wiring, deployment automation, or external egress.
- **Security review artifact**: `N/A`

## Deliverables

- Benchmark discovery artifact identifying the Python comparator path and health status.
- Reproducible benchmark harness or command transcript.
- Output parity artifact for each workload.
- Runtime/resource summary artifact with claim labels.
- Updated package tracker and ExecPlan progress notes.
- Follow-up package recommendations if the Python comparator fails or needs remediation before meaningful benchmarking.

## Follow-up Work

- If the Python abstraction fails due to code drift, prepare a remediation package scoped to comparator revival before publishing benchmark claims.
- If representative in-repo fixtures are insufficient, prepare a fixture-curation package to add small, license-safe TOPAZ/WBT abstraction fixtures to the repository.
- If Peridot benchmark results depend on release binary provenance, prepare a deployment/provenance package for binary rebuild and version stamping.
