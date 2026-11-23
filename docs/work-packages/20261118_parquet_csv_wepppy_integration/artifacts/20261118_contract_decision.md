# M0 contract checkpoint draft

Date: 2026-11-18 UTC. Status: **M0 ratified for implementation**.
Starting source: `392ee2299d8573e038b2e932fe3bdb7e044d1d35`.

## Operator decision

Execute implementation on `codex/parquet-csv-cli-package`. Intended delivery:
immediate cutover, no environment-variable-facing configuration, no Python
fallback. Zero-trust input handling and strict JSON response IPC carry forward.
Broad tests follow integration wiring. This approves the direction, not undeclared
compatibility reductions, arbitrary resource defaults or deployment execution.

## Contracts and discrepancy classification

- New [integration contract](../../../schemas/parquet-csv-integration-contract.md):
  records approved policy and draft implementation obligations; conformance pending.
- Existing [CLI contract](../../../schemas/parquet-csv-cli-contract.md): accepted
  standalone wire/resource/input subset; amend before needed native extensions.
- Existing [filesystem contract](../../../schemas/browse-filesystem-contract.md):
  preserve raw access, security/PII precedence, honest failures and retirement policy.
- Existing [filter contract](../../../schemas/weppcloud-browse-parquet-filter-contract.md):
  preserve selection/validation/empty-result semantics, explicitly reconcile CSV
  environment-backed settings without changing other consumers implicitly.

Classification: intended execution-boundary change with compatibility obligations,
not a claim that existing Python code violates an already-implemented native contract.
Security impact high. No project data mutation is planned; CSV artifact semantics
require a compatibility/regression plan before implementation.

## Required checkpoint completion

Record a route/state/type/codec/filter matrix from actual fixtures and projects,
including absent, empty, populated, supported legacy, hostile and retired states.
Specify fixed executable/provenance/scratch paths, code-owned settings, exact
HTTP mappings/headers, serving ownership and crash recovery. Resolve valid cases
excluded by CLI v1 and any versioned filter/input protocol extension. Freeze the
resource ADR and whole-service concurrency/disk/memory accounting under real worker
and mount topology. Inventory and reconcile CSV environment reads explicitly.

Record binary packaging/source-provenance policy and exact-image preflight, an
artifact visibility/retention policy, and regression commands with actual paths.
Amend all affected canonical contracts, then obtain two independent read-only
contract reviews and disposition findings. Commit those documents and dispositions
as a standalone ancestor before implementation. Record that SHA in the tracker.
Do not treat the scaffold commit as the completed M0 checkpoint.

## Regression and review evidence to retain

Real-child CSV/HTTP parity for every covered branch, filter validation/empty/cap
outcomes, auth/containment/PII denials before native invocation, malformed metadata,
external references and allocation limits, missing/tampered binary, bad JSON IPC,
shared-worker busy admission, slow-client disconnect, cancellation, worker death
and restart recovery. Prove no old Python exporter is callable from covered routes.
Run broad pytest after wiring. Exact-image production-equivalent readback is a
release gate; historical standalone results alone cannot close it.

Independent contract reviews: approved; see dedicated correctness/security artifacts.
Checkpoint ancestor: this standalone documentation commit.

## Prepared normative delta and evidence

The integration contract's implementation-checkpoint section fixes paths, modules,
protocol v2, filter transport, exact HTTP mappings, 30/120/100/600-second budgets,
inherited flock ownership, child wall/parent-death supervision and response
cleanup. ADR-0149 records the resource decision. Canonical CLI, filter and browse
contracts now reference the integration amendment. Conformance remains pending.

compatibility-inventory.json retains path, input SHA-256, size, row/row-group
counts, schemas and codecs for 156 real files. Required native additions are
null, timezone-free timestamp, WKB binary/geoarrow.wkb and ZSTD. Synthetic fixtures
must add zero-row, invalid metadata, adversarial structures and filter boundaries;
nonempty inventory alone is not exhaustive coverage. Dependency expansion is
conditionally evaluated in dependency-evaluation.md and its machine-readable
inventory/audit. All production implementation files remain unchanged.

The live directory NoDir CSV branch ignores pqf; classify this as a discrepancy
against the filter contract. Unify filtered exports without reviving archives.
Preserve physical-index filtering, DOUBLE comparison and DuckDB VARCHAR/lowercase
semantics with direct differential fixtures. The filtered cap does not constrain
unfiltered H.wat. Preserve authorized contained symlinks and raw-byte precedence.

Operator explicitly approved transient storage deletion. Original files and
correlated logs remain; retained CSVs could look current when stale and suggest
automatic generation, leading users to mistake absence for failed model outputs.
Exact exception is promoted to the canonical integration and browse contracts.

First independent correctness and security reviews identified these gaps; they
are incorporated into the amended contract. Final checkpoint review pending.


Final review dispositions: preserve duplicate projected-label last-value semantics
and all-index header-only output; scope NaN exclusion to numeric comparisons;
raise private normalized IPC ceiling to 128 KiB while retaining external64 KiB
and compact UTF-8 encoding; classify child SIGALRM as timeout504. User explicitly
approved rejecting invalid UTF-8 metadata; all156 inventoried files have valid
UTF-8 metadata and no duplicate physical names or unit labels. Native parity for
the duplicate-label edge case remains required. Test normalized-payload expansion
with32 conditions containing492 emoji values (65130-byte external JSON).

Final correctness reviewer approved hash c9c94c0b4430710c3a922b8d287587adac27abbfef6a4f0b3552ec39a8b20907.
All medium/high checkpoint findings are closed; runtime acceptance remains open.
