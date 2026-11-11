# Validation receipt — WebSocket authorization

Ratified ancestor: `6a06ad49a`. Full regression revision: `fadc8847b`; browser revision: `bae13ff84`. All commands run on forest through the installed dev `wctl`.

| Check | Result |
| --- | --- |
| Focused Python routes, shared redaction, Python-driven controllers | 45 passed, 1.43 seconds |
| Shared `services/streamauth` `go test ./...` via status-build | Pass, 0.153 seconds |
| `wctl run-status-tests -tags=integration ./...` | Pass; server 1.690 seconds |
| `wctl run-preflight-tests -tags=integration ./...` | Pass; server 1.930 seconds |
| `wctl run-npm lint` | Pass |
| `wctl run-npm test` | 126 suites / 1,076 tests passed, 7.988 seconds |
| `wctl exec weppcloud python wepppy/weppcloud/controllers_js/build_controllers_js.py` | Pass |
| `wctl check-test-stubs` | Pass |
| Scoped canonical/package docs lint | Pass |
| `wctl run-pytest tests --maxfail=1` | 13,568 passed / 435 skipped, 3,785.08 seconds; exit 0, revision `fadc8847b` |
| Correctness / QA / security source reviews | Code approved; final evidence review recorded in dedicated review artifacts |

## Discovered validation issues

- First full pytest attempt: 2,012 passed, 37 skipped, one failure in 603.67
  seconds. The new endpoint made OpenAPI 165,024 bytes against the 165,000-byte
  limit. Shortened only the new route metadata; focused OpenAPI suite now
  passed (13 tests), and the full suite was rerun with the unchanged budget.
- Host `python3` lacks Jinja2. Used the canonical web container for the builder;
  the local `.venv` also provides Jinja2 for the deploy entry point.
- Initial Go redaction test found newline immediately after `->` escaped the
  setter regex. Fixed and covered. Initial Jest lint found a missing Node global
  declaration in the new preflight test; fixed.
- Broad-exception enforcement against `origin/master` fails on a pre-existing
  increase in `wepppy/weppcloud/bootstrap/pre_receive.py`. Against the ratified
  task baseline, changed production files introduce no broad catch (pass).
- Code-quality observability is observe-only and completed against `6a06ad49a`.
  The shared HTTP helper grew to own one transport lifecycle across all clients;
  that scope prevents independent retry/cache implementations in each consumer.

Raw test output remains local under `/tmp/stream-auth-*.log`. Browser evidence
must contain only selected non-secret claims and assertions, never credentials.

The third full pytest attempt stopped after 9,803 passed and 429 skipped
(3,491.79 seconds) because the new browser-only route was missing from the
endpoint inventory. Promoted the unchanged existing table from its closed
package to `docs/schemas/rq-engine-endpoint-inventory.md`, added the stream-token
row, and switched the three readers, canonical pointers and generated CI path
filters. Both inventory/checklist guards pass. A focused pass over the remaining
test directories precedes another unsegmented full run; neither partial result
is a full-suite pass. This exposed a maintenance gap: route onboarding should
name the inventory guard before the expensive full suite.

QA tightened the forest harness before deployment: wait for Redis subscribers,
require a fresh preflight frame after renewal, log out explicitly, and clear the
disposable run cache before deletion. Cleanup supports already-absent runs; NFS partial deletion required the scoped recovery recorded below.

Remaining-directory precheck found one additional integration omission after
3,704 passes: diagnostics needed the standard deferred stale-controller check
immediately after its new controller bundle. Added that companion script;
all 2,370 web and OpenAPI checks pass (205.58 seconds), and QA approved the fix.
The fourth unsegmented full suite started at revision `fadc8847b`; forest cutover
was held until it passed. No partial run is counted as full-suite proof.
## Final consumer/tooling checks

The second full pytest attempt was explicitly interrupted at 387 passed / 28
skipped (103 seconds) after a focused diagnostics render test exposed a missing
Flask `request` global in its isolated Jinja harness. Corrected the harness;
all 57 diagnostics/run-sync/fork regressions pass (14.80 seconds). The third
unsegmented full attempt later exposed the inventory omission recorded above.

Operator Go smoke compiles/tests through the Go builder. Shell and k6 syntax
checks pass; k6 is not installed on forest, so no k6 runtime/load claim is made.
The generated nightly workflow passes `build_forest_workflows.py --check`;
actual GitHub Actions execution is not claimed. Independent reviewers approved
the tooling auth changes. The inherited k6 connection-age metric was renamed
and its invalid latency threshold removed; handshake and message-count gates
remain enforced. Live operator smoke passed after forest cutover (two clients, ten frames).

## Production-identity status canary

A disposable `wctl run --rm --no-deps --name stream-auth-status-canary status`
container used the built image
`sha256:dd324d2f0b498f0365d4c95e1137927a836078383a6199cd67af46ac08b2eed1`,
UID/GID `1000:993`, configured signing/Redis secret mounts and exact forest
Origin. The trusted operator smoke ran against its internal Docker address.
Two clients received five messages each (10 total), with the fixed negotiated
protocol. No live service was recreated for this canary.

The first two-client attempt exposed an inherited smoke race: HTTP 101 preceded
Redis subscription readiness, so one client's initial publish was lost. The
fixture now waits for all subscriptions and releases publishers together;
retest passed. Both attempted fixtures left zero session markers. Canary log
scan found no bearer/JWT credential pattern; the disposable container was
stopped/removed. This proves service transport under actual mounts/identity,
not browser authorization or deployed Caddy acceptance.

Preflight startup canary also passed with UID/GID `1000:993` and image
`sha256:db6e878e4c9610150dadc0b946681376bfc8d51896492ff25d818842d3cd42a1`.
Its internal `/health` returned `OK`; the disposable container was removed.
This is startup/readability evidence only; real preflight frames remain the
browser gate. Workflow bootstrap regressions: 2 passed (8.94 seconds).

## M4 completion

The fourth exact `wctl run-pytest tests --maxfail=1` run passed at `fadc8847b`: 13,568 passed, 435 skipped, 6,029 warnings in 3,785.08 seconds. All code review findings are closed. Forest deployment and browser acceptance are the remaining gates.

## Forest acceptance and cleanup

`20261111_forest_acceptance.json` joins the before/after deployment, original
browser and supplemental cleanup receipts. Chromium 141.0.7390.37 observed both
real frontend handshakes, 300-second claims, fixed negotiated protocols, initial
messages, fresh credentials and new messages after scheduled renewal, status
markers rendered in the page, both missing-token/cross-run denials, anonymous
private mint denial, standalone archive authorization and logout. In-memory
credential comparisons found none in URLs, storage, selected protocols, browser
console, five service logs or retained artifacts.

All browser assertions passed. The original harness exited 1 during cleanup:
canonical deletion removed DB records but deferred NFS `.nfs` files held by web
and RQ log handlers. The initial ownership-error diagnosis on retry was a
consequence of partial deletion, not an authorization defect. The fixed login
identity assumption was nevertheless replaced with the configured identity.
Restarting only web/RQ released the handles. After verifying that only TTL
metadata remained, canonical deletion removed both exact disposable directories;
DB records and stream/WD/lock markers were verified removed. The original failed
aggregate receipt is retained unchanged; the supplemental receipt establishes
completed cleanup. No production services, worker queues or shared Redis data
were reset.

The canonical deployment guard rejected `--skip-build` before web mutation;
reran with its required candidate build. Health, image identity and restart
stability gates passed. The new image additionally passed 34 focused Python
checks (0.94 seconds). Live operator smoke delivered all ten frames and left
zero fixture markers. Final login and all service health endpoints return 200.

Operational follow-up: the browser harness currently requires this documented
manual cleanup recovery on NFS when canonical deletion defers open log handles;
its nonzero result must never be relabeled as an original all-green run.
