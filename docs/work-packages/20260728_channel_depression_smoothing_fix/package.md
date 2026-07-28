# Channel Depression Smoothing Propagation Fix

**Status**: In Progress
**Timezone**: UTC
**Remediation ID**: REM-05
**Borrowed owner**: DOM-05
**Security impact**: High (inherited from the RQ-backed DOM-05 boundary)

## Overview

The Channel Delineation control renders the WhiteboxTools depression-smoothing
selector with DOM id and submitted form name
`input_wbt_fill_or_breach`. Both channel controllers serialize only the
canonical request key `wbt_fill_or_breach`. The mismatch turns the selected
value into JSON `null`; the RQ worker therefore keeps the run's existing
configuration value and builds channels with the wrong conditioning algorithm.

REM-05 restores one finite contract: choosing Fill, Breach, or Breach (Least
Cost) must submit the corresponding canonical token, persist it on the
Watershed controller before channel construction, and render the persisted
selection after reload.

## Execution Authority

This package is governed by
`docs/standards/contract-first-change-standard.md` and the active ExecPlan at
`prompts/active/channel_depression_smoothing_fix_execplan.md`. It is registered
as a bounded remediation under GOV-00A-M1E because DOM-05 is planned and its
normal dependencies are not complete.

The documentation-only checkpoint, both independent reviews, and their
disposition must be committed as a standalone ancestor before the template or
tests are edited.

## Included Boundary

- `wepppy/weppcloud/templates/controls/channel_delineation_pure.htm`
- actual-template regression coverage in
  `tests/weppcloud/routes/test_pure_controls_render.py`
- worker persistence/failure characterization in
  `tests/rq/test_project_rq_mutation_guards.py`
- the existing channel controller fixtures and payload assertions, only if
  needed to prove the canonical request token
- the Channel Delineation Usersum guide
- REM-05 and parent GOV-00A/umbrella governance records
- deployment and production verification of the repaired control

## Exclusions

REM-05 does not change enum tokens, default algorithms, WhiteboxTools behavior,
map inputs, DEM upload rules, RQ queue wiring, route parsing, NoDb schema,
authorization, CSRF behavior, or any other DOM-05 field. It does not advance
DOM-05 from planned or unverified.

## Acceptance

The rendered selector keeps DOM id `input_wbt_fill_or_breach` and submits form
name `wbt_fill_or_breach`. Selecting `fill` produces a request with
`"wbt_fill_or_breach":"fill"` rather than `null`. The worker persists `fill`
before building channels, and a reload renders Fill selected. Focused template,
JavaScript, docs, and production smoke checks must pass.
