# Final segment-summary correctness review

## Verdict and scope

**PASS for the reviewed implementation.** No unresolved high or medium
correctness findings remain. Package-wide validation and operational evidence
remain separate closeout gates; this is not deployment approval.

Reviewer: independent `accounting_contract_review` agent, 2026-10-22.
Contract ancestor: `bac3042b1`. Runtime files and tests were read only. The
reviewer authored this artifact and the earlier contract-review artifact, but
did not implement the producer or its correction.

Reviewed `wepppy/nodb/mods/roads/_segment_loss_summary.py`, the Roads facade,
source-summary and controller tests, native geometry/PASS compatibility and
actual isolated UM1 artifacts against the
[approved contract](../../../schemas/roads-segment-loss-summary-contract.md).
Publication/access security has a separate
[review](20261022_security_review.md).

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| COR-01 | Medium | The facade eagerly loaded model/climate state before detecting an empty or skipped/failed-only manifest. A real empty-manifest call failed on missing wepp.nodb, violating the empty-state contract. Helper-only tests missed this. | Resolved: a lazy execution-calendar provider is called only for populated records. An actual facade probe and all three empty-state facade regressions pass without creating model or climate state. |
| TEST-01 | Test fixture | The first COR-01 regression attempted to create a directory already created by Roads initialization. | Resolved with exist_ok=True; the targeted suite now passes. This was not a runtime failure. |

No other high/medium equation, source-attribution, scope, calendar or metadata
defect was confirmed in the reviewed code.

## Accounting assessment

The reducer selects original PASS rows by completed manifest native ID, without
reading receiving-hillslope loss. It validates required metrics before SQL sums,
then computes the six annual extensive quantities using persisted execution
duration. Full native WAT geometry supplies modeled area. Derived depths,
densities and delivery ratio use that same area and annual masses; final
nonfinite results fail before publication.

Expected year range/count, per-year 365/366 coverage, unique julian/simulation
days, global simulation-day continuity, equal profile calendars and PASS/WAT
date equality are checked. Native geometry supplies OFE topology/stationarity
and required WAT identity validation. CLI calendar semantics are retained.

Remainder scope precedes multi-OFE scope, followed by proven single-OFE inslope
scope and explicit unclassified scope. Full-profile values remain available
while unsupported aliases are NULL. Signed detachment/deposition are retained;
nonpositive detachment yields NULL delivery ratio and positive ratios above one
are not clipped. Original columns/types/order remain, with provenance appended.
Policy, consumed source hashes, manifest hash, annual basis and alias limits are
schema metadata, without field-unit changes to CSV headers.

## Independent execution

The reviewer ran the full focused command after the runtime fix. Its 26 producer
tests passed before the newly added facade test stopped on TEST-01. After the
fixture correction, the following focused command passed:

```text
wctl run-pytest \
  tests/nodb/mods/test_roads_segment_loss_summary.py::test_actual_facade_empty_without_model_or_climate_state \
  tests/nodb/mods/test_roads_controller.py::test_build_roads_segment_loss_summary_delegates_execution_calendar \
  --maxfail=1 -q
4 passed, 2 existing dependency deprecation warnings, 9.07 seconds
```

The earlier author-run full focused log records 73 passes before the three new
empty-facade cases were added. The package owner is rerunning the complete final
focused suite and broad gates; this artifact does not misrepresent those as
reviewer-run results.

Additional real-runtime probes used `wctl exec -T weppcloud python -`, native
geometry, DuckDB and PyArrow, with no numerical kernel stubs:

- Negative detachment/deposition survived with their signs; delivery ratio was
  NULL for negative detachment.
- A valid ratio of 62.5 remained 62.5.
- A multi-OFE remainder retained replacement_remainder scope and full area.
- Missing populated execution duration raised ValueError.
- Legacy WAT OFE column spelling was accepted by the native geometry path.
- A nonstationary OFE area raised the native ordinary error.
- The corrected actual facade produced zero rows with neither wepp.nodb nor
  climate.nodb present or created.

Scratch evidence remains in the local container under
`/tmp/segment-accounting-probes-1_p90pht` and
`/tmp/segment-review-empty-fixed-jnk5y9gc`. These are scratch observations, not
committed fixtures.

## Independent UM1 readback

Read the actual generated summary in
`tests/wepp/interchange/fixtures/roads-accounting-scratch/um1-restored` and
independently recomputed every row from original UM1 PASS/WAT data using Pandas
and NumPy, separate from the DuckDB producer. Confirmed:

- 34 rows covering native sources over 2000-2015, with simulation_years=16.
- Sediment export sum: 4,810.818379721261 kg/year.
- Runoff volume sum: 1,008.0648908316255 cubic meters/year.
- Source 900001 export: 4,071.013295042149 kg/year.
- Full modeled profile area sum: 4,127.15 square meters.
- All six annual quantities agree with original source sums within
  rtol=1e-10 and atol=1e-9. Largest observed absolute difference was
  2.7284841053187847e-12 in annual baseflow volume.
- Every area, area-normalized quantity and proven-road prism alias agrees;
  all buffer aliases are NULL and all UM1 profile scopes are road.
- Both consumed Parquet hashes and the manifest hash match current files.

The generated summary SHA-256 is
`68fa7acb7c2786efa83d0e24eaeeca1fa070d955a4ca41603be9cce66b910dc2`.
The author's retained [validation script](validate_um1.py) and local receipt
`/tmp/roads-segment-um1-validation.json` report 216 protected scratch artifacts
and 46 original Parquets unchanged, under uid 1000/gid 993. The reviewer inspected
that receipt and verified current numerical artifacts, but did not independently
repeat its before/after hash observation or the controller regeneration.

## Fingerprints and residual limits

| Reviewed source | SHA-256 |
| --- | --- |
| _segment_loss_summary.py | `ec7748c28f68415bafa5fddf73d38196d27f0906d6ba6573cc294f821878f097` |
| roads.py | `4c371d014710f34c4355ee963d8a120c941645f832a6440eb31108581dcd6772` |
| test_roads_segment_loss_summary.py | `6821fc5b52966615ce2842dadf9ef050684e0b082e6e3cf16fa2d5500ee94453` |
| test_roads_controller.py | `811829b87eb07129d4a458ed5010e9cb512043d5306f9045a9e25f96a92db88d` |

No native source or binary change is required. Shared native geometry behavior
is used as an existing dependency, not recertified in full here. Real UM1 covers
single-OFE inslope profiles; replacement/MOFE, empty and malformed states rely
on focused real-boundary tests and the independent probes above.

This review does not certify live browser authorization, canonical archive and
restore, process-crash recovery, production identity/mount parity, or a general
performance bound. The security/artifact-observability review and package owner
must retain their required workflow evidence and final broad-gate results before
closure. This diagnostic remains original profile export, not incremental road
effect or routed watershed-outlet yield.
