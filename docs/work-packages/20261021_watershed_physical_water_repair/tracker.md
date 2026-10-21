# Watershed physical water repair tracker

## Status

Scaffolded 2026-10-21 21:53 UTC; execution pending. Audit checkpoint:
`e85d582ed`. Operator requested commit and scaffold only. No repair experiment,
production source change, new binary, push or deployment has been performed.
Security impact low; no dedicated security review required for the present scope.

## Task board

- [x] Commit the completed physical audit and four defect reproductions.
- [x] Define repair scope, acceptance matrix, compatibility and scientific gates.
- [ ] M1: portable failing regressions, proposed scientific contract, ADR and reviews.
- [ ] M2: isolated WPA-04, WPA-03, WPA-02 and WPA-01 repair lanes with measured effects.
- [ ] M3: combined full-period accounting, all affected routing paths and independent storage/rate checks.
- [ ] M4: full native regressions, correctness/QA reviews, documentation and release-readiness handoff.

## Decisions

2026-10-21: Preserve closed audit history and keep Ash outside this package.
Use native default branch first; the HBP development checkout is not the repair
baseline. Retain 261021 and all historical outputs. Do not interpret scaffolding
as implementation/release authority or request an unnecessary approval during it.

2026-10-21: Repair one failure mechanism per lane. Establish groundwater and
soil allocation first, then source reconstruction and channel assembly, and
replay their combination. Aggregate improvements cannot excuse individual
regressions or hide error cancellation.

2026-10-21: A zero printed channel balance is not sufficient. Closeout requires
independent rates, volumes and storage; unresolved residuals block repaired-routing
acceptance even if all four narrow regression tests pass.

## Risks and open scientific decisions

Flat hydrographs can have mutually inconsistent volume, peak and duration.
Record the authority/timing choice before implementation. Channel-local losses
need available-water accounting without fabricated negative hydrographs or
rescaling unrelated source support. Negative soil infiltration must not remove
more water than exists. Groundwater initialization must not leak state between
hillslopes or reset at ordinary year boundaries.

The previous audit’s donors are private and its initial/interception stores
incomplete. Portable failure fixtures and complete control-volume observations
are M1/M3 work, not already-met acceptance. Field calibration, contour and tile
coverage are distinct from ordinary-case conservation.

## Validation and handoff

Scaffold checks: scoped Markdown lint, links, spelling, whitespace and root guide
size. No native/application tests are warranted for this documentation-only
turn. Future execution commands and required outputs are in the active ExecPlan;
review status must remain pending until independent reviews actually occur.

Next action on execution authorization: resolve native `origin/HEAD`, freeze
baseline source/input/binary identity, and establish M1 portable failing tests
and the proposed ADR. Do not start by changing routing formulas.

Scaffold validation passed: four package Markdown files and project board lint
with zero errors/warnings; local links resolve, spelling preview unchanged,
whitespace clean, root AGENTS remains 160 lines. Implementation remains pending.
