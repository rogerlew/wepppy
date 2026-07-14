# AgFields Management Capacity and Corpus Validation Plan

**Date**: 2026-07-14

**Decision owner**: Roger Lew

**Scope**: Concept 1 and hybrid management synthesis, the
`/workdir/wepp-forest_260430_baseline` hillslope binary, and the AgFields
management-data boundary used to create those inputs.

## Purpose

The routing-suite feasibility census found faithful management graphs containing
21-24 referenced yearly scenarios. The supported `wepp_hill` build accepts only
20. This package now owns the coordinated capacity increase because the limit is
exercised specifically by the Concept 1 and hybrid datasets and cannot be resolved
without validating their complete generated management corpus.

Capacity is only one failure class. Every synthesized Concept 1 and hybrid
management must also parse and complete under the rebuilt binary without a
floating-point trap, invalid producer value, non-finite output, or silent source
substitution. This plan defines how to choose whether a defect belongs at the
AgFields management-data boundary or within WEPP numerical hardening.

## Starting State

The forest worktree is detached at `dac3c950`, tagged
`wepp_260430_original_buggy_dac3c950`. It already contains unrelated uncommitted
soil-layer cursor work in `src/input.for`, corresponding source/release binaries,
one change-log row, one hillslope watchlist row, and an ablation directory. Those
changes are preserved and are not attributed to this package.

The active hillslope include family currently sets all three coupled constants to
20:

- `mxplan` in `src/pmxpln_hill.inc` and its two hill copies;
- `ntype` and `ntype2` in `src/pntype_hill.inc` and its two hill copies.

The makefile compiles `_hill` objects with `src/includes_hill/` and copies those
four build includes into the source root during compilation. The watershed build
uses separate `src/includes_watershed/` values of 15,000. The management reader
uses `ntype` as the upper bound for `nmscen`, while the same constants also size
plant/operation/yearly lookup arrays. A safe change must therefore inventory all
management section counts and not treat `nmscen` as an isolated scalar.

## Compatibility and Regression Contract

This is an additive capacity change. Existing management files with 1-20
scenarios must retain their parsed graph, simulation completion, and accepted
outputs. The Concept 1 planner remains limited to 20 OFEs unless a separate
evidence-backed decision changes that geometry contract; increasing binary
`mxplan` capacity does not increase the routing planner's selected OFE count.

The following invariants are mandatory:

- every retained source and rotation remains represented exactly once according
  to the accepted OFE plan;
- structural deduplication may reuse only reference-safe, equivalent scenario
  graph nodes;
- no field, year, rotation, or scenario is truncated to meet a limit;
- no invalid input is silently clamped, replaced, or converted to Concept 2;
- parser-capacity failures are fixed in the synchronized forest include family;
- objectively invalid database/input values fail with field, source row, value,
  unit, and rule provenance, or are normalized only when an existing canonical
  AgFields/WEPP contract defines the exact transformation;
- finite, contract-valid inputs that create a numerical trap follow
  `/workdir/wepp-forest_260430_baseline/docs/ablation/protocol.md`, beginning with
  an observed baseline and one behavioral change per lane; and
- hillslope PASS files and the watershed binary are built and vendored from the
  same source/release family.

No data schema column, user-visible retention threshold, or scientific management
parameter changes merely to make the executable finish. Any such change requires
an explicit ADR revision and science review.

## Implementation Sequence

First generate both complete deduplicated management corpora from the corrected
Concept 1 and hybrid plans. Record per parent the OFE count and counts for plants,
operations, initial conditions, surfaces, contours, drains, yearly scenarios,
rotations, and any nested cutting/grazing cycles. Parse every serialized file with
WEPPpy and retain hashes plus source-plan identity. The corpus inventory determines
the smallest synchronized hillslope capacity with explicit headroom; 32 is only a
provisional candidate because the currently observed maximum is 24.

Next add forest regression coverage using small real or minimized AgFields
fixtures at the old boundary, the new observed maximum, and one above the accepted
new limit. Update all six canonical/copied hill capacity includes together, plus
README and change-log evidence. Keep the watershed include family unchanged
unless a build/provenance test proves it must change.

Build in an isolated copy first so the existing dirty forest binaries are not
overwritten during diagnosis. Run the capacity fixtures with the current and
candidate binaries and require the expected distinction: current binary rejects
`nmscen > 20`; candidate parses the accepted corpus; both reject a count above the
new explicit bound.

Then execute every unique Concept 1 and hybrid management/input tuple under the
candidate hillslope binary. Classify each nonsuccess as one of:

- `capacity_or_parse`: array/input grammar or reference failure;
- `invalid_input_contract`: a non-finite, out-of-domain, or inconsistent value
  exists before WEPP execution;
- `numerical_model_state`: finite accepted inputs lead to a trap, non-finite
  producer value, or failed model invariant; or
- `environment_or_fixture`: missing/mismatched run resources or binary family.

Fix `invalid_input_contract` at the earliest authoritative AgFields database or
management-ingest boundary when a canonical validity rule exists. For a
`numerical_model_state` failure, initialize a forest ablation incident, add
observability, and promote only a minimal guard or scientifically reviewed
upstream mutation that passes the permanent watchlist and non-regression gates.

Finally rebuild and provenance-stamp a dated forest release, vendor matching
hillslope/watershed binaries into WEPPpy, update WEPPpy's explicit management
capacity guard to the accepted value, and rerun the complete management corpus.
Only then may ADR-0019 become Accepted and production Concept 1/hybrid execution
resume.

## Acceptance Evidence

The capacity/data milestone passes only when:

- the accepted synchronized `mxplan`/`ntype`/`ntype2` value is recorded in
  ADR-0019 with corpus distributions and rationale;
- all forest include copies and WEPPpy's management guard agree;
- the complete Concept 1 and hybrid management corpora serialize and reparse;
- every required hillslope run completes with a valid PASS and no parser/runtime,
  floating-point, non-finite, or invalid-producer signature;
- every input correction has row/value/rule provenance and regression coverage;
- every forest numerical fix has a completed ablation record and fuzzy/watchlist
  evidence;
- existing 1-20 scenario fixtures and protected baseline outputs do not regress;
- forest smoke, full pytest, hillslope watchlist, watershed replay, and ELF gates
  pass; and
- the matching rebuilt binary family is vendored and exercised through WEPPpy.

Large generated corpora and execution workspaces remain under `/wc1` or `/tmp`.
Git contains only concise manifests, minimized fixtures, hashes, distributions,
failure ledgers, and validation summaries.
