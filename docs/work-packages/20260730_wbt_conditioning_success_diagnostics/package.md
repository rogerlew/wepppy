# WBT Conditioning Success Diagnostics

**Status**: Complete locally; production promotion separate (2026-07-30)
**Timezone**: UTC
**Package ID**: DOM-05B
**Parent owner**: DOM-05 Channel Delineation

## Overview

Propagate successful DEM-conditioning diagnostics from the four WEPPcloud WBT
methods into the channel delineation summary. The change makes large terrain
alterations visible to ordinary users, including the incident class where
depression filling raises terrain by hundreds of metres.

## Objectives

- Add a versioned JSON diagnostics sidecar to `FillDepressions`,
  `BreachDepressions`, and `BreachDepressionsLeastCost`, and align the existing
  `TopazConditionDem` sidecar with the shared contract.
- Retain stage attribution so filling, cutting, pit filling, fallback filling,
  and synthetic flat relief are not conflated.
- Publish interpretable, labeled diagnostic measures with the durable channel
  summary report.
- Preserve conditioning outputs, defaults, thresholds, and fallback behavior.

## Scope

### Included

- `/workdir/weppcloud-wbt` algorithms, CLI metadata, Python wrappers, tests,
  end-user documentation, runtime binary build, commit, and push.
- WEPPpy WBT dispatch, diagnostics validation/formatting, RQ completion
  message, controller summary presentation, durable documentation, and tests.
- Generated-output validation using the tracked TOPAZ fixture corresponding to
  the `srivas42-reconciled-turf` incident DEM.

### Explicitly Out of Scope

- Changes to fill, breach, least-cost, or TOPAZ numerical behavior.
- New warning thresholds or automatic method selection.
- Queue topology, authentication, CSRF, or deployment to production.
- Replacing the existing controlled least-cost unresolved-depression error.

## Compatibility and Regression Plan

The sidecar is additive and run-scoped. Existing rasters, persisted NoDb keys,
request payloads, and existing RQ response fields remain unchanged; open
`jobstatus` gains one additive optional `conditioning_diagnostics` field. WBT wrapper
diagnostics arguments are optional; WEPPcloud supplies a fixed run-local path
and validates schema version, tool identity, status, units, and finite numeric
values before publishing a summary. Regression coverage verifies all four
methods, missing/malformed sidecars, source-to-output extrema, fallback
attribution, RQ propagation, and plain-text rendering.

## Success Criteria

- [x] A standalone documentation-only checkpoint is independently reviewed and
  committed before implementation.
- [x] Every successful method reports maximum terrain raise and cut, including
  zero values, with explicit units.
- [x] Fill diagnostics expose the incident-scale maximum raise; fixture evidence
  records the measured value.
- [x] Least-cost diagnostics distinguish breach results from fallback filling.
- [x] TOPAZ diagnostics separate FILDEP changes from synthetic RELIEF.
- [x] The channel report presents separate labeled measures without duplicate
  prose or stacktrace styling.
- [x] Focused WBT, Python, RQ, frontend, docs, and generated-output gates pass.
- [x] `weppcloud-wbt` changes are committed and pushed.

Implementation conformance is complete. Production deployment remains a
separate operator action.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; operator request in this thread,
  implemented by Codex

No default, formula, threshold, unit conversion, or fallback heuristic changes.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: the fixed diagnostics artifact crosses a native
  subprocess, run-scoped filesystem, worker status, and browser presentation
  boundary. No user-controlled path or new route is introduced.
- **Security review artifact**:
  `artifacts/2026-07-30_security_review.md`

## Related Packages

- **Parent**:
  [DOM-05 Channel Delineation](../20260728_channel_delineation_ui_contract/)
- **Depends on**:
  [Least-cost unresolved depression](../20260730_wbt_least_cost_unresolved_depression/)
- **Related**:
  [TOPAZ WEPPpy integration](../20260729_topaz_conditioning_wepppy_integration/)

## Deliverables

- Shared sidecar schema and four WBT implementations.
- WEPPpy diagnostics reader, formatter, RQ propagation, and summary UI.
- Contract, user/developer documentation, and validation artifacts.
