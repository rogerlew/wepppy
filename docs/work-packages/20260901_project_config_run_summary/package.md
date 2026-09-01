# Project Config Run Summary

**Status**: Closed (2026-09-01)
**Timezone**: UTC

## Overview

Config Builder runs currently expose the project projection in the run-page
header but do not give users an equally quick view of the configuration choices
that govern the run. This package adds an effective-locale pill beside the
projection pill and a read-only Config Summary modal under the More menu for
`/weppcloud/runs/<runid>/config/` pages.

## Objectives

- Show the run's effective Config Builder locale beside the projection pill.
- Present Locale, Delineation Backend, Representation, DEM Data Source, Cell
  Size (m), and CLIGEN Database in an accessible summary table.
- Derive every displayed value from the effective run configuration/runtime
  authority without mutating project state or silently substituting Builder
  defaults.
- Cover populated, legacy/absent, and malformed states with explicit rendering
  behavior and regression evidence.

## Scope

### Included

- The fixed run header used by the Config Builder run page.
- A More-menu launcher and accessible, read-only Config Summary modal.
- A server-side presentation model for the six requested values.
- Focused route/template tests, frontend accessibility checks, user-facing
  documentation, and correctness/UX review evidence.
- A contract-first checkpoint and canonical UI contract amendment before
  implementation.

### Explicitly Out of Scope

- Changing project configuration, locale authority, defaults, providers, model
  parameterization, or persistence formats.
- Adding an API or client-side fetch solely for the summary.
- Changing report-page headers or non-Config-Builder run pages unless the
  approved contract explicitly broadens the surface.
- Renaming canonical locale, dataset, backend, or representation identifiers.

## Stakeholders

- **Primary**: Config Builder users reviewing an existing run
- **Reviewers**: WEPPcloud UI/correctness reviewer and contract reviewers
- **Security Reviewer**: Dedicated artifact not required; final correctness
  review verifies authorization and escaping noninterference
- **Informed**: Project Config maintainers

## Success Criteria

- [x] A Config Builder run with an assigned projection shows a locale pill
  immediately to the right of the projection pill.
- [x] More contains a Config Summary action that opens a keyboard- and
  screen-reader-accessible modal.
- [x] The modal table contains exactly the six requested row labels and the
  effective values for the current run.
- [x] Representation renders as `Single OFE` or `Multiple OFE`.
- [x] Absent or unsupported summary state is communicated honestly and does
  not cause a run-page error.
- [x] Focused tests, frontend lint/tests, scoped documentation lint, and the
  correctness/UX gate pass. The modal smoke branch is committed and syntax
  checked; live execution was unavailable because the smoke environment could
  not provision or locate a Config Builder run, as recorded in the tracker.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes; this package and its contract decision
  record the requested read-only presentation behavior

## Dependencies

### Prerequisites

- Effective locale and project-owned config authority from the Project Config
  packages must remain available and unchanged.
- Operator approval of the exact locale pill spelling/display contract.
- Contract-first checkpoint required by
  `docs/standards/contract-first-change-standard.md`.

### Blocks

- None known.

## Related Packages

- **Related**:
  `../20260827_project_config_run_ui_authority/package.md`
- **Related**:
  `../20260804_project_config_builder_ui/package.md`

## Timeline Estimate

- **Expected duration**: 1-2 focused implementation days after contract approval
- **Complexity**: Low
- **Risk level**: Low

## Security Impact and Review Gate

- **Security impact triage**: low
- **Dedicated security review required**: no
- **Triage rationale**: The feature adds a new HTML disclosure/rendering sink
  for values already loaded behind the existing project-read authorization. It
  adds no route, mutation, external input, or broader audience; regression
  evidence must prove authorization precedes rendering and values are escaped.
- **Security review artifact**: N/A

## References

- `docs/standards/contract-first-change-standard.md`
- `docs/schemas/project-owned-config-contract.md`
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm`
- `wepppy/weppcloud/routes/run_0/run_0_bp.py`
- `tests/weppcloud/routes/test_pure_controls_render.py`

## Deliverables

- Approved canonical UI contract and contract-decision checkpoint
- Locale pill and Config Summary modal
- Presentation-model and rendering regression tests
- Updated user/developer documentation and completed correctness review

## Follow-up Work

- Record only discoveries that fall outside the six-field, read-only summary;
  do not expand this package implicitly.
