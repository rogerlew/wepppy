# Extract GL dashboard tooltip formatting

## Purpose and milestones

In wepppy/weppcloud/static/js/gl-dashboard/map/layers.js, createLayerUtils supplies the tooltip callback used by the map. First characterize returned text through that factory, including overlapping layers and missing values. Then extract shared value readers and ordered feature, RAP and raster formatting while preserving the factory's public methods. Finally exercise the same inputs against both revisions, run frontend tests and measure each changed module.

## Progress

- [x] 2026-11-23 UTC. Inspected the public interface and measured the baseline.
- [ ] Extract and wire formatting.
- [ ] Verify behavior and record local integration readiness.

## Surprises & Discoveries

The layer file has 1,604 source lines. ESLint measures formatTooltip at complexity 155. The next largest function scores 21.

## Decision Log

Keep picking order explicit. Yearly channel results precede regular channel results, and coordinate sampling follows feature lookups. Preserve units, decimal precision and null handling from the existing implementation.

## Validation and recovery

From the repository root run wctl run-npm lint and wctl run-npm test. Inspect the focused gl-dashboard tests and invoke createLayerUtils from the candidate browser modules. Measure complexity with ESLint's complexity rule. Revert the local merge to roll back the extraction as a unit.

## Outcomes & Retrospective

Pending execution.
