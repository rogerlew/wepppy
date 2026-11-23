# Extract GL dashboard tooltip formatting

## Purpose and milestones

In wepppy/weppcloud/static/js/gl-dashboard/map/layers.js, createLayerUtils supplies the tooltip callback used by the map. First characterize returned text through that factory, including overlapping layers and missing values. Then extract shared value readers and ordered feature, RAP and raster formatting while preserving the factory's public methods. Finally exercise the same inputs against both revisions, run frontend tests and measure each changed module.

## Progress

- [x] 2026-11-23 UTC. Inspected the public interface and measured the baseline.
- [x] 2026-11-23 UTC. Extracted and wired the shared readers and tooltip formatter.
- [x] 2026-11-23 UTC. Checked behavior, measured complexity and exercised the served dashboard.

## Surprises & Discoveries

The layer file has 1,604 source lines. ESLint measures formatTooltip at complexity 155. The next largest function scores 21.

## Decision Log

Keep picking order explicit. Yearly channel results precede regular channel results, and coordinate sampling follows feature lookups. Preserve units, decimal precision and null handling from the existing implementation.

## Validation and recovery

From the repository root run wctl run-npm lint and wctl run-npm test. Inspect the focused gl-dashboard tests and invoke createLayerUtils from the candidate browser modules. Measure complexity with ESLint's complexity rule. To roll back the extraction after integration, revert the merge with its first parent as mainline.

## Outcomes & Retrospective

The public factory now delegates hover formatting to layer-tooltips.js. Named helper keys remain available to consumers. The original file fell from 1,604 to 1,279 source lines and its peak complexity fell from 155 to 21. The tooltip and value modules measure 165 and 48 source lines, with peak complexity 10 and 11 respectively.

All 1,110 Jest tests and nine Node tests passed. A Chromium replay compared 410 tooltip strings from the baseline and candidate factories across run and batch modes. Inputs covered missing, zero, numeric, numeric-string and invalid values, yearly and event dates, RAP cumulative mode and scalar datasets. A Jest regression exercises priority among overlapping channel, event, OpenET and tile values.

The served dashboard check loaded all three candidate map modules in Chromium on the local development server. Thirteen repository layer cases passed, and three skipped after checking available project data. A separate check selected canopy cover, passed an actual project feature to Deck's registered getTooltip callback, and compared its full output with the selected summary row.

    Layer: landuse/landuse.parquet
    TOPAZ ID: 9511
    cancov: 0.900

The two complementary pytest segments cover all 15,510 selected cases. The first completed 257 modules (4,360 passed and 157 skipped during execution). The continuation collected the remaining 10,993 cases (10,604 passed, 388 skipped during execution and one failure). Pytest also reported one collection skip and 99 deselections. The completed-module list came from the first log and excluded its failing module so the continuation exercised that module in full. Candidate worktree receipts are 5feead9443114a5aa5e800139eed83b1 and 0e1b5a2234e046c5bc1b28a948b1b9a5.

The isolated runner used a local test image compatible with master, the pinned native interchange package, a temporary volume with sufficient free space, and a regular path for the WhiteboxTools executable. These settings applied only to the disposable tests.

The remaining failure, test_adduser_errors_when_user_unknown, also failed on the original master b464937eb in isolation (baseline receipt 7c9e7cef246b4e1f8729f1dc70d41689). The assertion expects “WeppCloud” and the route returns “WEPPcloud.” The layer refactor passed its local acceptance checks.
