# Correctness review - Disturbed thinning soil lookup

## Metadata

- Reviewer: `/root/contract_review_one` (independent reviewer).
- Date: 2026-09-25 UTC.
- Base implementation: `2b0c3e30d5856f74069530b422e2541cc7820f06`.
- Accepted checkpoint: `b63e738d0c1b628cd8ac5b7f60bdb467628c9816`.
- Reviewed implementation: `9a5eb08137d572ef437764515144b8fba2134c64`;
  checkpoint ancestry verified and reviewed production/test files match this commit.
- Scope: the two soil lookup sites in `wepppy/nodb/mods/disturbed/disturbed.py`,
  new `tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py`, treatment-soil
  archive regression, changed NoDb guidance and Disturbed README.
- Canonical intent: `docs/schemas/disturbed-treatment-soil-lookup-contract.md`,
  sections Class resolution, Parameters and compatibility, Artifact acceptance
  and recovery; `docs/adrs/ADR-0073-disturbed-thinning-soil-lookup.md`.
- Applicable unchanged boundaries: NoDb persistence/concurrency, MOFE management
  artifacts, WEPP run inputs, artifact observability and generated-artifact
  validation standards. Contract reviews: `20260925_contract_reviews.md`.
- Security: no changed attack surface, identity, path construction, locking,
  authorization or exception boundary; no separate security review required.

## User outcome

Rebuilt thinning soils must receive the existing effective texture-specific
thinning row, including operator edits. All supported mulch suffixes preserve
burned vegetation/severity soil parameters. Management identifiers and generated
filenames stay unchanged. Existing derived soils and reports require supported
rebuild/preparation/rerun; deploying the patch alone does not repair them.

## Valid-state and input matrices

| State | Required behavior | Evidence |
| --- | --- | --- |
| Class absent/None | Existing missing-row handling | New artifact nonprefix test, both modes |
| Class empty | Existing missing-row handling | Same test with empty string |
| Populated thinning | Prefix selects effective thinning row | New artifact matrix and operator-row test |
| Bare/legacy/custom thinning | Same prefix rule, preserve artifact identity | Bare, hyphenated and custom mulch-suffixed cases |
| Populated mulch | Preserve burned base row | All 27 vegetation/severity/level combinations |
| Unknown string/case/whitespace mismatch | No new prefix match | Nonprefix artifact test |
| Malformed non-string | Existing helper raises; no coercion | Unchanged helper executes before added branch |
| Explicit management soil | Existing single-OFE override wins | Unchanged earlier `man.sol_path` branch; source inspection |
| Derived soil key already exists | Existing reuse; rebuild required | Unchanged cache branch; documented recovery limit |
| Working/failed/completed artifacts | Existing visibility and retention | Canonical archive soil and diagnostic payload checks passed |

The new input matrix comprises 16 catalog thinning classes, bare thinning and
two custom prefixes, plus 27 mulch combinations, crossed with single/MOFE and
formats 9002/9005. It uses one representative loam profile and five identical
MOFE assignments; it does not claim all textures, heterogeneous stacks, format
7778, every optional soil control, or full runtime-state coverage.

## User-reachable error policy

| Condition | Classification | Result and justification |
| --- | --- | --- |
| Unknown/absent lookup class | Expected | Retain existing single-OFE source or MOFE fallback; canonical Class resolution |
| Missing source, malformed soil, writer failure | Exceptional | Existing explicit errors and transaction behavior propagate unchanged |
| Malformed non-string class | Exceptional | Existing helper validation error; no new input contract |
| Stale generated key/result | Expected stored state | Supported rebuild/rerun required; no automatic repair or fresh-result claim |

No new exception handler or completion/status behavior is introduced. Existing
failure/rollback tests remain relevant; this patch changes lookup selection,
not transaction or partial-publication semantics.

## Generated artifact evidence chain

| Stage | Evidence | Result |
| --- | --- | --- |
| User intent | Operator approval in ancestor checkpoint | Pass |
| Persisted/reloaded assignments | Isolated local supported-fork script | Pass for local actual project |
| Converted soil components | Real `WeppSoilUtil` readback in new matrix | Pass |
| Combined MOFE soils | Real modifier and synthesis, five OFEs parsed | Pass |
| Prepared executable inputs | Real `prep_soil`/`prep_multi_ofe_hillslope`, parsed `p10.sol` | Pass |
| Archive/restore | Canonical archive/restore, member bytes and restored bytes | Pass, including final log-byte assertions |
| Execution output | No model execution in local input tests | Outstanding release/recovery evidence |
| Fresh report/live browse/download | Route regressions passed; no live service evidence | Outstanding operator gate |

`red-tests.log` records the prepatch single/MOFE failures for `thinning_30_90`.
`artifact-tests.log` records 198 passes in 939.01 seconds for the full new matrix,
operator-value overrides and nonprefix lookup behavior. The passing tests directly
verify the relevant parameter values in generated and consumed files.
`focused-tests.log` records 123 passes, including existing Disturbed, Treatments,
archive, browse and download regressions. `archive-final-tests.log` separately
records three passing final treatment archive/restore cases, including diagnostic
log bytes, in 35.97 seconds.
The regression retains the real failing class selection, soil conversion,
serialization, synthesis and preparation boundaries. Doubles isolate controllers,
locks and unrelated state; they do not produce the soil artifact bytes. The fake
slope fixture is explicitly a copy-boundary fixture, not model-execution evidence.

Actual-project check passed at 2026-09-25 16:08:21 UTC:
`local-project-result.json` records the supported fork/full rebuild of the older
local `/wc1/runs/ch/choice-feminist` copy into
`/wc1/runs/th/thinning-soil-validation-20260925`, under UID 1000/GID 993.
Revision `9a5eb08137d572ef437764515144b8fba2134c64` and implementation SHA-256
`d4f5b1e0e2f6dbdca332fe334b55d330103eb4542734ee85e41af89e3291b4db`
match the reviewed candidate. Source NoDb hashes for all 12 recorded files
remain unchanged. The supported treatment build selected `thinning_30_90` for
all five OFEs of hillslope 71. Both `soils/hill_71.mofe.sol` and prepared
`wepp/runs/p10.sol` have upper-layer Ksat 40, `kr=4e-5`, `ksatfac=1.3` and
`ksatrec=0.3` throughout. The reviewer independently verified retained artifact
hashes against the JSON and inspected prepared soil content.

This establishes actual local-project input acceptance. It does not establish
live wepp1 repair, fresh model outputs, live reports, or production identity/mount
parity. Only one treated hillslope was inspected in that project; the broader
treatment matrix is provided by local regression fixtures.

## Review checks

- [x] Canonical intent and standalone ancestor identified before implementation.
- [x] Requested prefix behavior reaches both soil lookup sites.
- [x] Shared helper, RUSLE, PMET and Treatments remain unchanged.
- [x] Original management class, key naming, override precedence and lookup values
  are preserved except for the approved effective soil-row selection.
- [x] State and input dimensions are separately described with coverage limits.
- [x] Failing boundary remains unmocked and generated values are parsed.
- [x] No safety, persistence, filesystem-path or error-contract changes.
- [x] Recovery and freshness limitations are explicit and understandable.
- [x] Completed focused and artifact validation results reviewed.
- [x] Required broad-suite attempt completed; preexisting failure independently
  dispositioned below. No full-suite pass is claimed.
- [x] Completed actual local-project evidence and source/artifact hashes reviewed.

## Findings and residual risk

No blocking implementation defect found. Earlier contract scope/state findings
were resolved before checkpoint commit. Residual risks are unchanged generated
key reuse, untested non-loam profiles in the new matrix, and pending validation
outside the reviewed local boundary. The two intentionally duplicated prefix branches require both-path
regression coverage, supplied by the new tests.

### Broad-suite baseline failure disposition

`broad-tests.log` records **1 failed, 5,286 passed, 54 skipped** in 1,995.69
seconds. `--maxfail=1` stopped at
`tests/nodb/test_wepp_run_service.py::test_run_hillslopes_uses_mofe_timeout_for_continuous_hillslopes[False-60]`;
later suite items were not executed. This is a failed broad run, not a pass.

The reviewer independently verified the following evidence:

- The failing test at lines 82-125 still expects single-OFE timeout 60, but
  `wepppy/nodb/core/wepp_run_service.py:28` supplies 120, as required by the
  accepted Decision in `docs/adrs/ADR-0072-continuous-hillslope-timeout.md`.
- Git blob identities for the runner, test and ADR match between starting
  revision `2b0c3e30d5856f74069530b422e2541cc7820f06` and candidate
  `9a5eb08137d572ef437764515144b8fba2134c64`, corroborating
  `timeout-baseline-identity.json`.
- `timeout-baseline-repro.log` independently reproduces the same assertion:
  one single-OFE failure, one MOFE pass. The test stubs `run_hillslope` and
  invokes only the run service; neither changed Disturbed soil lookup is called.

Disposition: confirmed preexisting timeout-test/ADR mismatch, outside this
bounded thinning correction. It does not block code-delivery correctness
sign-off, but must remain visible in handoff and suite-status claims. Leave
unrelated runner/test values untouched. The incomplete broad run is an explicit
coverage limitation, not evidence that every remaining test would pass.

## Artifact observability gate

The existing Disturbed workflow remains the reference: `soils/*.sol`, combined
`soils/hill_*.mofe.sol`, prepared `wepp/runs/*.sol`, existing logs and later WEPP
outputs retain normal browse/download/archive behavior. No hidden storage,
exclusion or cleanup change is introduced. Archive soil and diagnostic-byte
regressions passed in the final dedicated three-case run. Live
browser/download and fresh-report evidence remain release/recovery gates.
Lifecycle labels in the archive test establish payload retention independent of
the label, not actual writer-failure or model-execution coverage.

## Verdict

- Correctness gate: pass for the reviewed source and locally validated generated
  inputs; unresolved implementation findings: High 0, Medium 0, Low 0.
- Required broad-suite attempt failed on a verified preexisting timeout test;
  the disposition above permits bounded code-delivery closure, without claiming
  a passing full suite or coverage of items after the stop.
- Highest supported claim: locally validated; 198 direct artifact cases and 123
  focused cases pass, with prepatch single/MOFE failures retained. Actual local
  project input acceptance also passed on the exact candidate; production
  environment validation remains outstanding.
- Release recommendation: hold pending required environment/release evidence.
  Deployment and affected production-run recovery remain separate operator actions.
- Reviewer sign-off: `/root/contract_review_one`, 2026-09-25 UTC; source, final
  local artifact/archive results, actual local project and baseline-failure
  disposition reviewed. No remaining correctness finding within this package.
