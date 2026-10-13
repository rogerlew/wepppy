# CBEXEC-01 validation

## Candidate and scope

Implementation: WEPPpy `3c114719b`; native default-branch remint:
`917265bb5de62d1e20f2f5aada434a622f916398` on
`wepp_260430_negmeltfix_comparator`. Contract checkpoint: `b4c950ced`.
The unrelated main native checkout remains untouched. No production deployment
or automatic changes to existing projects/defaults occurred.

Four sidecars were vendored unchanged from the native release directory.
`sidecar-remint.json` records original source commits, build times, executable
hashes and metadata hashes. Only the two declared feature members changed.
No Fortran rebuild or binary rebuild/smoke cycle was required for this
metadata-only remint; actual native execution is separately demonstrated below.

## Gates

| Gate | Result |
| --- | --- |
| Native complete suite before final source-repository identity assertion | 171 passed, 2 warnings; `/tmp/cbexec-forest-tests.log` |
| Native final refresh generator regression | 9 passed; `/tmp/cbexec-native-final.log` |
| Actual native soil/OFE matrix | 30 successful two-year hillslope executions, both releases, five formats, 1/2/32 OFEs; `native-input-validation.json` |
| Runner final tests including restored-mtime cache regression | 59 passed; `/tmp/cbexec-runner-final.log` |
| Final policy/schema/registry | 149 passed; `/tmp/cbexec-final-policy-schema.log` |
| Explicit-v1 persisted config, metadata-only revision change, rendered controls | 209 passed; `/tmp/cbexec-final-targeted.log` |
| Earlier API/parser/capability sweep | 344 passed, one test-only wrong dataclass attribute failed; corrected assertion passed in both final scoped gates |
| Frontend | 118 suites, 972 tests passed; `/tmp/cbexec-npm-test.log` |
| Frontend lint | Existing unrelated `climate.test.js:300` conditional-expect error; changed controller/tests have no reported lint error |
| Schema stubtest | Passed after synchronizing the preexisting missing upload selection member and new feature members; `/tmp/cbexec-stubtest2.log` |
| Stub completeness | Passed; `/tmp/cbexec-stubs.log` |
| Broad exceptions | No additional broad handlers; changed-file gate passed |
| Full Python sanity | Running; `/tmp/cbexec-full-pytest.log` |

Native refresh tests failed before implementation, then passed. A real-file
regression also proved the runner hash cache accepted stale sidecar hashes after
same-size in-place replacement with restored mtime. Adding ctime to its existing
cache key closes that failure; all runner tests pass. No new cache or dependency
was introduced.

## Persistence and user-facing acceptance

`tests/nodb/test_wepp_binary_policy.py` constructs a real older Builder config
while 261010 is absent from provider discovery, restores the current provider,
and runs the real parser, locks and detached reload. It verifies selection of
261010 without config/manifest changes; invalid paths, unknown IDs, unsupported
MOFE releases and scalar blank fail without NoDb changes. It covers explicit-v1
saved configs, unchanged legacy upload state, empty/absent optional declarations,
coarse geometry restrictions, zero-MOFE graph structure parity and invalid
TOPAZ/MOFE tuples.

The browser smoke uses the existing dev-agent account without role changes.
`browser-validation.json` proves actual MOFE creation with261010, upload-mode
validation, current run-page choices, live schema enums and full geometry tuples,
separate executable freshness identity, hostile HTTP400 and unchanged reload.
The creation endpoint returned201; no creation request was intercepted.

`validate_selected_execution.py` applies the production grouped-payload handler
to the browser-created disposable project, saves803 then261010 and reloads the
choice. Config and manifest hashes remain unchanged. It prepares real two-OFE
inputs and submits the existing `run_hillslope` function to Forest's default RQ
worker using the saved executable. `selected-execution-validation.json` records
terminal success, parsed OFE count, a fresh finite loss file, actual stderr
binary identity and output UID1000/GID993/mode0644. This is a bounded native
hillslope execution, not a complete watershed simulation or a scientific
stability guarantee.

`browser-artifact-readback.json` proves normal authenticated downloads of the
prepared soil and fresh loss output match those hashes; downloaded stderr
contains the expected binary identity. `archive-restore-validation.json` proves
canonical archive and restore jobs, downloaded ZIP parity, preserved selected
executable and exact restored config/manifest/soil/output hashes. No ad hoc
project cloning or restoration was used.

## Reproduction and limits

Use the normal `wctl run-pytest`, `wctl run-npm test -- --runInBand`, lint and
stubtest commands. The opt-in browser smoke is
`wepppy/weppcloud/static-src/tests/smoke/wepp-executable-capabilities.spec.js`.
Set `SMOKE_WEPP_CAPABILITIES=true` for creation, then run the retained selected
execution driver and verifier inside the web container. The driver intentionally
binds to the recorded disposable run and refuses to overwrite existing inputs;
for a fresh reproduction, explicitly select the newly created disposable run.
Use `SMOKE_WEPP_CAPABILITIES_READBACK=true` and
`SMOKE_WEPP_CAPABILITIES_ARCHIVE=true` for the separate readback/archive stages.
No credentials are retained in package evidence.

The native matrix uses committed fixture resources from WEPPpy base
`cf2ad6d7874b25377f529550b41cd46fc1f1e74f`; its generator and source hashes are
retained. Rebuild the disposable matrix before the selected-execution driver
when its temporary fixture directory is unavailable. Historical release
provenance and PASS contracts are unchanged. Matching watershed/hillslope
reruns remain required when users change releases; the feature does not make
old mixed-release intermediate files compatible.
