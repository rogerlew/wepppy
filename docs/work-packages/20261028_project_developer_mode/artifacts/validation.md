# DM-01 validation

Contract ancestor: `44746ff63`. Native release: `4d4c075421c4013cba99a0addc76482229e7f3f7`, pushed and verified equal to upstream. WEPPpy implementation revision: `9516fd7f3`. No production deployment.

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
| Broad Python regression coverage | 12,047 distinct passed / 298 distinct skipped across three segments after two reviewed test updates. One pre-existing Roads publication-provenance failure remains. |

Counts overlap across selections and must not be summed as unique tests.

## Actual runtime and artifact evidence

`validate_runtime.py` creates the isolated `/wc1/runs/dm/dm-anisotropy-validation` project from the earlier SA-01 fixture. It uses the actual Flask action and CSRF with a synthetic request principal to avoid changing any account roles. Dev activation succeeds; the same principal without Dev cannot activate. The real Wepp parser then accepts 101/11 without a Dev check. Saved Ron/Wepp are reloaded before preparation.

`runtime.json` retains completed default-pool prep and model jobs plus a completed fork-archive-pool fork. The new native module prepared 101/101/11 at 100/500/800 mm in both OFEs. Source SHA is unchanged. The actual WEPP 261026 hillslope runner returned success and produced fresh loss/water/soil/PASS/graph outputs. Input/output hashes, job ids, UID/GID/groups/umask and file mode are recorded. The live clone retained true mode and 101/11 settings.

`validate_browser.cjs` checks the actual public project page using Playwright: displayed saved values, absent maxima, developer indicator and no activation control for an ordinary viewer. `browser.json` records successful normal browse and download; soil and fresh native loss-report hashes equal the worker artifact hashes. `soil-options.png`, `prepared-p1.sol`, `fresh-H1.loss.dat` and `model-execution.log` are retained. This is one bounded MOFE hillslope simulation, not a claim of stability for all experimental values or a watershed-report rebuild.

## Reviews and resolved validation failures

Independent security review closed the accidental TTL-control exposure with regression coverage for both headers. Independent correctness review closed elevated facade-forwarding and real lifecycle-capture/recovery coverage gaps. Both reviews have no remaining blocking implementation findings.

Initial tests intentionally failed before JS implementation. Native-dependent tests failed explicitly against the old extension until the paired rebuild was installed. Test fixture adjustments supplied Ron policy to old facade fakes and used writable hydration for a stale-controller mutation test. The browser initially used an unreachable loopback address, then waited for a collapsed control to be visible; final checks use the canonical local-domain page and open its details before the screenshot. These failed attempts are not represented as successful checks.

Local web/API/default-worker services were restarted after idle-worker inspection to load paired source/native code. This is local development acceptance, not production rollout. Existing archive/fork recovery behavior and queue topology are unchanged.

## Existing broad-gate limitation

The isolated Roads publication check fails at `tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`: its reviewed stale-evidence receipt expects an older `roads.py` hash. `roads-provenance-baseline.json` proves that the current Roads source is byte-identical to starting revision `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`. This task does not alter that source or rewrite historical publication evidence. All remaining coverage completed as recorded below.

Broad-run fixture correction: `tests/nodb/test_ron_map.py` used a `SimpleNamespace` without the new `developer_mode` public property. Added `developer_mode=False` to that stand-in; real Ron already implements missing-persisted-state behavior. No production fallback was added. Continuation uses pytest's argument-file support with the 67 remaining file/directory paths, resumes at `test_ron_map.py`, and deselects only the independently reproduced Roads provenance failure. An initial 323-file ignore-list attempt was interrupted during slow collection before test execution; explicit remaining paths avoid that collection overhead. Earlier review-only test additions were validated separately.

The second segment passed 5,048 tests with 245 skipped before an old PowerUser onboarding test expected the Dev report-panel trigger to remain hidden. Updated that expectation to DM-01 and added an assertion that Dev sees activation but not clear-locks. Independent security review confirmed conformance. `remaining-pytest-args.txt` and `final-pytest-args.txt` retain the continuation selections; final segment starts at the corrected presentation file, so its earlier 17 passing cases overlap the second segment.

## Final broad results

`wctl run-pytest tests --maxfail=1`: 5,655 passed / 54 skipped before the corrected Ron stand-in. First continuation: 5,048 passed / 245 skipped / 1 deselected before the corrected Dev visibility expectation. Final continuation: 1,361 passed. Removing 17 repeated passing presentation cases and one repeated collection skip gives **12,047 distinct passes and 298 distinct skips**. The independently reproduced Roads provenance assertion is the sole remaining failure. These are segmented coverage results, not an uninterrupted green full run. No production changes were required by the broad gate; both test-only updates received independent reviewer confirmation.

Contract and implementation commits are `44746ff63` and `9516fd7f3`; the closeout commit contains the two existing-test conformance updates and final evidence. Production rollout remains outside scope.
