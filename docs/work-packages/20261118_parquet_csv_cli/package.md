# Bounded Parquet CSV CLI and Python harness

**Status**: Scaffolded; contract checkpoint pending (2026-11-18)
**Timezone**: UTC
**Owner**: Roger Lew; implementation agent to be assigned

## Purpose

Evaluate an owned Rust Parquet-to-CSV CLI and standalone asynchronous Python
harness before considering changes to WEPPpy's browse/download workflow. The
current exporter converts Arrow batches into Python dictionaries, formats each
cell in Python, and buffers the complete CSV in memory. A bounded subprocess
could reduce conversion cost and isolate failures, but these benefits must be
measured against both the current exporter and incremental native PyArrow CSV.

## Scope and integration boundary

Included: contract discovery and ratification, dependency evaluation, a standalone
Rust CLI, a standalone Python harness, real generated CSV readback, lifecycle and
resource tests, representative benchmarks, and a documented go/no-go decision.
The intended fidelity target is **faithful extraction** of contracted CSV semantics
within an explicitly enumerated supported input set. This initial delivery is
**scaffold only**, not implementation completion.

WEPPpy integration is **deferred and outside this package**. Do not modify or wire
browse/download routes, production Python exporters, image builds, Compose,
Caddy, RQ, authentication, deployment, or production run artifacts. Housing an
isolated evaluation under this repository does not authorize runtime integration.
A successful CLI and harness are necessary but insufficient for integration:
a separately authorized successor package, provisionally
`parquet_csv_wepppy_integration`, must own route contracts, aggregate admission,
production-equivalent workflow tests, rollout and recovery. A no-go result must
retain evidence without silently switching languages or redesigning services.

## Contract-first sequence

The draft [standalone contract](../../schemas/parquet-csv-cli-contract.md) is the
intended durable authority after ratification; it is not approved or implemented.
The [checkpoint](artifacts/20261118_contract_decision.md) records scope and open
choices. Complete input/valid-state inventories, exact interface/error semantics,
compatibility rules, resource ADR, and dependency evaluation before implementation.
Obtain explicit operator approval of that concrete contract, two independent
read-only reviews and finding dispositions, then retain a standalone checkpoint
ancestor commit. This package adopts that sequence for the standalone work too;
it does not imply that production integration has been approved.

## Complexity budget

Reuse the shape-converter process-group, timeout, cancellation/drainage, bounded
IPC, private scratch and binary-provenance patterns. Permit one Rust executable,
one standalone Python harness, fixture/benchmark tooling, and an evaluated,
locked minimum Parquet/Arrow dependency graph. The CLI uses synchronous local
file processing; the Python harness owns asynchronous execution. No new service,
queue, daemon, datastore, network protocol, privileged helper, or fallback to the
old exporter is authorized. No new C++ implementation is included.

The simplest performance comparator is existing PyArrow's incremental native CSV
writer. It is an evaluation baseline, not an authorized production replacement.
Escalation requires retained evidence that the bounded design misses acceptance,
the smallest proposed addition, and its operational/recovery costs.

## Evidence and success criteria

- [ ] Ratified contract, exact checkpoint revision, two independent reviews and dispositions.
- [ ] Exact dependency graph evaluated for capability overlap, transitive cost,
  advisories, allocation behavior, codecs, maintenance and build reproducibility.
- [ ] CLI and harness work independently of Flask, Redis, Postgres and live run services.
- [ ] Fresh CSVs from the rebuilt binary pass independent semantic and required
  byte-format readback against the contracted oracle for all supported states.
- [ ] Real subprocess tests demonstrate resource enforcement, admission,
  timeout/cancellation drainage, output cleanup and preserved valid large exports.
- [ ] Reproducible comparison with current exporter and incremental native PyArrow
  meets the numeric acceptance thresholds fixed before candidate benchmarking.
- [ ] Dedicated correctness and security reviews have no unresolved medium/high findings.
- [ ] Final decision states go/no-go and unresolved integration work explicitly.

For generated-artifact validation, retain request/config intent, immutable source
manifest and digest, exact input descriptor/path consumed, binary/provenance and
harness revisions, fresh output digest, parsed headers/rows/cells and failure
artifacts. No NoDb state is introduced. Use read-only copies of representative
real project files under a production-equivalent test identity and resource
envelope; run no stress benchmark on wepp1. Process success or file existence
alone is not output correctness. Current claim: scaffolded, not implemented,
validated, wired or deployed.

## Security and parameterization gates

Security impact: **high** for the planned native decoder, file handling and
subprocess resource boundary; the scaffold itself changes no runtime behavior.
Create `artifacts/<date>_security_review.md` and
`artifacts/<date>_correctness_review.md` from the repository templates during
execution. Review valid inputs alongside malformed files, allocation pressure,
path/symlink races, inherited authority, output overwrite, IPC and cancellation.
A subprocess shares its container authority; do not claim arbitrary-code sandboxing.

Resource defaults and rejection thresholds require a new resource-envelope ADR
before implementation acceptance. Numeric limits remain unset here. They must be
justified with representative valid workloads and a declared host-wide budget;
small batches alone do not bound decoder allocations. No model formulas, units
or project data schemas are changed.

## Observations and limitations

The read-only wepp1 review on 2026-11-18 around 18:04 UTC observed 99 successful
CSV exports with median 5.5 seconds, p95 about 246 seconds, and six browse worker
timeouts over roughly 12 hours. Some exports increased worker RSS by 500-670 MiB.
These are session observations, not retained benchmark artifacts or proof of
causation. Reproduce the baseline locally. The longstanding distributed crawler
is context, not evidence of a new compromise or authorization to block traffic.

## References and ownership

- [ExecPlan](prompts/active/implementation_execplan.md) and [tracker](tracker.md).
- Existing behavior: `wepppy/microservices/browse/_download.py` and
  `wepppy/microservices/browse/parquet_tables.py`.
- Lifecycle precedent: `wepppy/microservices/shape_converter/convert.py` and
  `wepppy/microservices/shape_converter/docs/specification.md`.
- [Dependency standard](../../standards/dependency-evaluation-standard.md): the
  GeoParquet precedent is conditional and does not approve added Arrow features.
- [Contract-first standard](../../standards/contract-first-change-standard.md).
- [Artifact validation](../../standards/generated-artifact-validation-standard.md).
- [History governance](../../standards/integration-history-governance.md).

Maintain the standalone contract outside the package after closure. Report local
acceptance, repository integration, publication and deployment separately. This
package can close as an evaluated standalone tool or documented no-go; it cannot
claim the production export problem has been repaired.
