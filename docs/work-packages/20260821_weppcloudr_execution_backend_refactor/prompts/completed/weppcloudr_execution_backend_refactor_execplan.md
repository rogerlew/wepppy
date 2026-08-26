# Implement the WEPPcloudR Execution Backend Contract

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while executing it.

## Purpose / Big Picture

WEPPcloud currently renders DEVAL In The Details by having an RQ worker invoke
`Rscript` inside the long-running Compose `weppcloudr` container. Introduce the
deployment-neutral execution boundary defined by
`docs/schemas/weppcloudr-render-execution-contract.md` without regressing that
path. At completion, Compose still uses Docker exec with unchanged mounts, and
the repository contains a deterministic, tested Kubernetes Job backend and
one-shot renderer interface ready for a separately governed image/deployment
package. The observable Compose proof is a successful render of the authorized
forest run after restarting only its development stack.

## Progress

- [x] (2026-08-21 18:04 UTC) Scaffold package, tracker, active ExecPlan, and
  pending review gates.
- [x] (2026-08-21) Ratify the canonical execution contract at commit
  `946f14518` and record review dispositions.
- [x] (2026-08-21) Capture baseline implementation, tests, Compose configuration, and mount
  evidence before edits.
- [x] (2026-08-21) Implement the shared request boundary and behavior-preserving
  `docker-exec` adapter.
- [x] (2026-08-21) Implement repository-side `kubernetes-job` orchestration, receipt/state
  handling, and the strict one-shot renderer surface.
- [x] (2026-08-21) Update tests, RQ catalog, stubs, configuration, and documentation.
- [x] (2026-08-21) Complete correctness, QA, and security review with findings
  dispositioned.
- [x] (2026-08-21 19:27 UTC) Execute and document the authorized forest Compose
  integration proof.

Kubernetes container building, publication, manifest application, and live
cluster testing are not milestones in this plan.

## Surprises & Discoveries

- The current Compose path runs independent `Rscript` processes through Docker
  exec; moving it behind a single Plumber process would alter concurrency.
- PUP runs can contain links to their parent run. Consequently, `run_root`, not
  a more granular `active_root`, is the narrowest compatible project mount and
  working directory.
- RQ worker count bounds steady-state dispatch but is not a hard cross-queue
  concurrency guarantee. A future Kubernetes deployment may add a logical
  permit/control-plane cap without changing this package's Compose path.
- A Kubernetes implementation can be unit/integration tested in-repository,
  but it is not deployable evidence until a digest-pinned image and cluster
  manifests are built and validated by the follow-up package.
- The first forest render exposed a real cross-container permission mismatch:
  the root-owned artifact was `0640` and unreadable by the worker. Explicit
  `0644` publication fixed the serving contract; the second render passed.
- Event delivery needs its own durable acknowledgment after cleanup. Otherwise
  a transient sink outage can strand a cleaned receipt outside the reaper even
  when reconciliation itself is isolated per receipt.
- The canonical broad suite cannot run its Compose CLI canary from inside the
  test container because that environment has no nested `docker compose -f`.
  A rerun excluding only that environment-specific test is recorded separately.

## Decision Log

- **2026-08-21 — Preserve Compose topology.** Compose continues to select
  `docker-exec`; no Compose mount, volume, service, socket, or container-name
  edits are authorized. This minimizes regression risk.
- **2026-08-21 — Keep WEPPcloudR separate.** The Kubernetes renderer remains a
  narrow R image rather than inheriting the WEPPpy worker image.
- **2026-08-21 — Wrap Jobs with RQ.** The existing RQ task owns user-visible
  lifecycle integration while the backend creates/watches/cancels one Job.
- **2026-08-21 — Use the run WD boundary.** Mount and set the working directory
  to canonical `run_root`; pass `active_root` as a validated path within that
  view, including expected PUP links.
- **2026-08-21 — TTL planning value.** Use 20 minutes after result collection as
  the initial configuration target, inside the operator's 10–20 minute range.
  Do not imply this is deployed by this package.
- **2026-08-21 — Publish through a fenced staging file.** Render into `/tmp`,
  copy under the run-scoped fence using no-follow directory descriptors, and
  atomically rename a mode-`0644` artifact. Track staging ownership so cleanup
  never removes another invocation's file.
- **2026-08-21 — Acknowledge receipt events durably.** Cleaned receipts remain
  reaper-eligible until the exact state event is accepted and acknowledged;
  sink failures are isolated so later receipts continue.

## Outcomes & Retrospective

Repository implementation and the authorized Compose integration are complete.
The explicit Docker adapter retained the existing stack and mounts; the forest
render completed in about 16 seconds and produced a 14,077,008-byte HTML report.
The Kubernetes request, Job-spec, receipt/reaper, cancellation, and one-shot R
surfaces are deterministic and tested, but no image or cluster deployment was
built or validated. Correctness, QA, and security gates all passed. The broad
suite passed every package test and reached 4,593 passes before an unrelated
pre-existing Topanga cwd-dependent test stopped the run; the canonical broad
command also has a documented nested-Compose environment stop.

## Context and Orientation

The current task lives in `wepppy/rq/weppcloudr_rq.py`. The browser/report
enqueue boundary is `wepppy/weppcloud/routes/weppcloudr.py`, with canonical run
context in `wepppy/weppcloud/routes/_run_context.py`. The current R renderer is
under `weppcloudR/`. Forest uses `docker/docker-compose.dev.yml`; Docker
instructions identify `forest.bearhive.internal` as the development host and
`wc.bearhive.duckdns.org` as its public endpoint.

The normative behavior is
`docs/schemas/weppcloudr-render-execution-contract.md`. Update
`wepppy/rq/job-dependencies-catalog.md` whenever enqueue/dependency edges
change. Read the nearest `AGENTS.md` before touching each subsystem.

The designated integration target is:

<https://wc.bearhive.duckdns.org/weppcloud/runs/branching-hubbub/disturbed9002_wbt/>

Authority covers a normal DEVAL request and restart of only the forest
development Compose stack. It excludes run deletion/rebuild, mount changes,
other hosts, production promotion, and Kubernetes operations.

## Plan of Work

### Milestone 1: Characterize and freeze Compose behavior

Record `git status`, revision, relevant service configuration, and the source
mount definitions for every Compose variant. Render the forest development
configuration with the repository's canonical `wctl`/Compose tooling and save
the `weppcloudr`, RQ-worker, `/wc1`, `/geodata`, source, cache, and Docker-socket
mount facts in the tracker or an artifact. Read existing RQ/route tests and add
characterization coverage before restructuring production code.

This milestone is complete when the current command, environment, output/cache
behavior, failure translation, and mount topology can be compared mechanically
after implementation.

### Milestone 2: Extract the execution boundary and preserve Docker exec

Add the versioned request model and explicit backend selection described by the
contract. Move current subprocess behavior into a `docker-exec` adapter without
changing its effective command, container, mounts, cache outcome, RQ response,
or route behavior. Accept canonical `run_root` at new enqueue sites while
supporting only the contract-authorized legacy queued-job shape. Reject unknown
backend values; never fall back across backends.

Use narrow exceptions and preserve canonical RQ errors. Bound protected logs,
validate artifacts, and keep lock/fencing ownership explicit. Do not edit any
Compose YAML in this milestone.

This milestone is complete when focused tests prove parity and a source diff
shows no Compose configuration changes.

### Milestone 3: Implement testable Kubernetes and one-shot R surfaces

Implement the Job request/spec builder, durable receipt, observation mapping,
reconciliation, cancellation, timeout, and terminal-result logic behind an
injectable client/control-plane boundary. Tests must use deterministic fakes or
a disposable local API and cover success, failure, timeout, cancellation,
duplicate/retry, missing Job, malformed response, and stale fencing cases.

Add the strict request-v1 one-shot R entrypoint. It must use `run_root` as its
working/mount boundary, validate `active_root`, emit the contracted result and
artifact metadata, and avoid server-global mutable state. Test representative
PUP links to the parent without adding finer-grained mounts.

Do not build an image, write target-cluster manifests, invoke a cluster, or
claim the backend is deployed. This milestone is complete when repository tests
prove the interfaces and clearly label external deployment dependencies.

### Milestone 4: Documentation, validation, and independent review

Update the RQ dependency catalog/graph if enqueue edges changed, plus affected
configuration, operator, and module docs. Run focused tests first, then the
required broad gates. Request independent correctness, QA, and security review;
record every finding and disposition it before forest execution. Medium/high
findings block closure.

### Milestone 5: Authorized forest Compose integration

Before mutation, connect only to the forest development host and establish the
canonical checkout/stack identity. Capture repository revision and dirty state,
the rendered Compose configuration, `docker inspect` mount data for
`weppcloudr` and affected workers, current health, and the existing DEVAL
artifact timestamp/hash if present. Stop if unrelated dirty changes overlap
deployment files or if the target resolves to forest1/production.

Deploy through the repository's canonical forest development workflow and
restart the smallest set of affected services; authority permits the entire
development stack if that is operationally required. Do not alter mounts or
prune volumes. Confirm services recover before requesting:

    https://wc.bearhive.duckdns.org/weppcloud/runs/branching-hubbub/disturbed9002_wbt/report/deval_details?no-cache=1

Use the normal authenticated/public browser flow as required. Capture the RQ
job identifier and terminal payload, structured worker/backend evidence showing
`docker-exec`, bounded renderer logs, and the resulting non-empty readable HTML
artifact with timestamp/hash. Re-inspect mounts and compare them with baseline.
Record durations; the expected render is one to two minutes, but use the
contract timeout rather than declaring failure at that expectation.

If the smoke test fails, preserve logs and receipts, avoid deleting the run,
and roll back only this package's deployed change using the established forest
workflow. Never reset or overwrite unrelated dirty state.

## Concrete Validation Commands

Run commands from `/home/workdir/wepppy` unless the nearest instructions say
otherwise. Adjust a test path only if discovery establishes its canonical name.

    wctl run-pytest tests/rq/test_weppcloudr_rq.py
    wctl run-pytest tests/weppcloud/routes/test_deval_loading.py
    wctl check-rq-graph
    wctl check-test-stubs
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260821_weppcloudr_execution_backend_refactor
    git diff --check

Also compare all `docker/docker-compose*.yml` files with the package-start
commit and compare before/after rendered forest mount snapshots. Run
`wctl check-rq-graph`; if it reports catalog drift, regenerate only with the
documented command and review that diff.

## Acceptance Criteria

- Compose backend selection, commands, cache/results, RQ payloads, and mounts
  remain compatible; Compose configuration files are byte-for-byte unchanged.
- Tests cover request-v1 validation, legacy queued arguments, both explicit
  backends, fencing, reconciliation, cancellation, timeout, bounded logs,
  artifact validation, and expected PUP links.
- The repository contains the one-shot renderer and Kubernetes orchestration
  interfaces, but handoff clearly states that no Kubernetes image or deployment
  was produced or validated.
- RQ graph/catalog, stubs, and affected documentation agree with production
  code, and required validation gates pass.
- Correctness, QA, and security artifacts contain no unresolved medium/high
  findings.
- On forest, the designated no-cache DEVAL request completes successfully via
  `docker-exec`, produces valid HTML, and before/after mount evidence matches.

## Idempotence and Recovery

Repository edits and tests are repeatable. Forest preflight and inspection are
read-only. A repeated no-cache DEVAL request may replace only its normal report
artifact/log state and must use the same locking/fencing rules. Compose restart
must not recreate volumes or change mounts. On interruption, resume from the
durable receipt/job state rather than creating an uncorrelated render. Store
evidence in this package; do not store secrets, cookies, or unredacted protected
logs.

## Artifacts and Notes

Expected evidence includes baseline/final Compose mount snapshots, focused and
broad test logs, RQ graph output, completed review artifacts, and a forest
integration record containing timestamps, revision, services restarted, job
identity, backend, terminal result, artifact metadata, and rollback status.

## Interfaces and Dependencies

The implementation must expose an explicit backend contract compatible with
the canonical schema, with dependency-injected Docker and Kubernetes clients so
state transitions are testable. Required external runtime dependencies must be
declared explicitly; missing clients/configuration fail closed. Adding a new
dependency requires the repository dependency-evaluation standard. The future
Kubernetes package owns renderer/control-plane image digests, RBAC, storage,
admission, concurrency policy, and live cluster evidence.
