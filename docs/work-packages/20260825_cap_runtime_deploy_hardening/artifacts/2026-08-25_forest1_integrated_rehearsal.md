# Forest1 integrated rehearsal evidence

## Result

The automated Forest1 release gate passed at revision `e11985f02`. Two exact
no-argument full deployments completed, the targeted modes changed only their
selected services, the live CAP browser gate completed, and an RQ-backed DEVAL
render published its HTML artifact. Production `wepp.cloud` was not changed by
this rehearsal.

## Deployment sequence

- Host: `forest1`; public origin: `https://wc-prod.bearhive.duckdns.org`.
- The host `acl` prerequisite was installed. The canonical CAP secret remained
  owner-readable, named UID `10001` readable, and group/other unreadable.
- An initial candidate run exposed that embedded single quotes in the Python
  `-c` payload were stripped by the real `wctl` command transport, producing
  invalid `redis.call(get, ...)` Lua. Redis rejected acquisition before RQ was
  suspended or services were recreated. Post-state was `suspended=0` with no
  deployment fence.
- Revision `e11985f02` replaced shell-sensitive Lua literals with Lua
  long-bracket strings and added focused regression assertions. The focused
  deployment-execution suite passed 27 tests before the rerun.
- Two subsequent exact invocations of `./scripts/deploy-production.sh` exited
  zero. Each passed CAP and WEPPcloudR candidate contracts, atomically acquired
  and renewed the global RQ fence, warm-stopped workers, recreated the full
  stack, verified candidate image identity and stable container state,
  re-established both workers, and atomically resumed dequeue.
- Final RQ state was `suspended=0` with no deployment fence. Public WEPPcloud,
  rq-engine, and CAP health endpoints returned HTTP 200. CAP ran as UID
  `10001` and passed challenge/redeem/siteverify.

## Targeted-mode isolation

- `--targeted-cap` exited zero and changed only `docker-cap-1`; every other
  container ID remained unchanged.
- `--targeted-web` exited zero and changed only `weppcloud` and `rq-engine`;
  CAP, WEPPcloudR, Redis, and both workers retained their container IDs.
- The targeted-web no-cache build spent about four minutes in the existing
  shallow `weppcloud-wbt` Git clone. It completed without cutover exposure,
  but the unbounded network clone remains operator-latency follow-up work.

## Failure and recovery evidence

- The production CAP contract exercised fresh, legacy, rotated-secret,
  unreadable-secret, unwritable-ledger, malformed-ledger, symlink, directory,
  special-file, and unexpected-entry states on disposable resources during
  every CAP/full deploy. Hostile states failed closed and cleanup completed.
- A disposable derived WEPPcloudR image with
  `/srv/weppcloudr/render-compose-request.R` removed was rejected by
  `docker/validate-weppcloudr-runtime-contract.sh` with exit status 1. The
  disposable tag was independently confirmed absent after cleanup.
- At exact revision `e11985f02`, a contained targeted-CAP failure injection
  stopped only the newly recreated candidate container before acceptance. The
  deployment returned 1 without a success footer, restored the known-good CAP
  rescue image, and re-passed internal/public health plus the functional
  canary. Every non-selected container ID remained unchanged; RQ remained
  `suspended=0` with no fence. A subsequent clean `--targeted-cap` invocation
  exited zero and restored the candidate image, proving idempotent recovery.
- An earlier full candidate activation independently exercised the full-mode
  rescue path after an RQ heartbeat failure during service recreation. It
  restored controllers and CAP, re-passed the functional canary, resumed RQ,
  and returned nonzero without a success footer.

## Browser and RQ canary

- Headless Chromium loaded the public run through the real CAP gate without
  credentials or browser-data remediation, then requested a no-cache DEVAL
  report for `soft-boiled-copying/disturbed9002_wbt`.
- RQ job `d872b1f2-cff9-4658-8132-14ebe1bf11a2` reached `finished`.
- The renderer published
  `/wc1/runs/so/soft-boiled-copying/export/WEPPcloudR/deval_soft-boiled-copying.htm`
  at 12,155,360 bytes. Its run-scoped stdout/stderr receipts recorded 93 render
  stages, cache bypass, and `Render succeeded`; no missing-entrypoint signature
  occurred.

## Manual UX gate

Safari CAPTCHA, local login, OAuth login, retention of an already-authenticated
pre-deploy browser session, and multi-tab logout require operator-controlled
browsers/accounts. Earlier rehearsal checks passed these flows, but they must
be re-confirmed against this final revision before production activation. No
test or recovery step requires logout, cookie clearing, or site-data clearing.

## Non-blocking observation

Recent logs contained no CAP-secret/ledger `EACCES` or missing-renderer
signature. They did contain the pre-existing profile-coverage warning for
`/workdir/wepppy-test-engine-data/coverage`; this is unrelated to CAP or DEVAL
and should be tracked separately.
