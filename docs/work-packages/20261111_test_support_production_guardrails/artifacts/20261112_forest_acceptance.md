# Forest NFS and browser acceptance — 2026-11-12 UTC

User authorization: bounded NFS repair, live browser acceptance on forest, and
F6 through M4. Production rollout remains excluded.

Contract ancestor `11a805e09`; implementation `b0cd6d4b7`. Independent correctness
and security approved both checkpoint and implementation. Correctness found
permissive lexists readback; lstat with only FileNotFoundError proving absence
closed that finding before activation. EACCES/ESTALE regressions pass.

## Runtime activation

Host forest; installed development wctl preset. Queues default/batch/fork-archive
had zero queued/started jobs and 11 workers were idle. No tests were active at
activation. `wctl rq-info --detailed` ran its existing registration refresh but
then failed because installed RQ has no --detailed option; direct read-only RQ
API checks supplied the actual queue/worker evidence.

Executed `wctl up -d --no-deps --no-build --force-recreate weppcloud rq-engine`.
Both retained image
`sha256:659eb59a98ce2e69a74cd36538b9e392c8e33d66de3c8ee5303e02bd243d01a0`
and UID/GID 1000:993. Only the intended development profile changed in their
rendered environment. Readback confirms development/true. No database, worker,
Caddy, query, browse, download, or D-Tale service was recreated. Those other
Flask consumers still need their explicit profile at their next activation;
their older images/unrelated environment deltas were deliberately preserved.

## Actual NFS boundary

An actual Ron constructor and two independent processes loading the same Ron
remained alive while their queues were drained and a separate process removed
the disposable run. Directory absence passed; late records left listeners alive
and did not recreate the directory. All fixtures were removed.

500-record queued write/drain and exact content readback: FileHandler 0.02015s;
RunFileHandler 0.51923s, roughly 1 ms additional per record. This measured NFS
metadata cost is retained; no throughput improvement is claimed. Active writers
are not globally synchronized with deletion and can cause explicit failure.

## Live browser and authorization

Invoked the actual wctl Typer command with its normal Compose environment:

    wctl run-playwright --base-url https://forest.tail305ec9.ts.net/weppcloud --config disturbed9002_wbt --grep 'runs0 page load' --workers 1 --playwright-args='--trace on --reporter=list,html --output=/workdir/wepppy/out/f7-nfs-20261112/browser-results'

An observation wrapper called the real mint function, retaining its return only
in memory for exact-token scans. No token replacement, signing bypass, mocked
backend, or browser request interception was used. The latest run executed one
test, passed in 13.0s, loaded all core controls without console errors, and removed
`abortive-turn-on`; trace-bound lstat raised FileNotFoundError. Earlier runs
also passed and removed `devilish-rifampin` and `immutable-quince`.

Live missing/bad bearer create requests returned 401. Missing/bad bearer delete
requests returned 401 and preserved the actual fixture. Authorized delete
returned 200 and lstat proved absence for `capricious-kabob`. Local route
regressions additionally prove denied create has no filesystem side effects.

Exact token absent from generated run files, captured command output, web/
rq-engine/Caddy logs, HTML report (including embedded ZIP), and trace ZIP contents:
147 scanned artifact/log items, zero matches. Private observation scripts and
sanitized receipts are under `out/f7-nfs-20261112/`; no token was retained.

## Regression and remaining gates

33 route/RQ focused tests passed. 43 NoDb/logging/F5 tests passed, two skipped
(the opt-in isolated Redis boundary). Final readback/helper selection passed 25.
Full `wctl run-pytest tests --maxfail=1` failed after 13,528 passes and 437 skips
at the run-catalog readonly notification-latency assertion (244.22ms catalog p95
versus 0.65ms baseline; allowed delta 50ms), in 4,280.28s. Docker image export
was concurrent; a quiet focused reproduction remains required. The threshold
is unchanged. This failed dev-runtime receipt is not F6 final-candidate M4 or
F7 combined M6.

F7 runtime cleanup/browser blockers are resolved for the exercised workflow.
F6 exact-image gates, final combined revision/gates, and final deployment plan
remain open. No production readiness or deployment claim follows this receipt.

Broad-exception enforcement passes after refreshing seven exact source-line
references for unchanged AST-identical existing handlers in the allowlist. No
new broad production catch was introduced. Root cause of the initial checker
failure was line drift from imports/handler cleanup, not added broad handling.

## QA evidence correction

QA found that the observation script initially ignored the log collection exit
status. Repeated observation now requires exit 0 for each service and scans both
streams. Web: 2,646 stdout bytes/93 stderr; rq-engine: 394/93; Caddy: 0/89.
Caddy emitted no runtime stdout in this bounded window; no file access-log sink
is configured in the development Caddyfile. 147 items scanned, zero token matches.
The browser test passed in 13.0s and removed `abortive-turn-on`.

The first run-ID extractor did not recognize three-part slugs. The original
receipt remains preserved, with supplemental trace-bound lstat readback in
`out/f7-nfs-20261112/browser-path-readback.json`; trace SHA-256 is
`7d2197cf3b4f38024abfd3db9546b98f3ea827fc8419b0817ff5424566f7950d`.
The observer now accepts multi-part slugs and rejects an empty run-ID set.
QA independently rechecked the trace hash/path absence and closed the Medium
log-evidence finding. M5 has no open Medium/High review findings.
