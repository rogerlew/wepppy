# Draft bounded shared-batch pilot implementation specification

Status: **design only; canonical checkpoint/review required before implementation**.
Scope: operator-authorized bounded admission guard and owned-scope pilot using
the existing eight batch consumers. General asynchronous refresh stays disabled.
This draft follows the [bounded proposal](20261027_bounded_admission_proposal.md)
and records deployment constraints rather than substituting another private-queue
canary for shared-worker evidence.

## Minimal execution architecture

Keep `QUERY_CATALOG_REFRESH_ENABLED=false` in every existing service. Ordinary
`request_catalog_refresh` calls retain their synchronous behavior; the normal
scheduler remains disabled. Do not replace production root configuration with
pilot roots or introduce a fifth namespace. Create uniquely named owned fixtures
under `/wc1/runs/qc/qcat-pilot-<opaque-id>-<suffix>` using the existing canonical
root, namespace, coordination directory and service identity.

Add an explicit internal `pilot_id` argument to refresh admission, inventory
admission and their worker entry points. This is the only exception to the
disabled admission/execution checks. It requires a registered operator manifest,
an approved exact scope, and a matching admitted job record. Merely supplying
the argument cannot create authority. `catalog_worker_configuration` advertises
new admission/pilot capability independently of its unchanged `enabled=false`.
Workers must advertise from installed code through normal
`WepppyRqWorker.register_birth`; never synthesize or patch registrations.

An installed operator CLI should expose register, status, tick, pause and resume
operations. It accepts a pilot identifier and validated fixed-schema manifest,
not a queue name, callable, source code or executable payload. It uses the existing
RQ Redis connection and fixed `batch` queue. No public route, service, pool or
queue is added. An operator loop invokes the reviewed tick entry point at the
existing 30-second cadence and stops new admissions at the recorded deadline.
Controller restart resumes the same manifest/counters and cannot restart its
clock. Stop conditions belong in the admission transaction, not only the loop.

Candidate file boundary: `wepppy/rq/query_catalog_rq.py`, its existing inventory
helper, admission/manifest helpers, and installed `tools/query_catalog_pilot.py`;
associated tests, contracts, ADR, operator guide and dependency
catalog change together. The shared filesystem protocol remains version 1.
Current `catalog_refresh.py` and `rq_worker.py` match the production baseline;
their producer behavior and normal worker lifecycle need no redesign.

## Manifest and job authority

The operator registers one immutable manifest containing pilot identifier and
generation, original start/deadline, exact participant configuration digest,
exact approved scope locators, scope IDs/incarnations and directory identities,
and the fixed cumulative budgets: 25 refresh job IDs and two inventory job IDs.
Registration validates owned fixture paths, nofollow containment and markers
before creating pilot metadata. Scope selection is not supplied by queued
arguments independently of this manifest.

Pilot inventory initializes its frontier from those exact approved locators,
not the full production roots. Inventory may not recursively discover unlisted
nested scopes. Scope/root mapping still uses the installed canonical configuration;
the worker cannot substitute arbitrary roots from a payload. Refresh execution
rechecks current configuration, admitted job binding, scope/incarnation/directory
identity, nofollow containment and READONLY before project work.

Every admitted job ID binds to manifest generation, kind, configuration and
scope identity, with a capacity reservation and cumulative counter increment in
the same Redis transaction as RQ enqueue. Ambiguous enqueue replies are recovered
from that committed record. Coalescing an existing job consumes no new cumulative
attempt. Failure/retry requires a new job ID and consumes the applicable remaining
budget. Automatic RQ retry or manual same-ID requeue must not bypass that debit;
pilot attempts use only the guarded successor path. Pause/resume preserves
counters, original deadline and scope allowlist.
Missing or malformed manifest/ledger state denies new admission; it is never
silently initialized by a worker, scheduler tick or controller restart. Redis-loss
recovery requires explicit operator reconciliation and cannot infer unused quota
from missing jobs. No automatic replacement manifest or fresh budget is allowed.

## Shared admission guard

Use one guard/permit ledger for the existing shared `batch` queue, not one ledger
per configuration, scope, pilot or host. All catalog enqueue paths participate,
including general producer admission when later enabled, recurring reconciliation,
inventory and retries. The new-job cap is `min(7, compatible_live_consumers)`;
existing work above a reduced live count drains without issuing new permits.
Seven is the operator-ratified bounded pilot policy, not automatic approval of a
future general-enablement default. It is not a permanent reserved-worker guarantee
when fewer than eight are live.

Queued, started, deferred, scheduled and reserved catalog attempts consume slots.
A worker disappearing is not sufficient to release a slot. Release must establish
terminal job state and ownership atomically; missing/ambiguous job state remains
reserved until explicit recovery. Initialization must reconcile any already
outstanding batch maintenance, not assume a missing permit ledger means zero.

WATCH the queue's waiting-list key and relevant reservation/job/consumer/pilot
state while making the admission decision. An ordinary queued job blocks a new
catalog job regardless of its position. A concurrent ordinary enqueue must
invalidate the transaction before catalog enqueue commits. Classify only raw
safe IDs, known ownership markers and primitive job fields; never deserialize
arbitrary jobs for policy checks. Unknown/corrupt waiting entries are conservative
ordinary backlog. The exact candidate transaction must be reviewed and tested
with real Redis before asserting this interleaving property.

Once an ordinary backlog, configuration mismatch, artifact failure or unexpected
job-count growth trips the pilot, persist paused/failed state. A five-minute
ordinary queue wait is a retained pilot failure trigger, not a completion or
preemption guarantee. New admissions require explicit operator resume and still
must satisfy the same deadline, budgets, queue and capacity checks. Existing
admitted jobs remain authorized to execute/drain after pause or expiry; those
states do not acknowledge receipts or cancel scientific work. Ordinary-wait
monitoring continues throughout paused/expired drain. Losing the operator monitor
must deny new admission through its owned Redis controller lease/heartbeat;
the reviewed contract must pin its timing/recovery before implementation. No
extra monitoring service is introduced. Public maintenance polling keeps its
existing generic shape; pilot identifiers, manifests, locators and diagnostic
details remain operator-only.

Existing `WORKERS_SUSPENDED` is a fleet-wide RQ stop and must not be used as the
pilot pause mechanism. Existing `suspend_catalog_refresh(scope_id)` is useful
per-scope control but does not cover inventory/global capacity. Add a catalog-only
pause field/key in the same guarded infrastructure; preserve existing controls.

## Deployment evidence and unresolved release mechanics

Read-only production preflight found both `wepp1` and `wepp2` on clean tracked
`master` at `813d912be1c8f6f13b6fc60cecebbef9259cd36e`. Local HEAD is
`f8f956c7a`, with unrelated intervening Roads, browse/Flask and deployment changes.
A plain production pull would release more than this pilot's candidate files.

Actual installed `scripts/deploy-production.sh --print-plan` reports:

- `wepp1`: full mode; builds `weppcloud cap fcgiwrap preflight status weppcloudr`
  and recreates the full stack, including Redis, web/query services, scheduler
  and workers.
- `wepp2`: worker mode; builds `rq-worker weppcloudr` and recreates
  `rq-worker rq-worker-batch weppcloudr`.

There is **no existing task-file-only or batch-only deployment mode**.
`--targeted-web` deliberately excludes workers; `--skip-build` is rejected for
rebuilt services. A code-only copy into live containers, import overlay, extra
worker or patched capability registration is not a legitimate pilot deployment.

The requested participant-only rollout therefore needs an **opt-in
`--targeted-batch` extension to the canonical entry point**. There is no equivalent
existing switch. Preserve every default/full/worker/web/CAP behavior and make
targeted flags mutually exclusive. Support only existing full and worker presets
with an active `rq-worker-batch`; reject the dedicated fork/archive preset.

The mode's recreated/expected service allowlist is exactly `rq-worker-batch`.
Follow the final canonical source-only image derivation: use each host's exact
retained running local batch image as base, replace only the five approved Python
files and their stale derived bytecode, and retain the immutable overlay manifest.
Use no network, installer, vendor checkout or native rebuild; preserve all runtime
configuration and verify source/native/dependency fingerprints. Effective Compose
JSON still supplies the target service/runtime contract. Do not add a Compose
file, worker count, image registry or dependency. Updating
the shared local image tag does not authorize recreating other image consumers;
retain and compare their running image/container identities across the cutover.

Build before activation, preserve the owned global RQ fence and existing shared
default/batch active-job check, then warm-stop only `rq-worker-batch`. Never run
stack `down`. Activate with the entry point's scoped
`up -d --no-deps --force-recreate rq-worker-batch`. Skip unrelated static/theme
publication, CAP preparation, broad service health loops and pruning in this
new mode. Redis, default workers, web/query/scheduler and renderer containers
must not be recreated. The global dequeue fence remains temporarily global as
required by the existing contract; it is not the catalog-only pilot pause.
Resume only a fence owned by this deployment after batch runtime/native preflight
and genuine current-container worker registration checks succeed. Existing
external suspension, fence renewal/loss, stopped-worker Redis-query fallback,
failure and rollback ownership semantics remain fail-closed.

The entry point already supports `--skip-pull`. Stage only a reviewed reversible
whitelist patch against the exact clean production baseline, then use the new
canonical targeted mode with `--skip-pull --no-flush-rq-db`. Include the reviewed
deployment-mode changes and their exact helper dependencies, not unrelated local
script/Compose changes. Record baseline/file hashes, full dependency closure,
patch hash, effective plan, rollback bytes and reconciliation to the normal
source workflow. This preserves branch HEAD and avoids unrelated history, but
intentionally leaves a patched production worktree; that provenance must be
accepted explicitly in the checkpoint. Do not silently cherry-pick onto
production `master`, change its branch/upstream, or substitute a copy/restart flow.

Affected deployment authority/documentation: `docker/AGENTS.md` deployment
boundary, `docker/README.md` targeted deployment instructions, and
`docs/infrastructure/deployment-tuning-knowledgebase.md` shared RQ check/fence
behavior. No dedicated targeted-batch schema currently exists; the reviewed
canonical pilot contract/ADR must specify this opt-in deployment boundary and
link the operator instructions. Add a dedicated canonical deployment schema if
the parent separates this reusable mode from pilot-specific authority.
Implementation validation uses existing
`tests/scripts/test_deploy_production_plan.py`,
`tests/scripts/test_deploy_production_execution.py` and
`tests/scripts/test_compose_deploy_contract.py`. Add full/worker targeted plans,
unsupported/conflicting modes, exact build/recreate set, no dependency/Redis
recreation, drain/fence ordering, stopped-worker fallback, renewal loss and
unchanged default-mode execution tests. Shell harnesses do not replace final
production operational approval or real registration/image readback.

Deployment must satisfy the canonical drain/cutover fence, preserve Redis data,
and install the candidate on all existing eligible consumers. After normal
startup, verify all eight real registrations advertise identical configuration
and new capabilities with `enabled=false`. Only then register and run the pilot.
The reviewed fixtures must be reachable under the unchanged identities/mounts
on both hosts. No per-request configuration overlay can substitute for this.

## Required checkpoint and acceptance

Amend the canonical recovery/admission contract and ADR before implementation:
explicit disabled-mode pilot exception, global cap, ordinary-work priority,
operator authority, immutable quotas/window, drain behavior, loss recovery and
privacy. Review absent, active, paused, expired, draining, completed, failed and
lost/malformed manifest states. Ordinary disabled producers must remain unchanged.

Real Redis tests must cover concurrent refresh/inventory admission, quota races,
ordinary arrival, permit conservation through worker loss, stale release,
ambiguous commit, controller restart, pause/resume and deadline exhaustion.
Filesystem tests must cover outside/within-root symlink replacement, incarnation
change, READONLY, an unlisted nested scope and an ordinary non-pilot scope while
global enablement remains false. Missing-capability consumers must block pilot
admission without fake registrations. Actual pilot evidence must come from the
normal eight shared consumers, with ordinary queue wait, job-count/budget ledger,
all admitted artifacts and post-pause drain readback retained.
