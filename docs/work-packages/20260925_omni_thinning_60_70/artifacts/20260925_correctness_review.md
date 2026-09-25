# Correctness review - Omni thinning 60% and 70%

## Metadata

- Reviewer: `/root/contract_review_one`, independent correctness reviewer.
- Date: 2026-09-25 UTC.
- Starting implementation: `cf6437095fead72722f91ccc124119c7f824d65e`.
- Accepted ancestor checkpoint: `9ed7398754a6ee3860ccdc933a02ff1b90903691`.
- Reviewed candidate: `2d0891398`; checkpoint ancestry verified and reviewed
  production/test files match this implementation commit.
- Scope: eight management assets, five catalog additions, CSV additions, Omni
  selector, changed regression coverage and affected user/developer documentation.
  Unrelated `code-quality*` changes are excluded.
- Authority: `docs/ui-docs/contracts/omni-thinning-contract.md`, all sections;
  `docs/adrs/ADR-0074-omni-thinning-60-70.md`, Context and decision; unchanged
  MOFE management, Disturbed treatment-soil, controller and NoDb contracts.
- Contract review evidence: `20260925_contract_reviews.md` in this directory.
- Security review: not required; no changed authorization, identity, filesystem
  boundary, locking, transport or exception-handling surface.

## User outcome

Users can select 60% or 70% remaining canopy with any existing ground-cover
choice. The selector retains 30/40/50/65%, defaults to 40% canopy and 93% ground,
and reloads legacy 65% scenarios unchanged. Existing files and IDs remain valid;
65% regional availability is preserved rather than expanded. Existing outputs
are not rewritten. New choices require running the new scenario for fresh results.

## Valid-state matrix

| State | Required behavior | Evidence |
| --- | --- | --- |
| Never used or absent scenario list | Add thinning with 40/93 defaults | Passing new-row controller test |
| Empty scenario list | Same ordinary default behavior | Existing controller creation path; no changed branch |
| Populated new 60/70 selection | Hydrate and serialize the original percent strings | Passing parameterized controller test |
| Populated legacy 30/40/50/65 selection | Preserve selection, files and IDs | Controller test plus independent compatibility readback |
| Missing/malformed parameters | Existing explicit parser errors | Existing Omni parser suite passed; no parser changes |
| Working/failed/completed scenario | Existing lifecycle and artifact visibility | No changed status path; labeled archive snapshots passed |
| Archived/restored run | Preserve management and diagnostic bytes | Canonical archive/restore regression passed |

The input matrix covers the eight new canopy/ground combinations in all five
catalogs, single-OFE preparation, and mixed eligible/ineligible MOFE segments.
Controller hydration covers all six canopy choices with one representative
ground choice; it does not claim every possible UI state combination.

## User-reachable error policy

| Condition | Classification | User-visible behavior and authority |
| --- | --- | --- |
| Missing canopy or ground | Exceptional request | Existing explicit parser failure, unchanged under Compatibility, states and errors |
| Unsupported/malformed payload | Exceptional request | Existing parser/build failure; no new coercion or fallback |
| Existing completed scenario after software update | Expected state | Previous results remain unchanged; run a new selection for fresh output |
| Writer or build failure | Exceptional execution | Existing status/error and retry behavior; no new completion path |

The patch adds options and assets only. It does not alter partial publication,
cleanup, retry, locking or failure handling. Rollback after saving new choices
must retain their hydration/serialization and referenced assets, as the ADR states.

## Generated artifact evidence chain

| Stage | Direct evidence | Result |
| --- | --- | --- |
| User intent | Approved ancestor checkpoint and six-choice controller test | Pass |
| Saved-selection hydration | Actual controller reads backend-shaped values and serializes them | Pass; HTTP/NoDb transport is stubbed |
| Source managements | Parser reads all new catalog variants; exact source byte comparisons | Pass |
| Serialized managements | Real management writer and parser round trip | Pass |
| Combined MOFE management | Existing scenario builder and real synthesis, mixed segments | Pass |
| Prepared WEPP management | Real single/MOFE preparation and parsed canopy/rill/interrill | Pass |
| Soil parameter propagation | Expanded thinning-prefix artifact matrix, 230 cases | Pass within broad run |
| Archive/restore | Canonical project archive and restore, member/restored bytes | Pass |
| Model output and live report | No model execution or production mutation in this package | Outside local delivery; release gate remains |

`red-tests.log` demonstrates the missing `thinning_60_90` catalog variant before
implementation. `focused-tests.log` records 308 passing tests plus 12 subtests,
including management variants, mixed MOFE inputs, archive, parser/build services,
catalog snapshot, browse and download regressions. `frontend-tests.log` records
913 passing tests in 112 suites. Frontend lint and the canonical controller bundle
build completed; inspection of `controllers-gl.js` confirms the six-choice list.

`broad-tests.log` completed the entire expanded soil module with
230 passing cases and advanced to subsequent modules. `soil-test-manifest.log`
records those 230 collected identities; the reviewer independently counted 32
new 60%/70% cases (eight variants, two soil formats and two OFE modes). The matrix
also retains 65%, other legacy canopies, custom prefixes, mulch, operator edits
and nonprefix/missing classes. This proves the new variants consume existing
thinning soil parameters in actual generated/prepared loam artifacts. The broad
suite later stopped at the unrelated baseline failure dispositioned below.

No mock replaces the changed asset, catalog or selector boundary. Management
tests use real parser/writer/synthesis/preparation. The mixed MOFE management test
stubs soil work, which is independently exercised by the expanded soil suite;
it is not presented as soil evidence by itself. No actual-project or live-browser
acceptance is claimed by these local tests.

## Independent compatibility checks

The reviewer independently compared files to the starting revision, in addition
to inspecting `check_compatibility.py` and `compatibility.json`:

- All 322 preexisting records across the five catalogs retain their complete
  values. All 16 legacy thinning assets, including every 65% asset, retain bytes.
- Each catalog adds eight unique keys; numeric `Key`, `DisturbedClass`,
  `IsTreatment` and management paths agree. IDs are 151-158 or C3S 451-458.
- Every new file equals its matching 40% source after exactly one initial-canopy
  token change. Ground covers, LAI and every other source byte are preserved.
- CSV compatibility evidence preserves all old bytes and validates the eight
  added row values. Existing CRLF line endings are retained. Some new management
  assets inherit source trailing whitespace/final blank lines; exact source-byte
  preservation is intentional. Do not report an unqualified whitespace-check
  pass across these assets; the CRLF-aware non-management check passes.

## Review checks

- [x] Canonical intent, independent approvals and ancestor checkpoint verified.
- [x] Source implementation is additive and satisfies the approved parameter rule.
- [x] Legacy 65% IDs, assets, selector value and hydration are preserved.
- [x] State and input combinations are separately stated with coverage limits.
- [x] Real generated/consumed management artifacts are parsed for semantic values.
- [x] Unchanged soil behavior is not inferred from mocked management-side calls.
- [x] No change to auth, locking, paths, schemas or error/completion contracts.
- [x] User, operator and developer documentation describes the new choices.
- [x] Partial state, old results, deployment and rollback limitations are explicit.
- [x] Expanded soil matrix passed; collection manifest and execution log reviewed.
- [x] Required broad-suite final result reviewed and baseline failure dispositioned.

## Findings and residual risk

No blocking source or test-quality defect found. Numerical parity is protected by
exact asset comparisons and real management readback. Remaining evidence gaps are
tests after the broad-suite stop, actual browser execution under service identity, and
fresh model outputs. Archive lifecycle labels are snapshots, not a complete
scenario lifecycle/failure simulation. No package claim should exceed these bounds.

### Broad-suite baseline failure disposition

The required broad run completed with **1 failed, 5,326 passed, 54 skipped** and
116 warnings in 1,977.31 seconds. `--maxfail=1` stopped at
`tests/nodb/test_wepp_run_service.py::test_run_hillslopes_uses_mofe_timeout_for_continuous_hillslopes[False-60]`.
The assertion receives 120 seconds while expecting 60. This is not a full-suite
pass, and later tests were not run.

The reviewer independently verified that runner, test and ADR-0072 Git blobs
are identical at starting revision `cf6437095` and candidate `2d0891398`, matching
`timeout-baseline-identity.json`. The runner's 120-second single-OFE timeout
matches the accepted Decision in ADR-0072; the test retains the earlier 60-second
expectation. Its stubbed `run_hillslope` path does not read the changed management
assets/catalogs or execute the selector. This same failure was independently
reproduced during the preceding soil-correction package; its runner/test/ADR
blobs are also unchanged here.

Disposition: confirmed preexisting test/ADR mismatch, outside this bounded
addition. It does not block source/local artifact code-delivery approval, but
the failed and incomplete broad gate must remain explicit in handoff. No
unrelated timeout behavior or test expectation was changed to obtain a pass.

## Artifact observability gate

The existing Omni/Treatments layout remains unchanged: management sources,
`landuse/hill_*.mofe.man`, prepared `wepp/runs/*.man`, soil artifacts, logs and
later WEPP outputs use normal project browse/download/archive paths. Canonical
archive restoration and existing browse/download route coverage passed locally.
Live browser/download checks remain an explicit operator release gate. No new
hidden-only records, exclusions or cleanup behavior require an exception.

## Verdict

- Source/local management and soil correctness: pass; High 0, Medium 0, Low 0 findings.
- Final code-delivery correctness gate: pass, with the documented preexisting
  broad-suite failure and resulting later-test coverage limitation.
- Highest supported claim: locally validated management/UI/soil addition; not deployed.
- Production release recommendation: hold until separately required live
  acceptance. No live project was repaired or model output refreshed.
- Reviewer sign-off: `/root/contract_review_one`, 2026-09-25 UTC. Candidate
  `2d0891398`, compatibility, focused/frontend/generated-soil evidence and final
  broad-suite disposition reviewed. No remaining finding within this package.
