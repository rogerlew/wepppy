# Independent M0 contract reviews and disposition

Date: 2026-11-18 UTC. Scope: standalone contract, ADR-0148, dependency probe and
package scope at checkpoint preparation. Reviewers were read-only independent
agents; these are not independent human GitHub approvals.

## Correctness reviewer: /root/csv_contract_correctness

Initial verdict: hold for two medium findings. Duplicate projected labels lost
values through the Python oracle's dictionary conversion (x with units m plus
x (m), values 1,2, yielded 2,2). Disposition: reject projected-name collisions
as an explicit v1 and integration-blocking exclusion. The error-code catalog and
provenance schema were incomplete. Disposition: enumerate finite codes and exact
strict provenance keys/types/path inventory. Reviewer re-read the changes and
confirmed both findings closed; no medium/high findings remain. Concrete bounded
standalone choices fit the user's implementation authorization. Baseline/corpus,
second review and synchronized living status required before checkpoint commit.

## Security reviewer: /root/csv_contract_security

Initial conditional pass with two low findings: openat2 was inaccurately cited,
and total scratch cap omitted abandoned crash state. Disposition: name the actual
pinned-directory openat/O_NOFOLLOW pattern and qualify the cap as live admitted
scratch; require operator crash reconciliation. Record parent SIGKILL child
survival until OS limits/operator termination. Reviewer confirmed findings closed
and conditional dependency acceptance for standalone evaluation. Verified probe
lock b4eb3e3474fb51f035200359f798cc0c6219045a0bac0f06af96c5e71f0e69d8.
Audit zero known vulnerabilities; chrono informational maintenance advisory remains
explicit. No medium/high architecture findings. Runtime preflight/allocation,
provenance, malformed Arrow IPC, cancellation and valid-state evidence remain
mandatory before final acceptance.

## Integrator disposition

All pre-implementation findings closed. Concrete contract preserves the agreed
standalone scope. Dependency acceptance is conditional for evaluation; this is
not a production release. Ratification is under the user's explicit instruction
to implement the package; no further runtime behavior or scope authorization is
inferred. The checkpoint ancestor contains contract, ADR, these reviews and M0
evidence. Final reviews must inspect actual code and artifacts independently.

## Measurement amendment

Both original independent reviewers approved adding strict `peak_rss_kib` and
`cpu_seconds` success fields to retain actual per-child getrusage measurements.
They require non-boolean finite numeric validation and separate parent/aggregate
memory evidence. Security review also accepted removal of csv from the candidate
graph, conditional on serializer byte-parity tests and updated lock/audit.

## Reviewed metadata compatibility amendment

Both independent reviewers accept explicit rejection of non-UTF-8 metadata as a
standalone v1, integration-blocking exclusion. Rust's upstream metadata model
requires UTF-8 before projection; rewriting input or adding a second decoder is
outside this bounded experiment. Syntactically invalid UTF-8 JSON remains ignored;
valid JSON with invalid pandas shape is rejected. Oracle runtime is Python 3.12,
including CR quoting; exact patch version is retained with benchmark evidence.
Direct rejection and parity tests remain mandatory. No production behavior changes.
