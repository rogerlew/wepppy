# Correctness review: historic PRISM integration

## Metadata and scope

Reviewer: `prism_contract_review_a`, 2026-10-08 UTC. Independent read-only
implementation review; no production edits made by this reviewer.
Contract ancestor `d3b5958c5` precedes reader floor `e25299022` (ancestry checked).
The subsequent single-input correction checkpoint `5b97490e7` precedes the
aggregate reader floor `6781de988` (ancestry also checked). The reviewed
production candidate is the working-tree delta above the aggregate floor.
Authority: `docs/schemas/prism-historic-climate-contract.md`, its linked
lineage/NoDb/seed/scaling contracts, ADR-0082, and the Project Config PRISM
amendment. Review covered the adapter, collection/publication, raw-dewpoint
revision, router/parser, catalog/capability authority, UI and RQ schemas/tests.

## Findings and dispositions

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| COR-01 | High | Initial `climate_prism_build.py` mapped same-cell hillslopes to a shared CLI filename. Existing `ClimateScalingService.spatial_scale_precip` writes `scale_<filename>` for each hill's raster factor, so different factors overwrote the same destination and every alias used the last factor. | Resolved: generation remains cell-deduplicated, but publication copies distinct `prism800m-hill-<id>.cli` files. `test_same_cell_hills_can_receive_distinct_spatial_scaling` uses native Rust scaling/readback and verifies independent factors 2 and 3. |
| COR-02 | Medium | Initial `climate_observed_build.py` wrote completed revision status unguarded after durable finalization. A diagnostic-only OSError incorrectly failed the accepted build and skipped later hooks. | Resolved: completed-status OSError is logged without escaping. `test_prism800m_postcommit_diagnostic_failure_keeps_success` exercises the real finalization and confirms persisted readiness/files survive the injected diagnostic error. |
| COR-03 | Medium | RQ controller and build-operation schemas omitted mode 16 from required observed-year predicates, contradicting updated request validation. | Fixed during review: all four predicates now include 16 and schema regression expectations were updated. |
| COR-04 | High | The broad suite discovered that the existing single-input CONUS Builder variant derived from the new climate graph was absent from strict reader authority. Ordinary PRISM builds worked, but valid single-input project creation failed, including when Vanilla remained selected. | Resolved by reviewed checkpoint `5b97490e7` and catalog-only aggregate reader floor `6781de988`, followed by creation/refresh and exact-reader reopening evidence below. Strict validation remains unchanged. |

No unresolved high/medium code finding remains from this inspection. COR-04 was
missed by the initial focused review and found by the required broad suite; its
failure remains retained rather than being relabeled unrelated. Findings remain
recorded above after their fixes. The final evidence readbacks below close their
regression and live acceptance obligations.

## User outcome and state/error policy

The user can select historic PRISM on eligible CONUS graphs, generate a centroid
climate plus monthly revisions or nearest-cell hillslope climates, and execute
WEPP using those mappings. Raw source evidence remains available in ordinary
project artifacts. Early acquisition/publication failures preserve prior
accepted files; failed Multiple revision leaves the accepted centroid with
unset hillslope mappings and must remain unready for WEPP.

| Runtime state | Contracted outcome | Evidence reviewed |
| --- | --- | --- |
| Never used / empty optional attempt area | Create visible attempt and publish validated files | Real temporary filesystem/native CLIGEN builder tests; forest starts with no PRISM attempts and builds through the normal menu/RQ path |
| Populated prior climate | Keep old files until validated publication; rollback rejected work | Real NoDb/filesystem publication test and injected replacement/supersession tests |
| Same native cell, several hills | Equal unscaled weather, independent later spatial scaling | Native repeated-cell values and independent scaling tests; same-cell weather equality asserted for all live hills |
| Different native cells | Preserve PRN-quantized daily weather differences | Live mode 2 contains 24 cells and 24 distinct daily wet/dry calendars; all 104 hills checked against source forcing |
| Historical stored graph | Preserve authorized old dataset envelope | Reader-floor artifact and current graph regression suite; no graph migration introduced |
| Malformed dates / missing cell / changed input | Explicit validation/acquisition/supersession failure; retained evidence | Year, failed acquisition and supersession tests; bulk client's existing strict protocol/cache checks |
| Working / failed / complete archived attempt | Preserve source bytes and ordinary visibility | Canonical archive/restore tests; authenticated live browse/download and 993-file ZIP restoration evidence |

These are separate from input combinations Single/Multiple/MultipleInterpolated,
explicit/automatic seed, scaling modes, leap years and locale/capability envelope.
Coverage is not claimed exhaustive. Invalid provider coverage, incomplete years,
corrupt cache, changed inputs and denied filesystem publication are exceptional
failures authorized by the PRISM contract. Absent optional artifacts remain valid
create-on-build state. Diagnostic failure after successful publication logs and
must not change the accepted result.

## Generated-artifact evidence chain

| Stage | Evidence | Result at this review |
| --- | --- | --- |
| Request/menu intent | Catalog/parser/controller/schema delta; existing transport/CSRF preserved | Live authenticated menu/RQ builds for both methods; nearest-cell selection/label persisted on reload |
| Persisted state | Builder test reloads real Climate NoDb and checks mappings/readiness | Passed |
| Raw source and intermediate | Native PRN/CLIGEN/CLI roundtrip; source frame equality; portable source copy | Passed focused tests |
| Numerical transformations | PRN precipitation/Fahrenheit quantization; solar conversion; shared wind; raw Td floor for warmer and cooler revised Tmin | Passed native adapter test |
| Prepared WEPP input | Required `wepp/runs/p*.cli` mapping and numerical readback | All 104 hills per method match their prepared CLI bytes; model precipitation also matches those inputs |
| Execution output | Fresh completed WEPP results for both methods | Both 18-job trees finished; each case has 113,984 daily hillslope balance rows and finite watershed loss results |
| User inspection/archive | Canonical working/failed/complete archive tests; browser/download | Archive tests passed; authenticated browse/download HTTP 200 and matching source bytes; portable live ZIP readback passed |

Reviewer command `wctl run-pytest tests/climates/prism/test_wepp_adapter.py
tests/nodb/test_climate_prism_build.py -q` passed **7 tests in 10.81 seconds**;
log `/tmp/prism-review-correctness-tests.log`. Acquisition is substituted in the
NoDb test, but native CLIGEN, PRN/CLI readback, NoDb persistence and successful
filesystem publication are real. The replacement-denial regression injects
`os.replace` failure; it is not evidence of an actual permission-denied filesystem
under the forest identity. The actual authenticated production-equivalent
workflow and permission checks remain the live acceptance boundary.

Reviewer command `wctl run-pytest tests/nodb/test_locale_capability_authority.py
tests/microservices/test_rq_engine_schema_defaults_routes.py
tests/rq/test_project_rq_archive.py -q` passed **201 tests in 40.62 seconds**;
log `/tmp/prism-review-contract-tests.log`. This includes corrected schema
predicates, current and historical capability structure validation and retained
PRISM attempt byte equality through archive/restore.

`reader-floor-live.json` records old-writer/new-reader coexistence, both exact
structural identities, unchanged target state and historical v2 readability.
It is reader compatibility evidence, not WEPP execution evidence.

## Final candidate and forest evidence readback

The reviewer inspected the latest working-tree production changes, the new
COR-01/COR-02 regressions and the explicit failed-revision readiness test.
`/tmp/prism-review-regressions-final.log` records **45 passed** in 16.14 seconds;
`/tmp/prism-revision-failure-test.log` records **2 passed** in 18.08 seconds. The
latter verifies that failed revision leaves the centroid bytes intact, no
published partial hillslope, unset mappings, retained failed status and
`has_climate == false`. These are regression evidence, not live failure claims.

Reviewed `forest_readback.py` and its two result JSONs: each case checks all
104 hills over 2019-2021 (1,096 days including leap day), source-to-CLI numeric
transforms, exact prepared CLI bytes and WEPP precipitation parity. Monthly
revision has one shared wet/dry calendar; nearest-cell mode has 24 native cells
and 24 calendars. Both RQ trees contain 18 finished jobs. Each model result has
113,984 daily hillslope balance rows with finite checked values and nonnegative
precipitation/runoff/ET components. The evidence is execution/parity evidence;
hydrologic accuracy is not established by these checks.

Independent worker reads confirmed both retained case directories and current
Climate mode 16 / spatial mode 2, years 2019-2021, readiness true and seed 84568.
The normal worker is UID 1000 / GID 993; the exercised WEPP binary is
`wepp_260430`. The readback artifacts name complete case snapshots below the
project's `archives/`, preserving both methods before the final nearest-cell
selection. The reviewer independently verified all 104 retained CLI SHA-256s
and prepared copies in each case, plus the browsed source and portable ZIP
digests against the retained JSON evidence.

`forest-evidence-2.json` records authenticated ordinary browse/download HTTP
200, the expected menu selection and nearest-cell label, and source SHA-256.
`forest-portability.json` and its reviewed script verify 993 restored files
byte-for-byte, 72 source partitions and 24 cell tables with the cache environment
pointing to a nonexistent path. This live check restores a climate ZIP into an
isolated temporary directory; it does not claim the full live project was
restored. The canonical project archive/restore path has separate real regression
coverage for working/failed/complete PRISM records.

Current worker-mounted candidate SHA-256s inspected for the principal paths:

| File | SHA-256 |
| --- | --- |
| `wepppy/climates/prism/wepp_adapter.py` | `5a9b03cea230078b64f922ab728696368bb203d057b782c3d5ae91e90cf289dc` |
| `wepppy/nodb/core/climate_prism_build.py` | `4ceffa92bff40b223e140e5c46fe93c1723c00a7b939dddd22b07b05c8046b17` |
| `wepppy/nodb/core/climate_observed_build.py` | `bab9e238a3f299eba4d08510ba3a736dac5f2b5894983a6503e0ac4d171d0e5e` |
| `wepppy/nodb/core/climate_build_router.py` | `8fa8ab52db42b92230ab925603f9e52ef8bd0f7d6d152cb9324ab1191ada7749` |

## Broad-suite discovery and aggregate reader correction

The initial broad run stopped after **4,964 passes and 51 skips** on
`test_single_inputs_are_independent_creation_capabilities[single-ofe]`.
This was a genuine PRISM integration regression: the unchanged single-input
transform retained the new climate axis, producing unregistered identity
`545e2197c8a67a88da9c796246a2b0572427c8228bcb0e5d3ccd883f11b320a6`.
The strict reader rejected the variant before publication. The prior two-mode
watershed evidence remains valid, but it could not establish compatibility for
this separate creation-time variant.

After independent contract reviews and checkpoint `5b97490e7`, commit
`6781de988` changes only the reader catalog. Independent JSON comparison of its
parent and result verified **17 prior payloads and identities unchanged, zero
removals, and exactly one added payload**, byte-equivalent as canonical JSON to
the approved candidate. The sole existing-record metadata change fills the
ordinary PRISM entry's reader revision from pending to `e25299022`; it changes no
capability. The working-tree metadata similarly records the new variant's actual
reader revision as `6781de988`. Both structure hashes were independently
recalculated; strict parsing and single-input policy code were not changed.

Inspected regression results:

- `/tmp/prism-single-input-fix.log`: **94 passed**, Builder snapshot plus
  capability authority tests.
- `/tmp/prism-single-input-create-refresh.log`: **14 passed**, single-input
  creation and explicit-refresh tests. The added cases cover both OFE
  representations and Vanilla/PRISM selection, preserve the restricted binary,
  excluded modules, independent landuse/soil methods and accepted source bytes.
- `/tmp/prism-aggregate-reader-tests.log`: **75 passed**, current reader
  authority and retained historical structure checks.

Reviewed `reader_floor_reopen.py` and
`aggregate-reader-floor-reopen.json`: code and catalog extracted from exact
commit `6781de988` reopen all four ordinary/single-input by single/multiple-OFE
current-writer configs with equal authority and unchanged persisted bytes.
The ordinary structure remains `2c293468...`; the single-input structure is
`545e2197...`. These are isolated persisted Builder configurations; the live
target's graph was not migrated. The aggregate rollback floor must now be
`6781de988` or a descendant retaining both PRISM identities.

The remaining 389 test modules resume from the failed Builder snapshot module
via the retained `remaining-test-modules.txt`. The first resumed run stopped
after 36 passes on a stale schema-v1 named-preset live-climate expectation in
`test_project_config_capabilities.py:283`: it expected seven CONUS datasets and
the implementation returned the newly ratified eighth PRISM dataset. Inspection
confirms this fixture describes current live projection, not a frozen stored
v2/v3 envelope; updating its expected climate axis is appropriate. The final
diff updates only current preset/registry expectations; historical stored graph
fixtures remain unchanged. No additional production defect was identified from
that failure.

The restarted continuation then reached **5,219 passes and 75 skips** before
`test_openet_signed_token_live_membership_admission` returned HTTP 503 instead
of its expected 403. The retained traceback shows Redis authentication failure
while acquiring the submission lock in middleware, before the climate handler.
This is distinct from COR-04 and does not establish a PRISM forcing defect.
The complete 33-test feature-access module and all remaining tail modules then
passed: **301 passed in 108.19 seconds**, without changing the admission code or
that test. Logs inspected: `/tmp/prism-integration-remaining-pytest-final.log`
and `/tmp/prism-integration-tail-pytest.log`.

Broad regression disposition is now complete through the original run,
correction-focused runs and continuations. The earlier 4,964 passes remain
evidence; overlapping counts must not be added as unique coverage. This is
completed segmented coverage, not a claim that one uninterrupted full-suite
invocation passed. The Redis-authentication failure remains a suite/environment
limitation recorded in the validation ledger; its passing isolated module/tail
does not identify or fix the underlying source of that test-context failure.

## Residual risks and limits

- Completed segmented Python coverage and retained failed probes are described
  above and in `validation.md`; no uninterrupted all-suite pass is claimed.
  Frontend 925-test success was reported by the primary
  agent; this reviewer did not independently rerun the frontend suite.
- The PRISM-scoped broad-exception gate passed. The primary agent's ledger
  reports a later workspace-wide warning associated with concurrent non-PRISM
  RQ notification edits and a line-based allowlist. Those files were outside
  this review and are not certified here; this pass is limited to PRISM scope.
- **CLIGEN convergence remains a real limitation.** An independent read of the
  final target confirms `silent_pass_observed_quality_guard == true` and the
  persisted warning: "CLIGEN failed to converge, continuing because silent-pass
  is enabled. Try selecting different station or setting Adjust MX .5 P Values".
  Completion does not mean the storm generator converged. The existing option
  and warning contract were preserved; no bypass was introduced by this change.
  Within-day storm duration/intensity should not be described as validated
  observations or scientifically validated solely from these successful runs.
- Automatic seed behavior remains the established observed default; no new
  numeric seed is imposed. Explicit override reaches native CLIGEN unchanged.
- OpenET and AgFields currently enumerate observed modes without 16. They are
  separate integrations; expose the limitation in handoff or deliberately
  register/test any intended extension instead of claiming full feature parity.
- Final precipitation parity must account separately for PRN quantization,
  monthly revision and configured scaling. Daily spatial forcing does not
  establish observed within-day storm timing or scientific model accuracy.

## Verdict

**Correctness gate: pass; release recommendation: ship.** All four findings
are closed, and no unresolved high or medium finding remains. The requested
two-method forest workflow is demonstrated through persisted state, generated
and prepared inputs, completed execution and ordinary artifact access, with
the explicit convergence limitation retained. Broad regression disposition is
complete through the documented segments and focused reruns. This sign-off
does not certify unrelated concurrent work or erase the retained Redis-auth
failure. Final reviewer sign-off: `prism_contract_review_a`,
2026-10-08T23:55:16Z.
