# Post-fire Kf replacement and rainfall-response report

Status: **Complete**. Implementation `d5646ca95`; contract ancestor `9395f4722`.
Restarted forest UI/RQ acceptance, regression and independent reviews passed. Date: 2026-09-16 UTC.

## Purpose and authority

Replace M1's POLARIS/RUSLE nomograph soil input with traceable, USGS-compatible
NRCS fine-earth erodibility (Kf), removing gridded RUSLE as a post-fire debris-flow
dependency. Add a simple probability-versus-rainfall-intensity curve and clarify
modeled versus observed rainfall. Preserve existing WEPPcloud delineation.

Owner requested this scaffold after the Thomas Fire audit. This explicitly
supersedes the audit's recommendation to retain POLARIS as the new-run M1 input;
the closed audit remains an immutable record. The direction is approved; the
exact source/aggregation policy was accepted in checkpoint `9395f4722`.
The original scaffolding turn authorized documentation only. The owner requested
execution on 2026-09-16, authorizing this plan's work and named acceptance scope.
Independent contract reviews passed before runtime implementation;
standalone ancestor checkpoint: `9395f4722`. The owner subsequently authorized completion after the explicit
review/commit request, including those steps. No push is authorized.
Owner's follow-up adds a forest-stack restart and a new M1 end-to-end run on
`nervous-mesquite` to the authorized acceptance scope when this package is
executed. This is not permission to operate the stack during scaffolding or
deploy to other hosts.

## Scope

- A module-owned Kf preparation/aggregation path, generic across supported basins.
  Accept authoritative fine-earth Kf with units, version and lineage; no silent
  Kw, POLARIS, RUSLE K, WEPP Ki/Kr, or fabricated-value substitution.
- Remove RUSLE readiness, fingerprints, UI prerequisites, feature prerequisites
  and queue coupling from new post-fire calculations. Leave standalone RUSLE intact.
- Preserve M3's soil-thickness policy and source behavior; Kf is not an M3 input.
- Duration-linked response curve for accepted M1/M3 predictors, P50 marker and
  saved design-rainfall markers, using the familiar report shell and Unitizer.
- Clear NOAA design-rainfall versus project-climate subdaily provenance, including
  exports. Calendar labels must not imply observed short-window rainfall.
- Additive old/new artifact compatibility, source-specific freshness, tests,
  documentation and independent correctness/security/UX review.

Excluded: changing delineation or slopes, coefficient fitting, exact reproduction
of historical USGS basins, soil-builder changes, landscape recovery, runout,
new rainfall observations, a dashboard redesign, or forced migration of old runs.

## Scientific gate and parameterization ADR

[ADR-0068](../../adrs/ADR-0068-staley-kf-source-replacement.md) records the owner's
accepted direction and scientific details. The checkpoint established the
source product/version, Kf field, horizon selection, component weighting, map-unit
aggregation, units, spatial resampling/support, missing-value rules and any
explicit source hierarchy from primary evidence. Do not inherit M3 thickness
rules as Kf rules. Do not assume a 0–15 cm weighted mean is USGS practice.
Historical Thomas metadata names STATSGO; that does not by itself mandate one
historic product for every future basin. Document what "USGS-compatible" proves
and what remains different. Do not tune toward the Thomas scalar 0.139364.

## Compatibility and regression plan

Keep existing accepted tables, attempts and source provenance immutable and
readable, including POLARIS-backed M1. Label legacy source honestly. New attempts
use Kf; failed replacements preserve old accepted results. Version the predictor
and freshness contracts additively rather than reinterpreting old manifests.
Result column meanings and probability units remain unchanged. Curve reads use
accepted predictors, never current unsaved inputs, and never write run state.
Missing historical rainfall provenance is "not recorded," not inferred observed.

## Complexity and security

Reuse existing source preparation/transport, native geospatial tooling, RQ,
publication, report plotting conventions and Unitizer. Permit bounded module-owned
Kf artifacts and a report extension; no new service, queue, dependency, shared
cache repair or soil rebuild. Prove the simplest supported source path first.
Any larger mechanism requires evidence and renewed scope approval.

Security impact: high for anticipated network/file and queue-boundary changes.
Dedicated security review is required, as are independent correctness and a
dedicated UX review advocating intuitive, uncomplicated human-facing behavior.
Reviews are future implementation gates, not claimed complete by this scaffold.

## Acceptance

New M1 succeeds through the normal workflow on an authorized development fixture
with no RUSLE artifacts or completed RUSLE jobs. Kf values independently reproduce
the chosen source policy; missing or invalid data are explained without silent
fallback. At least two materially different basins establish generic preparation.
M3 and standalone RUSLE are unchanged. Legacy reports remain readable.
The curve agrees with scalar probabilities/P50, responds to duration and units,
has an accessible numeric equivalent, and distinguishes NOAA design markers from
modeled project-climate events. Actual worker/browser generated-output evidence,
not fixtures alone, is required before implementation closure.

Mandatory live acceptance: after implementation and prerequisite checks, restart
the forest development stack using its canonical installed workflow, verify
service health and updated web/worker code, then run M1 on
[nervous-mesquite](https://wc.bearhive.duckdns.org/weppcloud/runs/nervous-mesquite/)
through the normal UI/RQ path. Preserve the prior accepted attempt and a
before/after evidence snapshot. Verify a new accepted Kf-backed manifest and
event/design/inverse parquet publication, independent probabilities, the curve,
labels, exports and reload persistence. Hash protected inputs before/after;
do not rebuild soils, climate, delineation or RUSLE. Do not delete existing
RUSLE data to demonstrate independence; use the separate no-RUSLE fixture.
Retain restart, job and browser evidence. A healthy restart alone is not acceptance.

See [tracker](tracker.md) and [ExecPlan](prompts/completed/kf_report_revisions_execplan.md).

## Completion evidence

All milestones completed on forest; see [tracker](tracker.md),
[validation](artifacts/validation.md), [restart](artifacts/forest_restart_validation.md),
[nervous-mesquite](artifacts/nervous_mesquite_e2e.md) and
[final reviews](artifacts/final_review_disposition.md). Full suite: 8,693 passed,
103 skipped; frontend: 112 suites, 899 tests. No push or production deployment.
