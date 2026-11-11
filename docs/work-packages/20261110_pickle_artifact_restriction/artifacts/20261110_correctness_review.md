# Correctness and user-experience review - Pickle artifact restriction

## Metadata

- **Package**: `docs/work-packages/20261110_pickle_artifact_restriction/`
- **Reviewer**: unassigned.
- **Date**: 2026-11-10 Pacific / 2026-11-11 UTC.
- **Scope reviewed**: proposed Bootstrap, browse, D-Tale, listing, download, and
  documentation behavior; implementation does not yet exist.
- **Related security artifact**: [security review](20261110_security_review.md).

## User Outcome

- **User goal**: safely manage project artifacts and inspect supported tabular
  data without exposing the service to executable serialization.
- **Success presented to the user as**: actionable Bootstrap rejection or HTTP
  415 for pickle interaction; existing file remains visible/downloadable.
- **Failures that may reach the user**: "pickle files are not allowed" at Git
  push and unsupported-media response for preview/D-Tale.
- **Partial-state behavior**: rejected push is not accepted/logged; existing file
  remains unchanged; no materialized or D-Tale dataset state is created.

## Failure-Class Coverage

The shared error is treating file admission/authorization as proof that Python
deserialization is safe. The bounded assessment is in
[the failure-class matrix](20261110_failure_class_matrix.md). Closure requires
every positive reader, link, capability tuple, document, and stub to agree.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| New Bootstrap `.pkl`/`.pickle` | no | reject before log/parse | Pending |
| Existing pickle file | yes as opaque artifact | list and byte download only | Pending |
| Existing pickle preview/D-Tale | no | explicit 415, no side effects | Pending |
| Empty/malformed pickle bytes | no interactive parse | same 415 independent of content | Pending |
| Allowed Bootstrap text input | yes | existing validation succeeds | Pending |
| CSV/TSV | yes | existing preview/D-Tale succeeds | Pending |
| Feather/Arrow | yes | existing D-Tale succeeds | Pending |
| Parquet | yes | existing lazy preview/D-Tale succeeds | Pending |
| Missing file | no | existing not-found behavior | Pending |

## User-Reachable Error Policy

| Condition | Expected? | User-visible result | Rationale |
| --- | --- | --- | --- |
| Pickle path in Bootstrap push | Expected invalid | stable rejection naming path/suffix | Format is forbidden |
| Pickle preview | Expected unsupported | HTTP 415 | Opaque download-only artifact |
| Pickle D-Tale request | Expected unsupported | HTTP 415 | No safe interactive reader |
| Raw authorized download | Expected valid | exact bytes | No server deserialization |
| Supported-format parse failure | Existing behavior | existing bounded error | Unchanged scope |

## Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| Git request | denied suffix identified | real pre-receive input/error | Pending |
| Git persisted state | rejected commit not logged | ref/push-log readback | Pending |
| Browse listing | file shown, no actions | rendered HTML/files JSON | Pending |
| Preview/D-Tale | no reader/loader/materialization | call sentinels | Pending |
| Download | source bytes preserved | SHA-256 before/after | Pending |
| Supported control | unchanged behavior | focused response/readback | Pending |

- **Direct unmocked failing boundary**: pending real temporary Git and byte-file
  tests; reader calls use sentinels to prove absence.
- **Actual-project/environment evidence**: scoped deployment smoke pending.
- **Highest completion claim supported**: diagnosed.
- **Deployment/recovery still outstanding**: all implementation and rollout.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-F2 | Medium | Legacy artifact access | A broad ban could hide/delete existing files, contrary to approved scope | Browse filesystem contract | Preserve listing/download and test bytes | Open |
| COR-F2A | Medium | Supported tabular formats | Shared suffix edits could regress valid CSV/Feather/Parquet behavior | Capability tuples/readers | Retain focused positive controls | Open |

## Verdict

- **Gate status**: fail.
- **Unresolved findings**: High 0; Medium 2; Low 0.
- **Release recommendation**: hold pending focused evidence.
- **Reviewer sign-off**: pending.

The approved focused suite is the correctness gate. A broad suite is intentionally
not required and would not replace the direct artifact/readback evidence.
