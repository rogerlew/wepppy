# ADR-0068: Replace M1 RUSLE K with traceable fine-earth Kf

Status: Accepted source and report policy after independent reviews, 2026-09-16.
Date: 2026-09-16 UTC. Implementation: wired; restarted forest acceptance passed (final regression closeout in package).

## Decision provenance

Venue: owner/assistant repository conversation, 2026-09-16 UTC (exact time not
recorded). Participants: repository owner and Codex. Decision owner: repository
owner. Implementer: Codex, after owner execution/completion authorization.

Owner direction: replace RUSLE K with stricter USGS Kf; gridded RUSLE is no
longer to be a post-fire debris-flow dependency. Add an intensity-response curve
and preserve existing delineation. The initial request was scaffold-only; subsequent owner instructions explicitly
authorized execution, required reviews/commits, stack restart and a named end-to-end run.

## Context and evidence

ADR-0059 selected POLARIS nomograph K. The Thomas audit independently verified
the equations but found K=0.337162 versus historical USGS Kf=0.139364; at the
same rainfall, probabilities were 85.63% and 69.35%. Geometry and terrain inputs
also differ. This does not prove which probability is better calibrated.
See [audit](../work-packages/20260916_thomas_fire_verification/artifacts/findings.md).

## Decision direction

For future M1 calculations use authoritative NRCS fine-earth Kf with traceable
source/units and explicit aggregation. Do not substitute whole-soil Kw, POLARIS
nomograph/EPIC, WEPP erodibility or a reference basin scalar. Remove gridded
RUSLE readiness/dependency from new post-fire calculations while preserving
standalone RUSLE. M3 thickness science is unchanged. Existing accepted runs stay
readable and retain their recorded source; no silent numerical migration.

This direction is intended to supersede ADR-0059's new-run K-source choice once
the scientific/contract checkpoint is accepted. It does not claim deployed
replacement or redefine legacy manifests today.

## Details required before acceptance and implementation

Establish source product/version/field and allowed hierarchy, horizon selection,
component/map-unit weighting, units, spatial alignment, missing/invalid treatment,
common support and provenance/freshness. Use primary evidence and independently
reproduced fixtures. Thomas XML names STATSGO; do not assume it proves a universal
SSURGO or 0–15 cm depth recipe. Kf strictness is not a new M3 horizon restriction.
Ratify these details in this ADR and affected canonical contracts before code.

## Alternatives and rationale

Retaining POLARIS plus warnings was the audit's initial recommendation; the
owner now chooses a Kf replacement to align the scientific variable and remove
RUSLE coupling. Reconstructing Kf from POLARIS, silently using Kw, or tuning K to
match Thomas would defeat that purpose. Redelineation and coefficient fitting
are excluded because the package changes input provenance, not basin conventions
or model calibration.

## Risks and rollback

Kf availability/aggregation may limit coverage; do not mask this with fallback
estimates. New results will change and require versioned provenance. Legacy
results must remain visible if preparation fails. Keep replacement additive and
attempt-local; no shared soil changes or automatic reruns. No exact historical
USGS probability or predictive-calibration claim follows from source replacement.

Execution: [work package](../work-packages/20260916_postfire_kf_report_revisions/package.md).

## Execution research and proposed detailed policy — 2026-09-16

The owner requested execution of the package. Source research is complete enough
to propose the following policy; independent reviews and the ancestor checkpoint
remain pending. Implementation has not started. The owner authorized completion after the
explicit independent-review/checkpoint-commit request, including those steps
and the named forest restart/end-to-end run. The original scaffold-only
statement above describes its authoring turn.

Select the USGS 2025 KFFACT COG from NRCS-derived USSOILS 1995, release
10.5066/P13WAPYV, policy `statsgo_kffact_1995_cog2025_v1`. Use the publisher's
all-recorded-layer thickness weighting and component-percentage weighting,
excluding missing values at each level and renormalizing. Do not impose a
0–15 cm rule or substitute current SSURGO, whole-soil Kw, or M3 thickness science.
The [canonical proposal](../../wepppy/nodb/mods/postfire_debris_flow/docs/kf_source.md)
fixes endpoint, limits, missing-value handling, schema and source freshness.

The COG's conductivity/inches-hour metadata conflicts with its original KFFACT
field identity. Original USGS aggregation metadata distinguishes KFFACT from
PERM, and independent comparison finds exact float32 equality with original
polygon KFFACT in 301,379 cells across two regions. Interpret values unchanged
as customary USLE fine-earth Kf; retain and explain the conflicting metadata.
This conclusion is local evidence, not publisher confirmation. The evidence
and reproducible probe are in the package's `artifacts/kf_source_policy.md`.

Align nearest-neighbor to the existing project grid and calculate S on existing
M1 common-valid support. This preserves source values while retaining established
support policy. Reject invalid values rather than interpolate, gap fill or tune
toward the historical Thomas scalar. The research mean 0.139396 on saved legacy
support is a validation observation, not an acceptance target or runtime input.

Prepare Kf within each model attempt instead of adding a shared cache/pointer.
The bounded extra acquisition is simpler than a second activation/freshness
state machine and retains complete provenance. Reuse existing fixed-source
transport with the new allowlisted endpoint; M3 transport behavior stays intact.

For the report, adopt `response_curve_v1`: 101 uniform samples plus exact saved
design/P50 values, with range reaching all markers and a finite available 99%
equality. A 1 mm/hour floor defines a visible degenerate axis. These are explicit
presentation choices, not fitted parameters, new design storms or hazard cutoffs.
The [report amendment](../ui-docs/contracts/postfire-debris-flow-report-contract.md#kf-response-curve-and-rainfall-provenance-amendment--2026-09-16)
retains scalar unavailable/nonunique/negative-response semantics and limits the
payload to 106 points. No coefficient or probability-unit changes.

## Checkpoint acceptance

2026-09-16: owner-authorized completion, source evidence, canonical amendments
and independent correctness/security reviews ratify the detailed policy above.
Both reviews have zero unresolved findings. Implementation conformance and live
acceptance remain pending; the standalone checkpoint precedes runtime edits.
