# Implementation correctness and compatibility review

## Metadata

- Reviewer: independent `contract_correctness` agent, 2026-09-16 UTC.
- Accepted checkpoint ancestor: `9395f4722`.
- Scope: working implementation of Kf acquisition/composition, schema readers,
  result/report projection, source freshness, advisory preflight and response
  curves. Production files were reviewed read-only.
- Canonical authority: `docs/kf_source.md`, Predictor, acceptance and freshness
  compatibility; report contract, Kf, response curve and rainfall provenance
  amendment; unchanged NoDb and RQ contracts.
- Parallel security and UX reviews own their detailed boundary assessments.

## Findings

| ID | Severity | Surface | Finding and required action | Status |
| --- | --- | --- | --- | --- |
| IMPL-COR-01 | Medium | A model/frequency selection changes during Kf preparation | The original `production.py` preparation/publication checks only inspected captured source authority, although `/selection` allows selected model/frequency changes during execution. The added `check_attempt` verifies running attempt ID/model/snapshot, active dNBR, selected model and frequency before/after preparation and inside publication. The real-artifact production regression changes both selections during acquisition and changes frequency immediately before the final mutation, asserting prior acceptance survives. | Resolved; regression passed in 633-test module sweep |
| IMPL-COR-02 | Medium | Inverse arithmetic failure while creating the curve | The original `response_curve.py` discarded arithmetic failure statuses returned by the scalar inverse and advertised an available curve. It now detects arithmetic reasons in both P50 and P99, returns unavailable, preserves P50, and retains ordinary constant/negative-rainfall semantics. The tiny positive F regression reproduces the previously missed branch. | Resolved by direct post-fix execution |

No high-severity finding was identified in the reviewed changes.

## Evidence and coverage

IMPL-COR-01 follows the actual selection route through the publication guard;
`_current_authority` reconstructs project source inputs using explicitly supplied
model/frequency and does not inspect the selected state. The new `check_attempt`
closes that gap. `test_upload_and_model_real_artifacts` invokes the real NoDb
mutation and publication callback; only source delivery and the timing of a
selection change are substituted. The boundary that previously permitted stale
publication remains real.

IMPL-COR-02 was reproduced by executing the actual pure `staley2017.py` and
`response_curve.py` modules against the snapshot above, without modifying source
files. Output was:

```text
status=available; reason=None; range_max=1.0;
p50.status=unavailable; p50.reason=arithmetic_overflow
```

Post-fix direct execution of those same modules now returns `status=unavailable`,
`reason=arithmetic_overflow`, no range and no sampled points. Independent direct
checks also preserve available constant/decreasing curves with the appropriate
unavailable P50 reason. The new pytest module supplies all-duration independent
published-coefficient checks, exact design insertion, source/schema round trip,
invalid/missing Kf admission, and retained failed-stage assertions. The reviewer
read the parent's completed logs and confirmed:

- `wctl run-pytest tests/nodb/mods -k postfire_debris_flow --maxfail=1`:
  **633 passed, 1047 deselected, 31 warnings in 196.44 s**. This includes the
  publication/selection races, tiny-response arithmetic regression, and
  independent all-duration coefficient checks.
- Route/rendered-shell command over
  `tests/microservices/test_rq_engine_postfire_debris_flow.py`,
  `tests/weppcloud/routes/test_postfire_report_bp.py`, and
  `tests/weppcloud/routes/test_pure_controls_render.py` with `--maxfail=1`:
  **250 passed, 8 warnings in 14.73 s**.
- `wctl run-pytest tests/rq/test_project_rq_archive.py -k postfire --maxfail=1`:
  **1 passed, 21 deselected, 3 warnings in 9.99 s**. The canonical archive
  regression is separate from the remaining live browser/archive inspection.

Retained [module log](logs/module-tests.log) (SHA-256
`fabdc47fa6d9965a3b2280173bbadb937adb1b2dcf216bd3f25edb6e7a0b1170`)
and [route log](logs/route-tests.log) (SHA-256
`b05985e8f39a0a27bfb3bf29ddd3f622a137711e8de1b2141dad03ef612564c4`).
Retained [archive log](logs/archive-test.log) (SHA-256
`2edf9113cb8ab8f1e1519adb0784d9d3586617bd8844aa1d5fb6b6a17b753051`).

The schema-3 dispatch is additive, retains schema-1/2 readers, validates Kf
source/grid/artifact relationships and recomputes S over the saved common mask.
Production source selection excludes POLARIS receipts/files for new M1, while
explicit legacy policy retains them. Advisory preflight reads the accepted
policy and preserves separate M3 rules. Existing scalar coefficients and common
support formulas are unchanged. Bounded sampling, finite units and exact saved
design/P50 insertion are otherwise consistent with the curve contract.

## Valid states and remaining acceptance

| State/input | Assessment |
| --- | --- |
| Missing optional Kf | Run prepares an attempt-owned source; local state reads do not fetch |
| Legacy M1 / current M3 | Additive reader and source dispatch covered by passing focused sweep |
| Failed new preparation | Retained-source and accepted-state regressions pass; failed harness evidence and prior attempts remain retained |
| Changed selected model/frequency | IMPL-COR-01 fixed; real publication regression passes |
| Zero/negative response | Direct scalar/curve checks and focused pytest pass |
| Arithmetic inverse failure | IMPL-COR-02 fixed and direct reproduction passes |
| Malformed/hostile files and range identity races | Dedicated security code findings resolved; boundary regressions pass |
| Archive/restore and real generated outputs | Canonical archive regression plus live generated-file round trips pass |

This is bounded implementation and development acceptance review, not a claim
of exhaustive tests or deployment to another host.

## Final live evidence disposition

The reviewer inspected [restart evidence](forest_restart_validation.md), both
M1 browser evidence records, `validate_live.py`, both numeric result JSON files,
the actual archive/restore harness and hash inventories, preservation evidence,
the M3 browser record and the final UX review. Development acceptance passes:

- [nervous-mesquite](nervous_mesquite_e2e.md): real browser/RQ job
  `b5232960-674f-4468-ba0f-a67588bed59d`, accepted attempt
  `0ea9c1f5b0964b22ba7f1b457c1a6c9f`, after the canonical forest restart.
  Saved raster T/F/S independently match the accepted predictors. Kf is
  0.1393960061975289 and I15=24 mm/hour probability is 0.7219154455948592.
  Independent checks cover 8,067 event rows, 12 design rows, three inverse rows
  and all four duration/unit curve CSVs. The P50 intensities match the separately
  transcribed coefficients. The source identity, saved policy and source hashes
  agree across preparation, schema-3 predictors and result publication.
- [Generic fixture](generic_e2e.md): real browser/RQ job
  `087cf30a-db0d-4ffa-afc2-7c9ea4e70a7a`, accepted attempt
  `089792b89459438ebd5de3f2c4b972c0`, without preexisting RUSLE/POLARIS or manually
  acquired Kf. This basin obtains a different actual source value, approximately
  0.20, over 1,156 cells. Independent checks cover its 90 event rows, 12 design
  rows, three inverse rows and all curve CSVs. Synthetic upstream terrain/climate
  make this source/workflow evidence, not a second real-fire validation study.
- Both browser records finish with PASS and preserve the same accepted identity
  through report/download/reload. The fixture explicitly retains visible,
  current postfire immediately after RUSLE removal and after reloads 1 and 2.
  Rainfall provenance labels match recorded GridMetPRISM/Vanilla contexts.
  English exports use the preexisting Unitizer factor 0.0393701; the scientific
  artifacts remain in canonical units. No parameter conversion change is claimed.
- [Protected input evidence](nervous_preservation.json) covers 387 files, no
  scientific changes and no replaced historical attempt files. The sole byte
  difference is the existing `climate.nodb` serialization timestamp, explicitly
  distinguished from input/configuration changes. The M3 read-only regression
  reports no model mutation and all 23 protected files unchanged.
- Canonical archive/restore on isolated copies round-trips all 137 named-run
  and 62 fixture records byte-for-byte, including actual range bodies, native
  and aligned Kf, metadata, manifests and generated outputs. These operations
  test the real archive engine with isolated runtime seams; they do not claim
  that the live projects were restored or that archive API authorization was
  retested.

Residual limits: live curves cover ordinary increasing responses; exceptional
inverse behavior is covered by focused tests and source review. Keyboard evidence
covers P50 focus and marker activation, while details expansion used its native
`open` property in the harness. The second basin uses synthetic upstream inputs.
Preflight needed one targeted recovery restart after Redis returned `LOADING`;
the retained restart report identifies this existing startup-order issue.
None of these limits leaves an unresolved correctness finding for this package.

## Verdict

Correctness and development live-acceptance gate: **pass** after independent
post-fix, focused-test and live-evidence review. Open findings: high 0, medium 0,
low 0. The full pre-handoff pytest sanity run is still running and remains an
explicit separate completion gate; this verdict does not claim it passed.
Final correctness disposition date: 2026-09-16 UTC.
