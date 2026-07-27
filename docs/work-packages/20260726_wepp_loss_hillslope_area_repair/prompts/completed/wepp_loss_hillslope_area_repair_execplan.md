# Repair annual WEPP LOSS hillslope parsing and publish the native release

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, WEPPpy can post-process watershed LOSS files whose annual
hillslope rows include `Hillslope Area`, as production WEPP currently emits.
The native interchange produces a typed additive area column without shifting
pollutant values, and all downstream consumers continue to operate.

## Progress

- [x] (2026-07-27 04:19 UTC) Confirmed the incident row, running release hash,
  and parser mismatch.
- [x] (2026-07-27 04:19 UTC) Scaffolded the work package and compatibility plan.
- [x] (2026-07-27) Audited WEPPpy consumers and legacy fixture shapes.
- [x] (2026-07-27) Implemented the strict annual schema correction and regressions.
- [x] (2026-07-27) Validated consumers against generated parquet.
- [x] (2026-07-27) Built and validated the canonical py312 release artifact.
- [x] (2026-07-27) Completed dual independent reviews and dispositioned findings.
- [x] (2026-07-27) Finalized docs, pushed WEPPpyo3, and closed the package.

## Surprises & Discoveries

- Observation: The production worker already uses the current committed
  WEPPpyo3 release artifact.
  Evidence: The production and local py312 extension SHA256 values both equal
  `de0c1bdc8cc5e5e0ccebb8b1b6bbfe1b519c9746601721a62f42a96774b5b18f`.
- Observation: Production annual rows and average annual rows share a 12-field
  layout, but only the average printed header names `Hillslope Area`.
  Evidence: Incident `loss_pw0.txt` lines 550 and 5921 contain `1.539` at the
  area position; the average table labels that position `(ha)`.
- Observation: Historical WEPP annual rows contain 11 fields and remain
  regenerable through the migration path.
  Evidence: The historical integration fixture converts with true null area.
- Observation: Per-row dual-width acceptance is unsafe because a truncated
  current row can resemble a legacy row.
  Evidence: Review required file-wide layout detection and mixed-width failure.

## Decision Log

- Decision: Add `Hillslope Area` to the annual Arrow/parquet schema.
  Rationale: It is real model output with an established average-table
  contract. Dropping it would lose data and require special positional parsing.
  Date/Author: 2026-07-27, Codex.
- Decision: Keep exact row-width validation.
  Rationale: Accepting arbitrary widths could silently shift pollutant values.
  Date/Author: 2026-07-27, Codex.

## Outcomes & Retrospective

The parser now accepts one uniform annual layout per file: historical
11-field rows receive a true null area, while current 12-field rows retain the
hectare value. Other and mixed widths fail explicitly. The rebuilt artifact is
pushed in WEPPpyo3 commit `cee6ff1`; its SHA256 is
`faa9173665aee64e92ce077488121cc21b7a1cc06cb771b280df81c7862299f1`.
All targeted gates and both independent reviews passed. No production consumer
required a source change because existing reads are named-column or use the
unchanged average table.

## Context and Orientation

`wepppyo3/wepp_interchange/src/loss.rs` owns the text parser and Arrow schemas.
`HILL_HEADER` describes annual hillslope rows and currently has 11 fields;
`HILL_AVG_HEADER` has 12 and includes `Hillslope Area`. The canonical deployable
extension is
`wepppyo3/release/linux/py312/wepppyo3/wepp_interchange/wepp_interchange_rust.so`.
WEPPpy calls it from
`wepppy/wepp/interchange/watershed_loss_interchange.py`.

## Plan of Work

Inventory all fixture layouts and all WEPPpy reads of the annual hillslope
parquet. Correct the annual header and units using the established average
field name and position. Normalize the explicit historical 11-field layout
with a null area and accept the corrected 12-field layout; reject every other
width. Add incident-derived assertions for schema order, units, area, and
pollutant values. Update consumers only where they make strict or positional
assumptions.

Run Rust formatting and crate tests. Build the py312 extension using the
repository's canonical release procedure, update release provenance, and
validate the copied shared object by importing it and converting the fixture.
Run relevant WEPPpy consumer tests.

Independent code and QA reviewers then inspect source, binary provenance,
consumer compatibility, and regression sufficiency. Every finding receives a
fix, evidence-backed rejection, or explicitly owned follow-up before closure.

## Concrete Steps

From `/home/workdir/wepppyo3`:

    cargo fmt --check
    cargo test -p wepp_interchange

Use the canonical build command discovered in repository documentation, then
import the copied py312 extension and run the native fixture conversion.

From `/home/workdir/wepppy`:

    wctl run-pytest <relevant interchange and consumer tests>
    wctl doc-lint --path docs/work-packages/20260726_wepp_loss_hillslope_area_repair

## Validation and Acceptance

Acceptance requires generated parquet from the rebuilt extension, not only Rust
unit tests. The annual schema must include the area value at the correct
position, existing pollutant values must retain their names, and audited
WEPPpy consumers must pass.

## Idempotence and Recovery

Rust builds are repeatable and only replace the canonical release shared object
after tests pass. The source and release artifact are committed together.
Generated test output uses temporary directories. No production mutation is
performed.

## Artifacts and Notes

Production incident:

    run: mdobre-foursquare-fovea
    job: e1598864-a1e5-40f6-9cd4-25bbf55afe67
    file: /wc1/runs/md/mdobre-foursquare-fovea/wepp/output/loss_pw0.txt
    line: 550

## Interfaces and Dependencies

No new dependency is required. The public Python function
`watershed_loss_to_parquet` remains unchanged. The annual hillslope parquet
schema evolves additively by one `Float64` field with `ha` units.
