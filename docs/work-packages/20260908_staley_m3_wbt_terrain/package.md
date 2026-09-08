# Staley M3 WBT Terrain and DEM Resolution

**Status**: Open — scaffold ready for a fresh agent; implementation not started.
**Started**: 2026-09-08 23:30 UTC
**Timezone**: UTC

## Overview

Implement the terrain tooling needed by Staley 2017 M3 in `/workdir/weppcloud-wbt`,
then assess matched catchments at 10 m and 30 m to recommend whether M3 should
require 10 m or support both resolutions. Numerical correctness and DEM
resolution sensitivity are separate acceptance questions.

## Objectives and Scope

- Specify vertical relief, upstream area, routing, elevation source, and units.
- Deliver a registered Rust WBT command with both Python bindings, tests, and
  generated-output evidence from the rebuilt binary.
- Select and document representative catchments; compare identical-input
  reference results separately from resolution effects.
- Produce reproducible measurements, plots, and an evidence-based M3 resolution
  recommendation, including limitations and any remaining uncertainty.
- Update the canonical postfire specification and terrain documentation.

Production Staley NoDb/UI/RQ integration, dashboard implementation, M1 changes,
soil-thickness estimation, deployments, binary vendoring, and live project
mutations are outside this package. This is new terrain tooling and evaluation,
not a faithful extraction of GPL pfdf. Scaffold completion does not satisfy
implementation closeout. Tool registration and wrapper execution are required;
production WEPPpy wiring remains a separate task.

## Stakeholders and Execution

The requesting user owns model availability decisions. The fresh executing
agent implements and evaluates the tooling; independent correctness and security
reviewers assess the final changes. Start with the
[handoff prompt](prompts/active/start_here.md), then execute the
[ExecPlan](prompts/active/staley_m3_wbt_terrain_execplan.md).
Track progress in [tracker.md](tracker.md).

## Success Criteria

- A scientific/CLI contract and parameterization ADR resolve or explicitly
  bound the relief-definition discrepancy before production implementation.
- Synthetic expected values and pinned external-reference comparisons explain
  all material differences in area, relief, and ruggedness.
- Current-binary CLI and both bindings generate correct outputs from fixtures.
- A catchment manifest and reproducible 10 m/30 m study separate routing/source
  effects and report terrain, M3 probability, threshold, runtime, and memory changes.
- A resolution decision report supports 10 m only, both with specified limits,
  or an explicit insufficient-evidence outcome. No unsupported acceptance claim.
- Required validation and independent reviews pass with no open medium/high
  findings. Durable contracts are promoted outside this work package.

## Parameterization ADR Gate

Parameterization change present: **yes**. ADR required: **yes**, draft during
milestone 1 using `docs/standards/parameterization-adr-standard.md`; choose the
next available ADR identifier at execution. Record this user conversation as
decision provenance, user as decision owner, and actual implementer identity.
The user selected WBT ownership and an empirical resolution study, not a final
relief formula, tolerance, or 30 m acceptance policy.

## Security Impact and Review Gate

Security impact: **high** under the repository's default triage for new CLI
file/path handling and Python subprocess bindings. Dedicated security review
required before implementation closeout. Use the existing raster I/O and
wrapper boundaries; no new network service or upload endpoint is in scope.
Create dated correctness and security review artifacts from the repository
templates after implementation, and close medium/high findings. These reviews
are future execution gates, not claims that the documentation scaffold adds an
attack surface.

## Dependencies and References

- `/workdir/weppcloud-wbt/AGENTS.md` and `DEVELOPING_TOOLS.md`.
- [Postfire specification](../../../wepppy/nodb/mods/postfire_debris_flow/specification.md).
- [Terrain investigation](../../../wepppy/nodb/mods/postfire_debris_flow/docs/m3_terrain.md).
- Local `/workdir/usgs-pfdf` reference checkout; GPL source must not be copied
  or translated into the owned implementation or tests.
- Local paper at `wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf`
  in WEPPpy, or `/tmp/staley2017.pdf`; both are optional local availability,
  not redistributable package artifacts. Preserve its existing gitignore policy.

## Deliverables and Follow-up

Deliverables are pending. Evidence locations and runnable steps are assigned
in the ExecPlan. The study informs future production M3 integration; enabling
M3 or changing its user-facing resolution restrictions is not part of this
tooling package. No branch changes, commits, or deployment are authorized by
this scaffold.
