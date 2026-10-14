# Observed flow-duration overlay

Status: Closed (local implementation and validation), 2026-10-14. Timezone: UTC.

## Purpose and scope

Add an optional observed streamflow distribution to both GL dashboard daily flow
sources, using the project's Observed upload. Reuse the existing graph renderer,
state, authorized bootstrap and Weibull ranking. No upload format, persisted
NoDb schema, model output, query endpoint, queue or deployment changes.

## Complexity budget

One bounded read-only bootstrap adapter and one optional graph series/control.
Reuse Python csv and DuckDB; no dependencies or infrastructure. Read normalized
observed CSV directly rather than requiring model-fit processing or a fresh query
catalog. Narrow rows are included in existing bootstrap metadata. Validate real
CSV/parquet consumption and browser graph behavior before claiming local completion.

## Security impact and review gate

High (file/path handling): existing authorized dashboard reads another project-local artifact. No new
endpoint or authorization behavior. Validate canonical project containment before
opening CSV and area parquet, including escaping symlinks. Independent contract
reviews and final correctness review are required; retain security assessment in
review artifacts. The dedicated [security review](artifacts/20261014_security_review.md) passes with
zero unresolved findings; [correctness review](artifacts/20261014_correctness_review.md)
also approves.

## Compatibility and regression plan

Additive metadata and optional state only. Existing uploads, comparison CSVs,
NoDb state and WEPP artifacts stay byte-for-byte unchanged. Tests exercise absent,
empty, populated, invalid, legacy and escaping paths on disk, plus independent
ranking, units, controls and renderer wiring. No run artifact schema is mutated.

## Generated artifact validation gate

Applicable: consume Observed-generated CSV and WEPP area parquet to render a
new distribution. Verify normalized CSV semantics (zero-based Julian), finite
positive area, hand-calculated discharge/probabilities and rendered series.
Direct filesystem tests consume actual files; a browser harness exercises the
actual control/loader/renderer. Production deployment is outside this package.
Highest completion claim: locally validated; full Python and frontend gates pass.

## Parameterization ADR gate

New observed conversion and population policy are recorded in ADR-0093.

## Success criteria

Projects with observed streamflow can toggle a single labeled Observed curve on
both source plots. No observed data means existing curves continue unchanged.
Malformed observed data explains failure without hiding simulation curves.
Period, sample count, missing counts, hover and keyboard values remain available.

## Execution

See [ExecPlan](prompts/completed/observed_flow_duration_execplan.md) and
[tracker](tracker.md). User requested scaffold and execution on 2026-10-14.

## Closure notes

Implemented in `4969c7323` after reviewed checkpoint `4e02ee2e0`. Both plot sources
now offer Show observed streamflow when the upload is usable. Full-record ranking,
conversion, missing/invalid data and resource bounds conform to the canonical
contract's Observed streamflow overlay section and ADR-0093. Independent correctness
and dedicated security reviews pass with no unresolved findings.

Validation: 34 focused backend tests, 24 focused graph tests, 986 full frontend
tests, 10,812 broad Python tests passed (126 skipped), and real-project Chromium
readback with 731 observations. See [evidence](artifacts/validation.md) for exact
commands, data hashes, performance, screenshot and the preexisting unrelated
exception-audit limitation. No production deployment or model-output mutation.

Review caught malformed/legacy area types before closeout; strict conversion before
aggregation now has direct real-parquet regression coverage. Full-suite runtime
was 48 minutes, supporting the existing practice of focused tests during iteration.
