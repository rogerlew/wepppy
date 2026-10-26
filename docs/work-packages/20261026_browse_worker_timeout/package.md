# Browse filesystem transparency and production timeout

Status: Closed locally 2026-10-26. Owner: Roger. Timestamps: UTC.

## Objective and scope

Implement the explicit 120-second wepp1 browse timeout and Roger's subsequent
2026-10-26 instruction to revert generic Roads lifecycle filtering. Generic
browse/download must expose actual files; only security and PII guards may
restrict them. This includes file metadata/schema, aria2c inventories and direct
D-Tale file viewers. Remove stale raw-archive exclusions where found. Preserve
model reports/query/producer eligibility, resource auth, path containment,
sensitive-path guards and ordinary lazy-viewer byte consistency.

Close and commit before separate deployment. No production code/service changes
or project mutations are authorized in this package.

## Trigger and evidence

Monday October 26 browse workers timed out at 18:21:10 and 18:24:43 UTC;
directory listing logs recorded 65.2 seconds. This is evidence of worker
unresponsiveness, not proof of its underlying cause. The NFS infrastructure
report documents loaded create/rewrite times near 57 seconds and RPC queuing.
Mariana's October 23 dressy-kiss HTTP 500 arrived in about two seconds and is
not established as a worker-timeout incident. See the retained investigation.

## Complexity and security

Reuse existing filesystem routes and reverse the finite Roads file-layer patch.
No new services, dependencies, permissions, retries or visibility abstractions.
Security impact: low with existing auth/containment/PII controls preserved;
explicit negative regression evidence is required. Contract reviews precede
implementation. Runtime report lifecycle locks remain intact; generic reads no
longer promise a producer-coordinated snapshot.

## Acceptance and boundaries

Canonical authority is docs/schemas/browse-filesystem-contract.md. Real file
listing, manifest and byte readback must pass for absent/empty/populated/legacy,
unreceipted/stale/locked and permitted-alias states. Existing auth/path/PII
negative cases must pass. Direct D-Tale opens must not require Roads publication;
lazy generation changes remain changed_source. Validate large-project inventory.
Run targeted suites and broad sanity; record limitations explicitly.

The full composed wepp1 configuration must differ only by --timeout 120 and the
Gunicorn parser must retain eight workers and graceful_timeout 30. Deployment,
production recovery and the exact historical 500 remain outside local closure.

## Precedent and hypothesis

Reuse the existing Gunicorn setting and the infrastructure report's measured
NFS evidence. The fork-read-retry package (20260906_fork_read_retry_hardening)
uses a 120-second initial-read budget; this change does not copy its retries.
Hypothesis: allowing 120 seconds of worker silence reduces worker recycling
under temporary stalls. Compare timeout counts per hour and download latency
before/after rollout. Review after 14 days of operation; consider reducing the
setting after storage/event-loop remediation and representative workload checks.
Durable signals and rollback criteria live in the deployment knowledgebase.

## Deliverables

Configuration, ADR-0108, operator guidance, investigation, correctness/QA
review and execution evidence. Deployment and root-cause remediation remain
separate; package closure certifies local filesystem-transparency and timeout
implementation and validation, not production rollout or the historical 500 cause.

## Closure

Local implementation and independent reviews are complete. Targeted suite: 333
passed. Broad suite completed in segments: initial 9,931 passed and 155 skipped
before one obsolete filename-ban expectation; corrected diff regressions: six
passed; resumed suite: 1,863 passed and one skipped. Segments overlap at the diff
module; counts must not be added blindly. No application source changed after
the initial broad run. See execution evidence for commands and environment.
Production deployment, durable logging and the historical 500 investigation
remain follow-ups.
