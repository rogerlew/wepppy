# Bounded pilot contract decision

Status: awaiting two independent contract reviews; no pilot implementation yet.
Operator authorization: “execute the bounded pilot,” 2026-10-27 UTC. This accepts
the proposed seven-job bound, finite owned-scope pilot and necessary reviewed
participant isolation/deployment. General enablement remains excluded. The
preexisting legacy mount limitation remains outside this release.

Starting implementation revision: `f8f956c7a`. Prior uncommitted streaming-inventory
and HTTP remediation is governed by checkpoint `09ce55d1d`; its seven-file
`20261027_remediation_source_manifest.json` binds that preexisting implementation.
No pilot runtime delta precedes this checkpoint. Both production hosts were
read-only verified at clean tracked `813d912be1c8f6f13b6fc60cecebbef9259cd36e`.

## Applicable canonical contract and exact delta

- `docs/schemas/query-engine-catalog-refresh-contract.md`: queue-wide atomic cap,
  ordinary backlog pause, trusted operator recovery, authentic capabilities and
  immutable manifest-bound disabled-mode exception; owned-only inventory seeds,
  admitted-ID execution authority, original budgets/window and drain semantics.
- `docs/adrs/ADR-0104-query-catalog-refresh-operational-bounds.md`: cap seven,
  retry-inclusive budgets 25 refresh/two inventory, 1,800-second admission window,
  300-second ordinary-wait failure trigger; observation10s/ownedlease60s; cadence and existing budgets unchanged.
- `docs/schemas/rq-response-contract.md`: retain sanitized maintenance polling,
  no public pilot control API, operator-only pending admission classifications.
- `docs/schemas/query-catalog-pilot-deployment-contract.md`: opt-in canonical
  `--targeted-batch`, existing fence/drain checks, batch-only recreate and
  candidate-only patch/image-build/rollback provenance; original default modes unchanged.

Implementation scope: `wepppy/rq/query_catalog_rq.py`, inventory/admission/pilot
helpers, trusted pilot operator tool, focused RQ/real-Redis tests, queue catalog/
graph, `scripts/deploy-production.sh`, a manifest-validated source-only image helper
and their existing/new bounded plan/execution tests,
operator/developer docs and this active plan/tracker. Change worker registration
code only if capability advertisement cannot use its existing configuration
hook. No scientific model, output-column, auth-route, general producer mode,
queue topology, runtime identity, mount or secret changes.

Compatibility/regression plan: default disabled calls remain synchronous;
ordinary reconciliation stays disabled. Owned fixture metadata changes are
additive and isolated; no real project data/schema mutation is permitted.
Filesystem protocol stays one; new queue/pilot capability makes mixed workers
unavailable for maintenance while ordinary jobs retain behavior. Existing
Admin/Root maintenance cancellation and public response shapes are preserved.

## Rationale and alternatives

The eight-consumer pool and 18,514 writable scopes can accumulate distinct-scope
work despite per-tick limits. More component scans cannot bound queue growth.
An atomic cap plus ordinary-backlog pause contains a finite shared-batch trial.
Reject general enablement, private-queue substitution, new workers/queues,
registration spoofing and dynamic source bootstrap as acceptance shortcuts.

General async false plus explicit recorded pilot authority is necessary to avoid
releasing unrelated projects. Scope identity and cumulative budgets must survive
controller restart and guard every admission/retry/execution path. Full deployment
would recreate unrelated services; an opt-in target on the existing canonical
entry point is smaller and reviewable. It does not change deployment defaults.

## Valid-state and hostile-state matrix

| State | Required result / evidence |
| --- | --- |
| No pilot, global disabled | Existing producer behavior; scheduler disabled; no new public failure. |
| Valid empty/paused pilot | No work admitted; explicit start/resume within original bounds; no budget reset. |
| Valid populated active pilot | Shared queue, real consumers, correct artifacts and bounded accounting. |
| Expired/exhausted/paused after admission | No replacements; admitted work drains; receipts retained; partial cycle not complete. |
| Existing ordinary backlog | Latched pilot pause, only catalog admission affected, ordinary waits observed. |
| Legacy/mixed/dead worker | Maintenance admission unavailable; no permit released solely for disappearance. |
| Controller loss or stale lease | Pause new admission, preserve drain, explicit new operator ownership, retain observation gap and original budgets. |
| Missing/corrupt manifest/quota/reservation | Fail closed; explicit evidence-based operator recovery, never fresh budget. |
| Unlisted/changed/symlink scope or replayed job | Reject before initialization/receipt/publication; held-out project unchanged. |
| Redis/controller crash around enqueue | Atomic quota/permit/job commit; restart retains counters and authority. |
| Malformed queue classification | Conservative pause; no task-payload deserialization or implicit cleanup. |
| Canceled/failed/retried job | New IDs consume budget; preserved failure/receipt evidence; no silent success. |
| Unsupported deploy preset/destructive flag | Fail before source/service mutation; original modes unchanged. |
| Deployment/capability/readback failure | Owned fence/recovery semantics, candidate-only rollback; general mode disabled. |

Security impact: high (disabled-mode execution exception and shared-queue/host
boundaries). Dedicated independent security review plus independent correctness
review required before checkpoint commit and after implementation. Direct
unmocked Redis/filesystem tests and actual participant/job/artifact evidence are
required; fake registrations/private queues cannot substitute for the final pilot.

Correctness draft finding: existing worker containers have no repository bind
mount; host patch plus skip-build would leave old source active. Disposition:
canonical scoped deployment now requires a task-only candidate image build,
source/native/dependency readback before cutover and retained old-image rollback
reference. Security sign-off is reopened for this corrected activation boundary.
No runtime implementation preceded the finding or disposition.

Final activation refinement: ordinary baseline Dockerfiles use mutable vendor/base
references and uncached installers. The canonical opt-in target derives a
source-only image from each exact running local batch image; no network or
dependency/native rebuild. Approved application source closure is
`wepppy/rq/query_catalog_rq.py`, `_query_catalog_inventory.py`,
`_query_catalog_admission.py`, `_query_catalog_pilot.py` (all under `wepppy/rq/`),
and `tools/query_catalog_pilot.py`. Add only the canonical deployment/helper/test
files required to stage/validate that manifest and mode. Reopen review hashes for
this explicit mechanism before checkpoint commit. Runtime inputs/candidate
configuration parity and real shared-queue acceptance remain required.
