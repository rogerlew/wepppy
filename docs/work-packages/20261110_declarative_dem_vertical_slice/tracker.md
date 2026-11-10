# Tracker — Declarative DEM vertical slice

## Quick Status

**Started / last updated**: 2026-11-10 20:18 UTC

**Phase**: M1 concrete contract approved; ancestor checkpoint preparation

**Next**: Commit reviewed contract checkpoint; implement M2–M4; prepare deployment handoff

**Security**: High; dedicated review pending

## Task Board

- [x] Scaffold package, active ExecPlan, checkpoint/review artifacts and evidence ledger.
- [ ] M1: identify source/viewer fixture, exact paths, interfaces and runtime verifier;
      amend contracts, obtain two independent reviews and checkpoint ancestor commit.
- [ ] M2: shared DEM task provenance and on-demand regression coverage.
- [ ] M3: independent engine/image adapter and bounded queue/worker execution.
- [ ] M4: read-only finalization and real derived viewing task.
- [ ] M5: open-wepp-org validation, fault cases and archive/readback evidence.
- [ ] M6: final correctness, QA, security, documentation and closeout.

## Decisions

**2026-11-10 20:18 UTC** — User requested a work-package scaffold to complete the
vertical slice on open-wepp-org. Full builds, canonical project storage, Git audit,
operator-only access and protected read-only completion are accepted direction.
Use the spec's recommended DEM slice as the planning baseline; exact runtime
verification and failed/canceled protection mechanics require M1 disposition.
No Bootstrap, deterministic/comparison machinery or compatibility layer.

## Risks and dependencies

Actual image/attempt binding is unproven (ARCH-3 / INTEGRITY-1). Cluster worker
capacity must be inspected without displacing active jobs. Existing read-only
finalization refreshes catalogs and creates a browse manifest; permissible later
writes and failure ordering need direct tests. A DEM-only project may not support
all reports: select a genuine existing DEM viewer/derived task, not a fake report.
SOPS is deferred for engine-specific secret storage, not permission to bypass the
infrastructure repository's existing secret delivery requirements.

## Verification and evidence

[Validation matrix](artifacts/validation_matrix.md) is entirely pending.
[Contract checkpoint](artifacts/20261110_contract_decision.md) is not ratified or
committed. [Correctness](artifacts/20261110_correctness_review.md) and
[security](artifacts/20261110_security_review.md) reviews are not performed.

Run focused tests as behavior lands; required closeout includes broad Python,
applicable frontend/stub checks, RQ graph validation and live job-tree inspection,
scoped docs lint, actual generated artifact and read-only workflow checks. Record
commands/revisions/results rather than check boxes without evidence.

## Progress Notes

**2026-11-10 20:18 UTC** — Planning only. Read package/ExecPlan conventions,
contract-first standard, local DEM/read-only task source and deployment guidance.
All seven package documents, the linked spec and root tracker pass scoped doc lint;
package spelling preview produced no changes. No runtime tests were warranted for
this documentation-only scaffold. Preserve unrelated
working-tree changes and do not create/switch branches.

## Handoff

Start the [active ExecPlan](prompts/active/implementation_execplan.md) at M1 when
implementation work is requested. This scaffold is not a completed contract
checkpoint or deployment authorization. Prepare concrete reviews/configuration
before any required approval; do not request repeated approval for already accepted
product policy. Update this tracker and the ExecPlan at every milestone.

## Execution update — 2026-11-10

User authorized execution through deployment-ready handoff. Selected public
`ned1/2024`, 30 m, bounded Idaho extent and existing zero-write HTTP elevation
query. Two independent contract reviews passed after restore/finalization fixes;
see `artifacts/20261110_contract_reviews.md`. No cluster deployment authorized.
Local baseline run `metastatic-interconnection`, job
`88af4419-a979-4718-99d0-cf4e5f441443`, was created through ordinary initialization
and enqueued on the existing local default queue; artifact readback pending.
Current source baseline is `3a113ac28df9c5b2cdf453a4223e1c42e83b81bb`.
The local environment has no `kubectl` executable; live Kubernetes verification
remains a deployment handoff prerequisite, not a claimed local result.
