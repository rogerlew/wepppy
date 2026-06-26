# Forest-Family Burn Gradient Assessment

**Status**: Complete (2026-06-26)
**Timezone**: UTC

## Overview

This package extends the disturbed matrix harness so the new unburned
`deciduous forest` and `mixed forest` managements are compared against the
existing low, moderate, and high severity burned forest managements. The goal is
to determine whether the current generic burned forest classes remain
directionally correct when the unburned baseline is deciduous or mixed, or
whether a follow-up parameterization package is needed for burn severity variants
specific to deciduous and mixed forests.

## Objectives

- Add deciduous and mixed forest rows to the disturbed unit-test matrix.
- Regenerate `tests/disturbed/analysis_results.md` from actual WEPP runs.
- Summarize whether runoff, sediment delivery, and peakflow remain
  directionally correct from unburned to burned states.
- Record the decision on whether to add low/moderate/high burn severity
  parameterization for deciduous and mixed forests.

## Scope

### Included

- `tests/disturbed/test_disturbed_matrix.py` metadata expansion.
- `tests/disturbed/analyze_matrix.py` report-generation expansion.
- Regenerated `tests/disturbed/analysis_results.md`.
- Work-package and disturbed README documentation updates.

### Explicitly Out of Scope

- No shipped `.man` parameter changes.
- No production disturbed lookup row changes.
- No new deciduous/mixed burned management classes unless this assessment opens
  a follow-up package.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes, in this package and tracker

This package tests existing parameterization behavior. If a follow-up changes
burned forest defaults, that follow-up must update or add an ADR per
`docs/standards/parameterization-adr-standard.md`.

## Security Impact and Review Gate

- **Security impact triage**: none
- **Dedicated security review required**: no
- **Triage rationale**: test harness and documentation only; no route, auth,
  secret, filesystem boundary, queue, subprocess contract, or deployment surface
  changes.
- **Security review artifact**: N/A

## Dependencies

### Prerequisites

- Existing deciduous and mixed forest management package:
  `docs/work-packages/20260626_deciduous_mixed_forest_managements/`.
- Existing disturbed matrix harness under `tests/disturbed/`.

### Blocks

- Any decision to add low/moderate/high severity burned deciduous or mixed forest
  managements should use this package as evidence.

## Related Packages

- **Depends on**:
  `docs/work-packages/20260626_deciduous_mixed_forest_managements/package.md`
- **Follow-up**: TBD only if the regenerated report shows directional failures.

## Success Criteria

- [x] Disturbed matrix includes `forest`, `deciduous forest`, `mixed forest`,
  `shrub`, and `tall grass`.
- [x] All generated hillslope runs complete for the expanded matrix.
- [x] Regenerated markdown report includes explicit forest-family comparison
  conclusions.
- [x] Documentation states whether a follow-up burn parameterization package is
  needed.
- [x] Focused test and documentation validation pass, or any blocker is recorded.

## Deliverables

- Updated disturbed matrix harness and analysis script.
- Regenerated `tests/disturbed/analysis_results.md`.
- Updated `wepppy/nodb/mods/disturbed/README.md` validation summary.
- Work-package tracker with decision and validation evidence.

## Outcome

The expanded disturbed matrix passed with 80 hillslope simulations across four
soil textures, five vegetation types, and four burn severities. The regenerated
report shows the existing generic burned forest managements are directionally
correct against evergreen, deciduous, and mixed unburned baselines for runoff,
sediment delivery, and peakflow.

Decision: do not add low/moderate/high burned deciduous or mixed forest
managements from this evidence. A follow-up parameterization package is only
needed if a broader climate/slope/soil matrix later shows directional failure
or a calibration source requires vegetation-family-specific burned classes.

Validation:

- `wctl run-pytest tests/disturbed/test_disturbed_matrix.py -q` (`83 passed`,
  `2 warnings`, `232.70s`)
- `tests/disturbed/analyze_matrix.py --output-dir
  /tmp/pytest-of-unknown/pytest-10/disturbed_matrix0/output --out
  tests/disturbed/analysis_results.md` (`80` simulations loaded)
- `tests/disturbed/analyze_matrix.py --output-dir
  tests/disturbed/disturbed_matrix0/output --out /tmp/should_not_write_disturbed_report.md`
  exits before writing because the local ignored artifact tree contains only the
  old `48`-run layout.
- `wctl doc-lint --path docs/work-packages/20260626_forest_family_burn_gradient_assessment`
  (`2 files validated`, `0 errors`, `0 warnings`)
- `wctl doc-lint --path tests/disturbed/analysis_results.md`
  (`1 files validated`, `0 errors`, `0 warnings`)
- `wctl doc-lint --path tests/disturbed/PLAN.md` (`1 files validated`,
  `0 errors`, `0 warnings`)
- `wctl doc-lint --path wepppy/nodb/mods/disturbed/README.md`
  (`1 files validated`, `0 errors`, `0 warnings`)
- `wctl doc-lint --path PROJECT_TRACKER.md` (`1 files validated`, `0 errors`,
  `0 warnings`)
- `git diff --check`
