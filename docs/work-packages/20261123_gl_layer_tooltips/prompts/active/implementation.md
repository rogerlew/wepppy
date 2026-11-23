# Extract GL dashboard tooltip formatting

## Purpose and milestones

In wepppy/weppcloud/static/js/gl-dashboard/map/layers.js, createLayerUtils supplies the tooltip callback used by the map. First characterize returned text through that factory, including overlapping layers and missing values. Then extract shared value readers and ordered feature, RAP and raster formatting while preserving the factory's public methods. Finally exercise the same inputs against both revisions, run frontend tests and measure each changed module.

## Progress

- [x] 2026-11-23 UTC. Inspected the public interface and measured the baseline.
- [x] 2026-11-23 UTC. Extracted and wired the shared readers and tooltip formatter.
- [ ] Verify behavior and record local integration readiness.

## Surprises & Discoveries

The layer file has 1,604 source lines. ESLint measures formatTooltip at complexity 155. The next largest function scores 21.

## Decision Log

Keep picking order explicit. Yearly channel results precede regular channel results, and coordinate sampling follows feature lookups. Preserve units, decimal precision and null handling from the existing implementation.

## Validation and recovery

From the repository root run wctl run-npm lint and wctl run-npm test. Inspect the focused gl-dashboard tests and invoke createLayerUtils from the candidate browser modules. Measure complexity with ESLint's complexity rule. Revert the local merge to roll back the extraction as a unit.

## Outcomes & Retrospective

The public factory now delegates hover formatting to layer-tooltips.js. Named helper keys remain available to consumers. The original file fell from 1,604 to 1,279 source lines and its peak complexity fell from 155 to 21. The tooltip and value modules measure 165 and 48 source lines, with peak complexity 10 and 11 respectively.

All 1,110 Jest tests and nine Node tests passed. A Chromium replay compared 410 tooltip strings from the baseline and candidate factories across run and batch modes. Inputs covered missing, zero, numeric, numeric-string and invalid values, yearly and event dates, RAP cumulative mode and scalar datasets. A Jest regression exercises priority among overlapping channel, event, OpenET and tile values.
