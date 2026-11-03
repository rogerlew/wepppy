# MIPA-02 native repair and revision 6 execution

## Result and authority

The operator requested contract-first native repair, producer/consumer reconciliation
and revision of undeployed 261029. Standalone ancestors WEPPpy `a42b9d640` and native
`0a8727057` precede implementation. Two independent contract reviews passed after
clarifying unsupported9005/RAP consumers and existing PMET parse behavior.
Durable intent: `docs/schemas/native-mofe-coefficient-contract.md`, whole-soil/MOFE
identity contracts, native `docs/contracts/mofe-coefficient-ownership.md`, ADR-0133.

Native model source `b581352b6` changes FC/HK COMMON dimensions and all active
references in daily/hourly water balance, PURK, PERC and DRAIN. Formulas, guards,
initialization timing, defaults and output formats stay fixed. Current 261029
already has ntype-sized PMET arrays and direct EVAPPM mapped selection; the
six-slot/adapter findings belong to the older kernelized audit checkout.

Native release/report commit `8931daed29268dae930b3ee8a9f73c663fd203c6` is pushed
and verified on remote-default `wepp_260430_negmeltfix_comparator`. No branch
switch occurred. Full configured application supplement `4f0728984` follows;
its independent review is `mipa02_full_context_qa.md`. WEPPpy release handoff is
local; no production deployment.

## Matched artifacts

| Artifact | SHA256 |
| --- | --- |
| Watershed 261029 r6 | `611a145b02955d1e71d6dfadb3a0810c09b5ad883bd375093f7f5f27131f248a` |
| Hillslope 261029 r6 | `ef8a23f494b595fba48208c196b3f673f6834feea90d3a024179c7028eecea31` |
| Reviewed 3-page PDF | `247176029b2537f3a1676cd5fa6ff2797793839dc361240cfcdbe24ae938aa66` |
| Final watershed sidecar | `71a15f61d762187b07f14a3b860a70f4f1bb010a3b1a4464ce7a11d8c122e55c` |
| Final hillslope sidecar | `289f7530b6a9343d6ade2fd2deb3d6e669eeb1414eee8d14ba46a33c068eb809` |

Built sequentially with `TARGET_TAG=261029 tools/build_wepp_dated_release.sh`,
system gfortran and pinned PATH. All units rebuilt after COMMON ABI change;
watershed includes restored. Native/installed executable and sidecar bytes match.
Eight prior native/vendored revision 5 files are retained under
`/wc1/holdouts/mipa-native-r6-20261102/baseline-r5/manifest.json`.

The installed Rust extension is unchanged at SHA
`7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad`.
Producer source repair `5e3540f` is not a newly installed Rust release.

## Validation

| Check | Observed result |
| --- | --- |
| Compiled real initializer/PURK/PERC before correction | Four distinct-material failures, eight passes |
| Focused native probes after correction | 26 pass; includes unequal layers/order, frozen states, eight drain/lateral expressions, PMET 32/15000 capacity, mapped transitions and guarded-HK sentinel cases |
| Full native suite | 1416 passed, two tarfile deprecation warnings; four later-added guard cases pass separately |
| Native watchlist / smokes / artifact policy | 31 pass / both roles pass / pass |
| Four 16-year ownership histories per revision | Both policies × daily/hourly; 17532 OFE/day rows each |
| First dynamic ownership observations | Wrong-owner states 20/30 before,0/30 after;15 actual sub-0.95 powers per history |
| Observer neutrality | Seven ordinary outputs exact per history in both revisions |
| Six single/repeated-material controls | Exact before/after inputs and outputs; committed generator and binary hashes bound |
| Actual producer + runner PMET history | 48 OFE/year mappings, three distinct pairs, retry identity, reversed-row exact parity |
| Post-vendor tests | Eight pass; both installed smokes and provenance pass |
| Installed pair application | Fresh two-year three-OFE hillslope and watershed run, 13 output hashes verified |
| Copied actual project, partial preparation | 72 hills,235 OFEs,35 years;504 fresh outputs; installed interchange/report readback passes |
| Same-input partial-preparation counterfactual | Retainedr5 also completes; all 504 outputs exact, all 235 per-OFE water deltas zero |
| Complete configured copied-project workflow | Canonical preparation, enabled UI/baseflow native consumption, 72 hills/235 OFEs/35 years and installed report readback pass; all 504 outputs match r5 on identical 363 inputs |
| Local document delivery | Final PDF/manifest bytes and application/pdf/application/json verified over configured HTTPS endpoint |
| Broad WEPPpy sanity | Initial run: 9899 passed, 422 skipped, one test-isolation failure; repaired fixture sequence 43 passed; continuation 3623 passed, 7 skipped |

The initial copied-project run omitted its enabled baseflow/UI companion files.
Its inputs/outputs are preserved, but it does not prove the complete configured
workflow. Canonical preparation and fresh installed-name execution pass under
`actual-project-full-v1`: 363 model inputs, including `gwcoeff.txt` and
`wepp_ui.txt`; all 72 logs confirm both companion consumers and 35 completed
years. Installed interchange/report readback passes (72 hills, 36 water-year
groups, 3,004,240 water rows). This full workflow supersedes v1 as configured
application acceptance. The configuration completion changes 433/504 outputs
relative to v1; those differences are not attributed to the ownership repair.
Retained revision 5 against the identical 363 full inputs produces all 504 outputs
exactly and zero per-OFE water deltas (`actual-project-full-r5-v1`).

The same-input partial-preparation project is a non-discriminating control, not evidence that
arbitrary heterogeneous materials are unaffected. The distinct-material committed
S01 cases supply the ownership failure and correction proof. Per-OFE runoff, ET,
deep percolation and terminal storage change materially there; the report gives
four measured comparisons. These are printed per-element diagnostics, not watershed
outlet/full-budget closure or field calibration.

Commands and machine receipts are bound in `mipa02_release_evidence.json`.
Additional receipts: `mipa02_http_delivery.json`, `mipa02_installed_reader.json`,
and private `actual-project-r5-v1/receipt.json`. Mandatory native gates use
committed fixtures/generators. The actual copied project is supplementary.

## Reviews and retained attempts

Independent contract, source correctness, QA, scientific/disclosure and security
reviews pass. Final review records and QA logs are retained in this directory.
The final PDF was independently rendered/inspected on all three pages. A disclosure
review corrected the historical Roads score:744 passed, 96 failed; overall acceptance
remained unmet. Prior failure counts are not revision 6 scientific campaigns.

Retained failures include observer-v1 missing its committed calendar module
(fixed helper `f0ab62935`, clean fresh v2 builds), PMET probe v1 container mount
assumption, PMET probe v2 calendar-year assertion, and actual-readback v1 wrong
Climate property. Corrected guarded helpers completed fresh final attempts.
Initial local HTTP requests hit an empty unmatched host response or HTTPS redirect;
the configured HTTPS endpoint then returned exact bytes and MIME types. None of
these failed attempts is relabeled successful.

## Remaining boundaries

Native 261029 lacks specialized 9005/revegetation and RAP cover readers. Source
inspection finds extended-header misbinding, duplicate restrictive-layer reads,
9003-only lower-limit logic, and no specialized cover readers. The user preference
question did not receive an answer during independent execution; retain the
separate compatible-engine requirement. No silent input downgrade or new reader/
physics port is included. SOIL-02/COVER-01 full native acceptance remains HOLD,
so the broader package stays open.

Observation records first initializer/PURK/PERC-power states per slot, not every
time step. Drain/lateral probes test actual expressions, not complete tile-drain
control flow. No new tillage/density refresh policy, missing-density generalization,
retention default, thermal calibration, Windows release or universal scientific
validity claim. Historical runs/reports and unrelated dirty work are preserved.

## Broad-suite isolation repair

The full invocation stopped after 9,899 passes and 422 skips at the PMET unsafe-name
fixture. The PMET module passes 28 tests alone; running `tests/test_managements_module.py`
first reproduces one failure after 33 passes. Its hand-loaded management module
replaced and then removed the canonical `sys.modules` entry, splitting enum/class
identities from consumers already imported during collection. The fixture now uses
normal `importlib.import_module`; the identical two-module sequence passes all 43
tests. This changes test isolation only, not PMET or native runtime behavior.

The continuation reran that fixture and every following test path through the end
of the suite: 3,623 passed, 7 skipped, 79 warnings in 269.35 seconds. The initial
run recorded 5,785 warnings and stopped after 3435.29 seconds. Counts overlap and
are not summed. The independent ordered rerun passes 43 tests; test-stub checks
also pass. See `mipa02_test_isolation_qa.md`. Retain the initial failed log and before/after order reproductions;
this is segmented coverage, not an uninterrupted full-suite green result.
