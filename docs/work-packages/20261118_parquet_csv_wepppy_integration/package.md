# Integrate the native Parquet CSV exporter

**Status**: Closed locally, 2026-11-18; production deployment pending
**Timezone**: UTC
**Owner**: Roger Lew; implementation integrator: Codex

## Purpose and authority

Replace browse/download's whole-output Python CSV conversion with the evaluated
Rust CLI and asynchronous harness. The implementation target is faithful user-facing
behavior through a single native path, with bounded resource use under crawling
and concurrent downloads. The operator has authorized package execution.

The operator requires immediate cutover, no environment-variable-facing CSV
configuration and no fallback to the Python implementation. These decisions and
their rationale are captured in the ratified durable
[integration contract](../../schemas/parquet-csv-integration-contract.md#authority-and-cutover-policy).
Execution does not authorize production deployment. The reviewed runtime and retained acceptance evidence implement that policy.

## Scope

Implement all currently supported/reachable Parquet-to-CSV download variants in
run, culvert and batch routes; native filter/schema/codec compatibility as needed;
shared admission; complete-file streaming and lifecycle ownership; required binary
packaging/provenance; readiness and failure contracts; production-equivalent local
validation; documentation and a concrete rollout/rollback handoff.

Do not migrate previews, D-Tale, raw/filtered Parquet downloads, unrelated report
CSV writers, the dedicated archive-download service, auth policy or model artifact
schemas. Preserve their behavior when shared helpers change. Do not revive retired
virtual archives. No publication or production deployment is authorized by this
implementation request. The closed standalone package remains immutable history.

## Complexity budget

Reuse the existing synchronous Rust CLI, stdlib async supervisor, filesystem lock
admission, current browse service, current image build and deployment workflow.
Permit a production adapter, reviewed native compatibility/filter extensions and
bounded input staging for representations proven reachable. No new service, queue,
datastore, daemon, language implementation, speculative converter framework or
runtime backend/configuration API. New dependencies require the dependency gates;
escalations require evidence the smaller design failed real acceptance.

## Compatibility and security gates

Security impact: **high**. Dedicated independent correctness and security reviews
are required at M0 and final acceptance; retain artifacts using the repository
review templates and close medium/high findings. A zero-trust child boundary must
also cover schema-dependent filtering; staging an already Python-decoded table
would not satisfy the contract. This is not an arbitrary-native-code sandbox claim.

Before editing implementation, inventory actual request/state combinations and
resolve v1 exclusions (types, codecs, metadata, duplicate labels, filters). Preserve
valid behavior or explicitly ratify exceptions; no native/Python split is allowed.
Inventory existing CSV environment reads and move CSV settings to code-owned
policy without changing separately governed preview/D-Tale/Parquet consumers.
Resource/default changes require an integration ADR before acceptance; ADR-0148
is evaluation evidence, not automatic production sizing approval.

## Acceptance

- [x] M0 contract matrix, exact settings/error mappings, independent reviews and committed checkpoint.
- [x] Required native compatibility and bounded filter/input handling implemented and tested.
- [x] Every supported CSV route immediately uses the native path; legacy serialization unreachable/removed.
- [x] No environment-facing CSV settings, fallback, feature flag or schema-based backend selector.
- [x] Shared-worker admission, real response/disconnect cleanup, worker-death recovery and bounded serving proven.
- [x] Exact built image/provenance and authorized real-project HTTP bytes validated under production-equivalent identity.
- [x] Focused checks pass; broad suite run after wiring, not at scaffold stage.
- [x] Independent final reviews, user/operator/developer docs and rollout/rollback handoff retained.

Generated-artifact evidence must connect request/filter intent, authorized source
identity, staged/consumed bytes, exact binary, finalized CSV and actual downloaded
bytes. Application persistence is N/A unless implementation introduces it (outside
the present complexity budget). Define scratch/failure observability explicitly.
No closeout based solely on mocks, child exit, metadata, file existence or a green
broad suite. Current completion claim: implemented, wired and locally validated against the
exact service image. Production deployment has not occurred. See
[validation](artifacts/validation.md) and [release handoff](artifacts/release-handoff.md).

## Execution map

[Tracker](tracker.md), [completed ExecPlan](prompts/completed/implementation_execplan.md),
and [M0 checkpoint](artifacts/20261118_contract_decision.md).
Starting revision: `392ee2299d8573e038b2e932fe3bdb7e044d1d35`.
Accepted standalone source: `fe82d99d5c5ec2bae60733e1c491f0cadebd9c58`.

Authorities: [integration contract](../../schemas/parquet-csv-integration-contract.md),
[CLI contract](../../schemas/parquet-csv-cli-contract.md),
[browse filesystem contract](../../schemas/browse-filesystem-contract.md), and
[filter contract](../../schemas/weppcloud-browse-parquet-filter-contract.md).
The [standalone decision](../20261118_parquet_csv_cli/artifacts/decision.md) is
historical evidence, not authority to change closed records or skip integration gates.
