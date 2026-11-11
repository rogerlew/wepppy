# Validation receipt — WebSocket authorization

Ratified ancestor: `6a06ad49a`. Implementation revision will be recorded at
forest cutover. All commands run on forest through the installed dev `wctl`.

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
| `wctl run-pytest tests --maxfail=1` | Running; no full-suite claim yet |
| Correctness / QA / security source reviews | Approved; environment gate pending |

## Discovered validation issues

- First full pytest attempt: 2,012 passed, 37 skipped, one failure in 603.67
  seconds. The new endpoint made OpenAPI 165,024 bytes against the 165,000-byte
  limit. Shortened only the new route metadata; focused OpenAPI suite now
  passes (13 tests), and the full suite is rerunning with the unchanged budget.
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

## Final consumer/tooling checks

The second full pytest attempt was explicitly interrupted at 387 passed / 28
skipped (103 seconds) after a focused diagnostics render test exposed a missing
Flask `request` global in its isolated Jinja harness. Corrected the harness;
all 57 diagnostics/run-sync/fork regressions pass (14.80 seconds). The third
unsegmented full attempt is running.

Operator Go smoke compiles/tests through the Go builder. Shell and k6 syntax
checks pass; k6 is not installed on forest, so no k6 runtime/load claim is made.
The generated nightly workflow passes `build_forest_workflows.py --check`;
actual GitHub Actions execution is not claimed. Independent reviewers approved
the tooling auth changes. The inherited k6 connection-age metric was renamed
and its invalid latency threshold removed; handshake and message-count gates
remain enforced. Live operator smoke will follow forest cutover.
