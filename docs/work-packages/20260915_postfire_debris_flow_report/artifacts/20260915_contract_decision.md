# PFR-01 — Proposed report documentation checkpoint

Date: 2026-09-15. Author: root agent. Base:
`e6c821cdd844e1cde360bd76d3ce500f389b3f15`.

## Authority and classification

Classification: proposed new report behavior, not a conformance fix. The owner
authorized items 1–3 (contract, module links, implementation package) with agent
review and a dedicated simplicity-focused UX advocate. Exact new UX behavior
has not been ratified. No implementation or contract ancestor commit is claimed.

## Applicable contracts and proposed delta

The [report proposal](../../../ui-docs/contracts/postfire-debris-flow-report-contract.md)
names the module specification, rainfall/results, production M1/M3/runtime,
run control and report-shell authorities. Shared implementation boundaries also
include `docs/ui-docs/controller-contract.md`,
`docs/schemas/weppcloud-csrf-contract.md`,
`docs/schemas/nodb-persistence-concurrency-contract.md`,
`wepppy/weppcloud/feature_registry/specification.md`, and
`docs/standards/artifact-observability-standard.md`.

Delta: a separate read-only report of one accepted assessment, with a 15-minute
initial view, saved design points/table, three existing 50% threshold rows,
paginated events, coherent unitization, identity-aware stale/error handling and
clearly scoped downloads. No science, output schemas, model controls or source
delivery changes. Maps, continuous curves, custom targets and model comparisons
remain deferred to prevent a second configuration interface. Future implementation
also needs a ratified additive validated design/inverse-table projection; the
current ResultCatalog retains only manifest/events. Existing scalar and saved-mask
validation remains required; new upstream reads/computation remain excluded.

## Compatibility, security and regression evidence

Compatibility: additive report adapter only in future; preserve accepted v1/v2
semantics and all existing NoDb/parquet/artifact behavior. No project data
migration. Validate report values against accepted generated artifacts, including
after archive/restore; verify input/result hashes unchanged by reads.

Security: no current application runtime delta; requested read-only UX role is
registered without new tools, model, permissions, sandbox or concurrency settings.
Future run-scoped GET/query/download surface is high-impact by default and
must preserve authorization, typed bounded queries, output encoding, fixed local
paths, provenance verification, and sanitized errors. No arbitrary file/SQL/URL
inputs, secrets, new egress or RQ work. Direct filesystem and authorization
tests are mandatory alongside valid-state tests.

Evidence planned in [field matrix](field_matrix.md) and
[implementation plan](implementation_plan.md). Documentation reviews are not
runtime evidence. Before implementation, finalize route/payload/feature entry
contracts, obtain exact owner approval, two independent read-only contract
reviews plus UX review, disposition, and standalone ancestor commit. Request
commit authority if not granted; do not start code from an uncommitted proposal.
