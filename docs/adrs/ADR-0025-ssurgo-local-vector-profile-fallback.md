# ADR: SSURGO Recovery, Local Vector-Profile, and Global Fallback Order

Status: Accepted
Date: 2026-07-22
Review Date: 2026-10-22

**Supporting work package:**
[`20260721_ssurgo_intelligent_fallback_study`](../work-packages/20260721_ssurgo_intelligent_fallback_study/)

## Promotion Abstract

The supporting work package inventoried the 2025 gNATSGO raster, ran both
mapped-area and uniform-MUKEY conversion cohorts, classified residual failure
evidence, built deterministic local-candidate raster fixtures, and evaluated
map, terrain, ring, and shallow-profile candidate rules. It also implemented a
read-only padded-raster shadow evaluator that builds candidate MUKEYs under the
same source and converter settings as a run without altering that run.

The study found 244 residual-invalid outcomes in 12,288 mapped-area draws
(1.99%; Wilson 95% interval 1.75%–2.25%) and 49 in 2,048 uniform-MUKEY draws
(2.39%; Wilson 95% interval 1.81%–3.15%). Historical invalidity could not be
reproduced reliably after source/cache/converter drift, so the policy uses only
the current build's recovery result and current candidate buildability.
Geometry, terrain, and strict early-ring rules did not generalize sufficiently
for promotion. A 2 km padded categorical map did establish complete bounded
local context without a national cell scan, and validated shallow-profile
vectors were the first rule with strong, repeatable similarity evidence.

The promotion policy follows directly from those findings: preserve ordinary
source recovery first; only if a raw dominant MUKEY remains invalid, conditionally
build the padded candidate set and choose the closest locally buildable direct
profile; retain the watershed-global donor for every insufficient-evidence
case. In the current-build 50-seed masked-valid cohort, this vector proposal
was strictly closer than the global donor in 29 of 33 directly comparable
cases, tied in four, and never worse. The score is the decision owner's stated
quality objective, not a claim of independently measured downstream WEPP
improvement.

## Context

The gridded SSURGO builder currently replaces every dominant MUKEY that cannot
produce a valid WEPP soil with the watershed's most common valid MUKEY. This
keeps a run executable, but can replace a partly described local soil with an
unrelated watershed-global soil.

Existing SSURGO conversion already has a recovery path: it applies documented
horizon defaults, Rosetta estimates where authorized, field-capacity/wilting-
point sanitization, restrictive-layer handling, and validation before deciding
that a MUKEY is residual-invalid. The fallback must preserve that recovery
behavior and only select a donor after the original MUKEY still fails.

The 2025 gNATSGO study found roughly 2% residual-invalid MUKEYs after this
ordinary conversion. A current-build padded-map study found that a 2 km local
candidate map can be built under identical run settings. On 50 deterministic
masked-valid holdouts, the shallow-profile vector proposal was closer than the
current global donor in 29 of 33 directly comparable cases, tied in four, and
was never worse. The median improvement was 1.95 normalized vector-distance
points (100% median relative reduction). Profile similarity is the decision
owner's accepted quality objective for this policy.

## Decision

Authorize a full production rollout of the ordered policy specified in
[`wepppy/soils/ssurgo/fallback.md`](../../wepppy/soils/ssurgo/fallback.md):

1. retain and complete the existing SSURGO recovery/conversion path for every
   raw dominant MUKEY;
2. for the remaining profile-bearing residual-invalid MUKEYs, select the most
   similar buildable local donor by validated shallow-profile vector distance;
3. use the existing watershed-global valid donor only when recovery or local
   vector selection cannot make an assignment; and
4. retain the separate STATSGO path only when no valid SSURGO soil exists.

The implementation retrieves the full gNATSGO source, materializes a 2 km
padded project candidate map, and builds the added MUKEYs **only when the
primary project build has at least one residual-invalid dominant MUKEY**. Runs
without an affected hillslope retain the current build cost and behavior.

Candidate discovery uses the raw soil-map location and the padded categorical
raster, not watershed or hillslope topology. The final donor is nevertheless
recorded per affected hillslope because a MUKEY can occur in disconnected map
locations.

## Decision Provenance (Required for Parameterization Changes)

Decision Venue: Codex operator session, 2026-07-22 America/Los_Angeles
Participants Present: WEPPcloud operator/user, Codex coding agent
Decision Owner(s): WEPPcloud operator/user
Implementer(s): Codex coding agent

## Change Summary

Old behavior:

- Build MUKEYs from the ordinary project SSURGO map and retain any that pass
  the existing recovery/conversion path.
- Assign every residual-invalid dominant MUKEY to the watershed-global most
  common valid MUKEY.

New behavior:

- Keep the ordinary recovery/conversion path unchanged and preserve the raw
  MUKEY whenever it succeeds.
- Trigger padded-map retrieval and added-MUKEY construction only if one or more
  hillslopes still have residual-invalid dominant MUKEYs.
- Choose a local donor by the approved shallow-profile vector policy where
  sufficient direct source evidence and a buildable local donor exist.
- Use the watershed-global valid MUKEY as the explicit last SSURGO fallback;
  calculate it from valid primary-collection MUKEYs only, never from added
  padded-map candidates.

## Rationale

This order prefers the raster-selected soil, then a locally similar soil with
direct profile evidence, before the broadest available substitution. It adds
no synthetic profile or new source-data repair formula. Conditional candidate
work prevents the normal all-valid watershed from paying for a padded crop or
additional SSURGO build set.

Vector distance is the policy's declared quality objective; it is not claimed
to independently predict an unmeasured WEPP output. Profile-free and
insufficient-evidence failures retain the globally valid continuity path
instead of applying an unvalidated spatial-majority heuristic.

## Alternatives Considered

1. Retain watershed-global substitution for every residual-invalid MUKEY -
   rejected because it discards demonstrated local profile similarity.
2. Build the padded candidate set for every watershed - rejected because most
   runs have no invalid dominant MUKEY and receive no benefit.
3. Use local support alone for profile-free failures - rejected because it has
   no accepted profile-similarity evidence for that failure class.
4. Synthesize a hybrid soil from source and donor fields - rejected because it
   creates a new imputation and WEPP-validity policy.
5. Use terrain or watershed topology in v1 - rejected because neither is part
   of the required candidate contract and neither showed consistent evidence.

## Consequences

Only affected runs incur the padded-raster and additional-build cost. The
candidate collection is separate from primary soils so unused padded MUKEYs do
not become ordinary output soils; selected donors are materialized into the
final run set. Per-substitution provenance makes recovery, local choice, and
global fallback auditable and preserves existing raw/final map contracts.

## Evidence

- Authoritative policy contract:
  [`wepppy/soils/ssurgo/fallback.md`](../../wepppy/soils/ssurgo/fallback.md).
- Active work package:
  [`docs/work-packages/20260721_ssurgo_intelligent_fallback_study/`](../work-packages/20260721_ssurgo_intelligent_fallback_study/).
- Current-build shadow artifact:
  `/tmp/ssurgo_current_shadow_improvident_dyslexia/shadow_evaluation.json`
  (50 holdouts; 29 better, four ties, zero worse among 33 direct comparisons).
- Research tools and tests: `tools/ssurgo_padded_shadow_evaluator.py`,
  `tools/ssurgo_masked_valid_evaluation.py`, and their regression tests.

## Risk and Rollback Notes

An unavailable candidate raster, failed candidate build, profile-free source,
or lack of a comparable local donor must result in the explicit global fallback
with provenance; it must never select an unbuilt donor or a silent alternate
algorithm. A missing native categorical-support dependency is an explicit
build error.

Rollback disables local vector selection and restores the existing
watershed-global substitution after ordinary source recovery. Existing runs
retain their assigned soils and provenance. Any change to the field set,
accepted ranges, radii, normalization, or tie order requires an ADR amendment
or successor.

## Implementation Notes

Implement the contract in `wepppy/soils/ssurgo/fallback.md`, with deterministic
tests for all three policy stages, conditional candidate construction, ties,
legacy hydration, and generated-artifact propagation.
