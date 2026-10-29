# DM-01 validation

Contract ancestor: `44746ff63`. Native release: `4d4c075421c4013cba99a0addc76482229e7f3f7`, pushed and verified equal to upstream. WEPPpy implementation revision is recorded in tracker at handoff. No production deployment.

## Checks

| Check | Result |
| --- | --- |
| Native `cargo test --locked -p wepp_interchange_rust` | 110 unit + 17 integration passed. Clean source export excludes unrelated dirty calendar/HBP changes. |
| UI/API/render/startup focused pytest | 292 passed, including real authorization/CSRF/readonly and locked Ron persistence, exact roles and Dev-only header controls. |
| Developer-mode state/native tests | 10 passed; malformed state, fresh concurrent-update preservation, lifecycle guard and actual prepared soil readback. |
| Facade/native anisotropy + archive review follow-up | 93 passed, including elevated facade forwarding and activation during real archive capture. |
| Fork/archive suites | 166 passed, 3 existing skips. |
| Failed-fork recovery follow-up | 3 passed for incoming true/false/missing mode; real destructive replacement, production rsync and Ron readback; queue admission is stubbed. |
| `wctl run-npm lint` | Passed. |
| `wctl run-npm test` | 1,019 tests passed; 59 project tests also passed after adding delegated-click coverage. |
| Controller bundle rebuild | Passed through wctl. |
| Stubtest Ron and WeppSoilUtil | Both passed. |
| `wctl check-test-stubs` | Passed. |
| Broad-exception changed-code enforcement | Passed; no added broad catches. |
| Code-quality observability | Completed, observe-only reports generated. |
| Docs lint / diff check | Passed for changed docs; spelling preview made no unrelated replacements. |
| Full Python suite | Running; final outcome below will distinguish regressions from unrelated baseline failures. |

Counts overlap across selections and must not be summed as unique tests.

## Actual runtime and artifact evidence

`validate_runtime.py` creates the isolated `/wc1/runs/dm/dm-anisotropy-validation` project from the earlier SA-01 fixture. It uses the actual Flask action and CSRF with a synthetic request principal to avoid changing any account roles. Dev activation succeeds; the same principal without Dev cannot activate. The real Wepp parser then accepts 101/11 without a Dev check. Saved Ron/Wepp are reloaded before preparation.

`runtime.json` retains completed default-pool prep and model jobs plus a completed fork-archive-pool fork. The new native module prepared 101/101/11 at 100/500/800 mm in both OFEs. Source SHA is unchanged. The actual WEPP 261026 hillslope runner returned success and produced fresh loss/water/soil/PASS/graph outputs. Input/output hashes, job ids, UID/GID/groups/umask and file mode are recorded. The live clone retained true mode and 101/11 settings.

`validate_browser.cjs` checks the actual public project page using Playwright: displayed saved values, absent maxima, developer indicator and no activation control for an ordinary viewer. `browser.json` records successful normal browse and download; soil and fresh native loss-report hashes equal the worker artifact hashes. `soil-options.png`, `prepared-p1.sol`, `fresh-H1.loss.dat` and `model-execution.log` are retained. This is one bounded MOFE hillslope simulation, not a claim of stability for all experimental values or a watershed-report rebuild.

## Reviews and resolved validation failures

Independent security review closed the accidental TTL-control exposure with regression coverage for both headers. Independent correctness review closed elevated facade-forwarding and real lifecycle-capture/recovery coverage gaps. Both reviews have no remaining blocking implementation findings.

Initial tests intentionally failed before JS implementation. Native-dependent tests failed explicitly against the old extension until the paired rebuild was installed. Test fixture adjustments supplied Ron policy to old facade fakes and used writable hydration for a stale-controller mutation test. The browser initially used an unreachable loopback address, then waited for a collapsed control to be visible; final checks use the canonical local-domain page and open its details before the screenshot. These failed attempts are not represented as successful checks.

Local web/API/default-worker services were restarted after idle-worker inspection to load paired source/native code. This is local development acceptance, not production rollout. Existing archive/fork recovery behavior and queue topology are unchanged.
