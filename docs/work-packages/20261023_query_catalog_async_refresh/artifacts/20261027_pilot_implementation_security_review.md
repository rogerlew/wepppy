# Bounded pilot implementation security review

Disposition: **PASS for the final bounded-pilot implementation; no unresolved
medium/high finding.** This is an independent
implementation review following the contract checkpoint `5c1edb22a`; a contract
PASS is not an implementation or production acceptance PASS. Reviewer:
`inventory_security_review`. No implementation or production changes by reviewer.

## Findings

### PILOT-SEC-04 — Medium, closed: cancellation released a live execution permit

Confirmed in `_query_catalog_admission.prepare` and
`_query_catalog_pilot.pilot_status`: every `canceled` RQ status is treated as
terminal even when its admitted execution claim is already in use. Installed
RQ `Job.cancel()` permits canceling a started job and removes registry entries
without stopping the executing process. Thus raw status alone cannot prove this
particular execution has exited.

The independent disposable-Redis reproduction
`pilot-security-cancellation-repro.py` holds an actual RQ execution process inside
`refresh_catalog`, cancels that claimed job through `Job.cancel()`, and attempts
another approved admission. `pilot-security-cancellation-before.log` records:
the process is still running; reported outstanding is six while actual
outstanding is seven (one executing and six queued); an eighth outstanding job
is admitted. This violates the cap and can make drain accounting premature.
No production queue/project was used.

Closure: final code atomically retains a claimed canceled job as
occupied/uncertain until its worker records `execution_exited_at` after catalog
work returns. The same classification drives admission, observation and
drain/status. Both worker boundaries enter their exit-recording `finally` only
after a successful execution claim, covering post-claim early returns and
exceptions. Rejected replay cannot falsely mark the original execution exited.
Unclaimed cancellation may release its permit under the watched claim/status
transaction. Installed RQ's normal finished/failed/stopped semantics and prior
killed-worker/timeout recovery remain intact; missing claimed cancellation exit
proof requires explicit recovery. The canonical catalog contract and operator
guide now distinguish these cases.

Independent final regression execution proves seven outstanding/one uncertain
while cancellation remains live, denies an eighth admission, preserves replay
denial, and verifies the actual catalog/zero pending receipts and exit record
after releasing the worker. The original independent reproduction also now
passes; see `pilot-security-cancellation-after.log`.

## Reviewed boundaries

- One global `batch` ledger covers all configurations/pilots; RQ enqueue,
  reservation, counter debit and immutable job binding share one Redis
  transaction. Queue/worker/pilot/controller inputs and execution claims are
  watched. Unknown or duplicate raw queue entries do not bypass ordinary work.
- The disabled-mode exception requires an explicit registered pilot, exact
  approved scope identity, owned controller token and fresh observation.
  Ordinary producers/scheduler remain disabled. Inventory uses only approved
  seeds and cannot recurse into unlisted child scopes or ordinary dirty indexes.
- Eight compatible worker registrations, seven outstanding permits, original
  1,800-second window and cumulative 25 refresh/two inventory job budgets are
  checked without resetting across controller restart. Same-ID execution claims
  are single-use. Observation failure pauses admission; admitted work can drain.
- Operator artifacts remain in a private owned evidence directory. Raw
  publication, scope/incarnation/inode binding, source metadata and receipt
  acknowledgment are checked before consumer queries can repair output.
- Source activation accepts exactly five hashed Python paths and an exact local
  running image. Trusted generated recipes reject redirects/ONBUILD/overlapping
  volumes, disable network and pulls, preserve runtime configuration,
  dependencies/native binaries and source ownership/mode, and retain rollback
  evidence before service-tag promotion. The canonical target changes only batch
  lifecycle, retains the global fence/active-job gate, and supports exact-image
  rollback with deployment tooling restored last.

No additional confirmed security finding in the reviewed scope. Redis/Docker
operator authority remains trusted; this change adds no public pilot endpoint,
new pool, new queue, secret flow, arbitrary job bootstrap or mount change.

## Independent verification

Executed against the owner's marked disposable Redis Unix socket, sequentially
with other Redis tests:

```text
wctl exec -e BATCH_BOUNDARY_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/pilot-test.sock weppcloud /opt/venv/bin/python -m pytest tests/rq/test_query_catalog_pilot.py tests/rq/test_query_catalog_inventory.py tests/rq/test_query_catalog_rq.py -q
```

Before the cancellation finding: **71 passed in 31.83s**, retained in
`pilot-security-rq-tests.log`. These include concurrency, cancellation-before-
claim, strict consumers, retained budgets, actual worker death/restart and
filesystem containment. The added independent reproduction then failed for the
confirmed cancellation-after-claim gap; passing existing tests did not close it.
After closure, the same command with `tests/rq/test_query_catalog_disclosure.py`
added passed **86 tests in 37.06s** (72 RQ/inventory/pilot and 14 disclosure),
retained in `pilot-security-rq-final-tests.log`. Existing deprecation warnings
and multiprocessing fork warnings were emitted; no tests failed or skipped.

```text
wctl run-pytest tests/tools/test_query_catalog_pilot_cli.py tests/scripts/test_build_source_overlay.py tests/scripts/test_deploy_production_plan.py tests/scripts/test_deploy_production_execution.py -q
```

**80 passed in 41.82s**, retained in
`pilot-security-operator-deploy-tests.log`. Independently inspected the exact
deployment delta against production baseline
`813d912be1c8f6f13b6fc60cecebbef9259cd36e` and retained real local Docker build
evidence, including `20261027_source_image_production_user_build.json`. The
UID1002/GID130 fixture proves existing/new source metadata and parent directory
metadata parity on that local base. Independently checked the later
`20261027_source_image_final_build.json`: its five source hashes equal the final
post-cancellation workspace, 306 distributions/nine native binaries and runtime
configuration match its base, and source modes/owners are `0664`/1002/130.
The exact local candidate is
`sha256:0a4a8019bf17ee15b850e64902e21b25a0184239bbb12009a779df452d441fe2`;
the evidence artifact digest is
`fe40aed5eaca5fe54a12e40f64eaaf5b0f0827abc5c83cda70f49bc52f116053`.
This is still a local production-style fixture, not either production host's
final image/payload acceptance.

## Reviewed source identity and remaining gates

The refreshed production candidate patch SHA-256 is
`08cf69965d21ac00465874e7387fb1cae857a0b81025b224a24b09894aa8d161`.
Independently recomputed the patch digest and all seven candidate file digests
against `20261027_pilot_production_candidate_manifest.json`; all match. The six
non-deployment-script files also match the current workspace. The deployment
script is intentionally the bounded backport against production `813d912be`.

Final application source:

| File | SHA-256 |
| --- | --- |
| `wepppy/rq/query_catalog_rq.py` | `6de79801a17428df2caccd8fb7a449dfa1bf960b6b6bbd7dfa2fa397a4222ce9` |
| `wepppy/rq/_query_catalog_inventory.py` | `f023fc55743141705aa964baf9ded6a4d031319c8b247f90c95583daa31de1b4` |
| `wepppy/rq/_query_catalog_admission.py` | `ccf94032d46ec7038017a4f219b13e1d288b59753412ea3b9fdcf60abfecaf80` |
| `wepppy/rq/_query_catalog_pilot.py` | `c85de18002b08dd5fc9d69f4bb597df0a03bb2b18f2e333d838f401881fbb0c5` |
| `tools/query_catalog_pilot.py` | `1f22c196845ff394747b6286593a7f69329430b2cea507d6550ccb9b084ea1c5` |

Deployment tooling reviewed:

| File | SHA-256 |
| --- | --- |
| Workspace `scripts/deploy-production.sh` | `7a9c20caa07e9770d62d462260be32acec589cdf5eb85e6ae82da7f5c2c4182a` |
| Production-backport `scripts/deploy-production.sh` | `74866cfb081699157134c2c7f450019adaeeeff96d6a63c95bf74dde0f4fbf92` |
| `scripts/build_source_overlay.py` | `b5493432a3c3cf901a0cfe0d7d4647f72658c831bb7c49afb7d9dc4553d5836f` |

This review does not approve general asynchronous enablement, fleet capacity,
production deployment, untouched-service parity or actual shared-queue pilot
acceptance. Each host's exact image/source/native/dependency readback and all
eight genuine registrations remain required. The active production scientific
job remains subject to the canonical deployment gate; this review authorizes no
bypass. Preexisting read-only mount routing remains expressly out of scope.
