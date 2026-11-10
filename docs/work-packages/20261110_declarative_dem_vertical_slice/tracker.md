# Tracker — Declarative DEM vertical slice

## Quick Status

**Started / last updated**: 2026-11-10

**Phase**: Ready for controlled canary handoff; M5 live acceptance pending

**Next**: Receiving operator publishes/reviews the candidate and authorizes the bounded canary

**Security**: High; independent source and staged deployment review passed

## Task Board

- [x] Scaffold package, active ExecPlan, checkpoint/review artifacts and evidence ledger.
- [x] M1: identify source/viewer fixture, exact paths, interfaces and runtime verifier;
      amend contracts, obtain two independent reviews and checkpoint ancestor commit.
- [x] M2: shared DEM task provenance and on-demand regression coverage.
- [x] M3: independent engine/image adapter; inactive bounded worker preparation.
- [x] M4: real local finalization/viewing; cluster endpoint evidence belongs to M5.
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

[Validation matrix](artifacts/validation_matrix.md) records actual local evidence
and pending receiving gates. Contract ancestor is `d6e101ab8`. Independent
[correctness](artifacts/20261110_correctness_review.md),
[QA](artifacts/20261110_qa_review.md) and
[security](artifacts/20261110_security_review.md) report zero open high/medium
findings in the reviewed local candidate. No live deployment approval is implied.

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

Continue the [active ExecPlan](prompts/active/implementation_execplan.md) at the
receiving M5 gate. [Deployment handoff](artifacts/deployment_handoff.md) links the
inactive open-wepp-org package and runbook. Source implementation and local tests
are complete subject to final gates below; live runtime identity, browser/download,
production-equivalent workflow and worker-loss acceptance remain unexecuted.

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

## M1 checkpoint and implementation progress

Contract ancestor: `d6e101ab8`, committed before implementation edits. The tracker
revision entry was recorded after implementation began; the commit/review ancestry
itself preceded every code edit. M1 contract review is complete; M2–M4 implementation
and direct boundary validation are active. No cluster deployment has occurred.

Local baseline `metastatic-interconnection` produced EPSG:32611, 37 x 26 pixels,
962 valid cells, elevation range 989.341–1066.154 m and center query 1032.540 m.
Raster SHA-256: `10b6b95c574f8a90e6fe5ebed0a56ae68f90f38129cd434c8d7cb04302698134`.
Original job took 3.960 s. An isolated local worker then ran updated shared DEM
code successfully in 3.684 s (job `a7b1626b-9783-4b2a-9675-181de81067b0`).
Neither timing establishes a global performance budget.

Focused gates: 14 original new boundary tests passed; ordinary regressions
ultimately passed 150 tests across two runs after the worker test double acquired
RQ's real `perform` interface. Six canonical archive tests passed, including
interrupted restore, alias/extra raster rejection and byte preservation. Expanded
protocol/real RQ rejection suite: 19 passed. Further integration/UI/gates pending.

Interim independent reviews found archive aliases/extra protected paths, executable
Pod hooks, positional-path task binding, science-to-finalization fingerprint drift,
initialization failure truth, duplicate completion writes and stale observation
publication. Fixes are implemented; post-fix review and final gates remain pending.

## Local review and receiving preparation

Correctness/security/QA passed after reviewed fixes; findings and failed evidence
are retained. Real adapter/RQ/NoDb/Git/manifest fixture success and failure matrix
passed. The QA manifest fault injects inside the real shared writer; it confirms
READONLY remains, error state is durable and repeated finalize does not replay.
Frontend: 124 suites/1069 tests passed, lint passed. Stub hygiene and regenerated
RQ graph checks passed. Full Python and final focused gates are pending below.

Reviewed inactive renderer/template/runbook/receiving package copied to
`/workdir/open-wepp-org`; no active resource inclusion or image change. All guard
consumers must be deployed before admission, and rollback must retain guards for
existing declarative projects. This rationale and sequence are in
`artifacts/deployment_handoff.md` and receiving `docs/operations/declarative-dem-canary.md`.

## Ready-for-handoff disposition — 2026-11-10

Implementation `185429547`; reviewed inactive receiving preparation `5c98b96`.
Final scoped gate: 102 passed; corrected legacy cache-ordering double module:
65 passed. Frontend 1069 passed, lint/stubs/RQ graph/docs checks passed. Retained
broad continuations deduplicate to 6401 passed/241 skipped with one confirmed
preexisting Runs-list TTL-help assertion; exact baseline reproduction and the
original session-reset limitation are in `artifacts/validation_matrix.md`.
No unresolved high/medium source findings. No image publication, push, active
infrastructure change or deployment occurred. M5 and final package closure remain
with the receiving canary; no remaining local implementation task blocks handoff.

## Receiving execution — 2026-11-10

Roger authorized handoff execution and then explicitly authorized table migrations.
Receiving PR202 deployed b3786ae7e (amd64 child 0effe388...) and additive notification
revision f6b8d27a901c after fresh encrypted backup. Fleet/native/ordinary existing
reader and authenticated notification checks pass. First DEM UUID
01b51a4d-a617-46ef-a7a2-072520dc9e5b failed initialization, science not dispatched.
Real NFS EOPNOTSUPP on redundant RedisPrep xattr writes reproduced in isolated
ordinary constructor; bounded conformance repair underway. No M5 completion claim.
Receiving durable record: open-wepp-org docs/work-packages/20261110-declarative-dem-canary.

### Receiving correction validation

The shared snapshot regression now preserves original mode before comparing NFS
attributes, skips only identical inherited values and verifies exact final mode
and attributes. A regression first failed against old code; the corrected module
passed a real NFS ordinary-constructor/repeated-snapshot probe at UID:GID1000:993,
umask0022, with original mode/ACL/security label unchanged. No privileges changed.
Independent review also confirmed RQ rejects `__main__` function objects from the
actual `python -m` adapter entrypoint; both jobs now enqueue canonical import names.
The lifecycle matrix covers both imported and `__main__` function identities.

Forest Docker-wrapper focused validation with a dedicated disposable Redis socket:
**106 passed**, no skips (47.21s). The earlier run's 35passes/62skips reflected a
missing test Redis executable; it is not the acceptance result. RQ graph check
passes. No full-suite claim is made; broad-suite limitations from the original
handoff remain. Independent source correction review is retained in the receiving
security review. Corrected image publication and fresh-UUID live acceptance follow.
