# Close peak-flow Gate 2.1 assurance gaps

This ExecPlan is a living document. Maintain `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a reviewer can run one command and verify that WEPP records
the solver it actually called, emits complete event packets, applies the
published APPMTH validity ranges, preserves canonical output while tracing is
active, and reproduces both selected peaks in a separate process. This plan
does not run or authorize the Topanga census.

## Progress

- [x] (2026-08-08 21:55 UTC) Convert review findings into a bounded package.
- [x] (2026-08-08 21:53 UTC) Push the initial WEPP-Forest observer branch.
- [x] (2026-08-08 22:35 UTC) Correct and push the observational source at `ea25ad79`.
- [x] (2026-08-08 22:41 UTC) Publish strict packet and replay-report schemas and conforming build manifests.
- [x] (2026-08-08 22:44 UTC) Correct APPMTH domain calculations and add closed-boundary tests.
- [x] (2026-08-08 22:51 UTC) Demonstrate active tracing byte parity for both Ksat lanes.
- [x] (2026-08-08 22:53 UTC) Run the one-command acceptance workflow, including 1986 fixtures and inactive control.
- [x] (2026-08-08 22:55 UTC) Pin full-precision expected packets/replays and regenerate evidence.

## Surprises & Discoveries

- Observation: Phase 1 exact replay proves packet sufficiency only for the two
  simple continuous-event paths; the logged solver label was inferred from
  `tp(2)` rather than captured at each actual call.
  Evidence: Gate 2.1 review finding 1.
- Observation: current WEPP-Forest requires the binary `.hbp` hillslope-pass
  artifact; the Phase 1 fixture still requested retired `.pass.dat` output.
  Evidence: the pinned build stopped before completing year one until all
  three fixture lanes were migrated consistently to `H106.hbp`.

## Decision Log

- Decision: the final pushed WEPP-Forest feature-branch commit will be the new
  observer source authority.
  Rationale: this removes ambiguity between an operational branch and a
  generated patch against an older private commit.
  Date/Author: 2026-08-08 / Codex.
- Decision: acceptance will regenerate evidence in temporary directories and
  compare semantic JSON plus canonical hashes, rather than trusting committed
  result files as inputs.
  Rationale: the checker must detect stale or incomplete artifacts.
  Date/Author: 2026-08-08 / Codex.

## Outcomes & Retrospective

Gate 2.1 remediation is complete and accepted. The acceptance report records active-trace
parity in both 1980 lanes, exact selected-method replays, strict schema
validation, the 1986 anomalies, and the inactive control. Phase 2A is now
authorized under the separate review disposition; no census work was run by
this remediation package.

## Context and Orientation

WEPP selects `APPMTH` or `HDRIVE` in `src/irs.for` through several branches:
breakpoint mode, the `apr` flag, model mode, and the `tp(2)` test. The current
observer logs a method inferred only from `tp(2)` and writes the result before
the minimum-peak clamp. WEPPpy's `tools/peakflow_phase1_replay.py` packetizes
the trace and invokes a standalone Fortran driver. The existing schemas live
under `docs/work-packages/20260808_peakflow_phase1/artifacts/schemas/`.

## Plan of Work

First revise WEPP-Forest so each actual solver call assigns a method code next
to the call. Move result logging after the minimum-peak clamp. Emit scalar and
forcing records for runoff events without surplus, distinguish all five
assignment modes, and capture raw `surdra`, adjusted `surpls`, and runoff on
both sides of water-balance reconciliation.

Then tighten WEPPpy's packet identity and forcing fields, add strict schemas
for packets and replay reports, and make both build manifests conform. Compute
`vstar`, `tstar`, and `qpstar` with the documented closed intervals. Finally
create one acceptance entry point that verifies binaries, runs active and
inactive parity, packetizes, validates, replays, checks full-precision expected
values, and runs the 1986 and inactive-control fixtures.

## Concrete Steps

Work in `/workdir/wepp-forest_260430_baseline` for Fortran and
`/workdir/wepppy` for contracts and acceptance tooling. Build WEPP-Forest with
the pinned GNU compiler in an isolated source copy so generated includes and
binaries do not dirty the shared checkout. Run WEPPpy tests through `wctl`.

## Validation and Acceptance

The acceptance command must fail if any solver label is inferred incorrectly,
any active canonical output differs, any artifact violates its schema, any
packet hash changes unexpectedly, either selected replay differs from the
post-clamp peak, or any fixture/control result changes beyond its declared
tolerance. Boundary tests cover each documented domain endpoint and a value
immediately outside it.

## Idempotence and Recovery

All runs occur in temporary directories. Authoritative `/wc1` inputs remain
read-only. The unrelated dirty WEPPpy RQ files remain unstaged. The shared
WEPP-Forest checkout must be clean after its remediation commit.

## Artifacts and Notes

Generated Gate 2.1 evidence will live under this package's `artifacts/` and
will identify the final pushed observer commit and executable hashes.

## Interfaces and Dependencies

Use existing Python standard-library tooling plus the repository's pinned
`jsonschema`. The observer remains fixed-form Fortran and must not make shadow
solver calls. The standalone replay remains a separate operating-system
process receiving an immutable packet.

## Revision Note

Initial plan authored 2026-08-08 from the conditional Gate 2.1 review.
