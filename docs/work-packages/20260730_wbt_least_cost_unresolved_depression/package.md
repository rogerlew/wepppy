# WBT Least-Cost Unresolved-Depression Fail-Fast Guidance

**Status**: Implementation complete; rollout pending (2026-07-30)
**Timezone**: UTC

## Overview

Prevent WhiteboxTools least-cost breaching from silently converting a bounded,
unresolved depression into an extreme fill that materially changes drainage.
When WEPPcloud cannot resolve a depression within the selected breach search
distance, channel delineation must stop with concise, instructional guidance
instead of producing a plausible-looking but invalid channel network.

The triggering run is
`srivas42-reconciled-turf/disturbed9002_wbt`. Its 2026-07-29 watershed log
records `breach_least_cost`, a 1,000 m search distance, and `blc_fill=True`.
The fill fallback raised cells by as much as 379.16178369142 m after 377
depressions remained unresolved.

## Objectives

- Disable automatic filling of depressions left unresolved by
  `BreachDepressionsLeastCost` for the approved WEPPcloud path.
- Establish an explicit fail-fast postcondition when least-cost breaching
  leaves one or more unresolved depressions.
- Preserve a stable, typed error from `weppcloud-wbt` or the narrowest reliable
  WEPPpy boundary through RQ and into the channel delineation status summary.
- Tell the user what happened, why continuing would be unsafe, and what they
  can change: increase breach distance, enlarge/reposition the DEM extent so a
  plausible outlet is available, inspect DEM/NoData boundaries, or select a
  different conditioning method.
- Add exact-incident regression evidence without permanently depending on the
  production run directory.

## Scope

### Included

- A reproducible spike using
  `/wc1/runs/sr/srivas42-reconciled-turf/dem/dem.tif`.
- WhiteboxTools source/CLI behavior for `BreachDepressionsLeastCost --fill`.
- The WEPPpy wrapper and WBT channel-build path:
  `wepppy/topo/wbt/wbt_topaz_emulator.py`,
  `wepppy/nodb/core/watershed.py`, and `wepppy/rq/project_rq.py`.
- The channel delineation status/summary presentation in
  `wepppy/weppcloud/controllers_js/channel_delineation.js` and
  `channel_gl.js`, with the Pure UI control contract updated first when
  behavior changes.
- Targeted unit, integration, generated-output, controller, and manual smoke
  coverage.
- Operator/developer/user documentation and a parameterization ADR.
- Coordinated `weppcloud-wbt` work under `/workdir/weppcloud-wbt/` if the
  fail-fast contract belongs in the fork.

### Explicitly Out of Scope

- Automatically selecting a larger breach distance.
- Silently switching to Fill, Breach, or Topaz conditioning.
- General redesign of channel delineation or all WhiteboxTools errors.
- Treating every depression as invalid; the contract is limited to depressions
  that remain unresolved after the selected bounded least-cost search.
- Replacing the completed Topaz conditioning integration.

## Compatibility and Regression Plan

This package changes scientific workflow parameterization and failure behavior,
but must not rename or remove persisted NoDb keys, request fields, or
user-visible conditioning choices.

- Keep existing `wbt_fill_or_breach` and `wbt_blc_dist` contracts compatible.
- Introduce only additive diagnostic fields/codes if structured metadata is
  required.
- Do not leave partial `relief.tif` or downstream flow/channel artifacts
  discoverable as successful output after the controlled failure.
- Clear or preserve timestamps/readiness according to the existing failed
  channel-build contract; prove a corrected retry succeeds.
- Validate both fixture behavior and generated artifacts from the exact
  incident DEM.

## Stakeholders

- **Primary**: WEPPcloud users delineating WBT channels and WEPPcloud
  operators.
- **Reviewers**: WEPPpy/WEPPcloud maintainers and `weppcloud-wbt` maintainer.
- **Security Reviewer**: Not required by current triage.
- **Decision owner**: Operator/user requesting the parameterization change;
  record the named owner and meeting/channel in the ADR before merge.

## Success Criteria

- [x] A controlled experiment records behavior for `--fill=true` and
  `--fill=false`, including exit status, unresolved-pit signal, output
  existence, maximum elevation delta, and downstream D8 behavior.
- [x] The accepted design stops before channel products are accepted whenever
  bounded least-cost breaching leaves unresolved depressions.
- [x] The incident fixture no longer produces the extreme outlet-area
  fill on the approved least-cost path.
- [x] The channel delineation summary shows a non-stacktrace user message with
  the conditioning method, configured distance, corrective actions, and a
  correlation/error identifier when the canonical RQ contract supplies one.
- [x] Increasing the breach distance or choosing another conditioning method
  can be submitted as a normal retry without reconstructing the project.
- [x] Ordinary least-cost runs with no unresolved depressions remain
  byte-equivalent or scientifically equivalent within documented tolerances.
- [x] WBT, Python, RQ, frontend, documentation, and generated-output gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: `yes`
- **ADR required**: `yes`
- **ADR link**:
  [`ADR-0035`](../../adrs/ADR-0035-wbt-least-cost-unresolved-depression-failure.md)
- **Decision provenance captured**: `yes`

## Dependencies

### Prerequisites

- Confirm the precise user-facing summary surface and canonical controlled
  error payload before UI implementation.
- Complete the fill/no-fill experiment; upstream WhiteboxTools documentation
  says `--fill` fills remaining unbreached depressions, but does not state that
  omitting it returns an error.
- Decide whether the authoritative unresolved-depression error originates in
  the `weppcloud-wbt` fork or in a WEPPpy postcondition.

### Blocks

- Production rollout of least-cost fail-fast behavior.

## Related Packages

- **Related**:
  [`20260729_topaz_conditioning_wepppy_integration`](../20260729_topaz_conditioning_wepppy_integration/package.md)
  integrates the alternative Topaz conditioning path.
- **Related, cross-repository**:
  `/workdir/weppcloud-wbt/docs/work-packages/20260729_topaz_condition_dem_parity_hardening/`
  documents the same class of extreme outlet-area fill.
- **Related**:
  [`20260729_user_preferences_wbt_boundary`](../20260729_user_preferences_wbt_boundary/package.md)
  establishes controlled WBT boundary failures and retry semantics that should
  be reused rather than duplicated.

## Timeline Estimate

- **Expected duration**: 3-5 focused sessions
- **Complexity**: Medium-High
- **Risk level**: High scientific correctness; Medium implementation risk

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: The work changes subprocess outcome interpretation,
  RQ error propagation, and authenticated UI presentation without adding a new
  endpoint, permission, secret, file-input surface, or shell construction path.
- **Security review artifact**: N/A

## Hardening and Callus Softening

- **Failure signature**: `BreachDepressionsLeastCost` completes with fill
  fallback after the 1,000 m search cannot reach the western edge; the
  conditioned outlet-area waterbody is raised by roughly 450 m and downstream
  channel products are accepted.
- **Scope boundary**: Stop this confirmed least-cost unresolved-depression path
  and explain recovery without refactoring unrelated WBT tools.
- **Health signals**: No accepted extreme-fill artifact for the incident
  fixture; controlled-error frequency is observable; corrected retries
  succeed; unaffected delineations remain stable.
- **Danger signals**: Generic subprocess failures, leaked stack traces,
  partial artifacts treated as complete, silent algorithm fallback, or users
  repeatedly failing without actionable guidance.
- **Observation window**: 30 days after production rollout.
- **Temporary calluses introduced**: None planned. Any feature flag or
  compatibility shim must name an owner and removal date in `tracker.md`.

## References

- [WhiteboxTools hydrological analysis manual](https://jblindsay.github.io/wbt_book/available_tools/hydrological_analysis.html#breachdepressionsleastcost)
  — `--fill` fills depressions left unresolved by bounded breaching.
- `/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/breach_depressions_least_cost.rs`
  — fork source reports solved/unsolved pits and only fills them when
  `fill_deps` is true.
- `wepppy/topo/wbt/wbt_topaz_emulator.py` — currently passes `fill=True`.
- `wepppy/weppcloud/routes/usersum/weppcloud/wbt-channel-delineation.md` —
  current end-user conditioning guidance.
- `docs/standards/contract-first-change-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`
- `docs/standards/parameterization-adr-standard.md`

## Deliverables

- Parameterization ADR and accepted error/summary contract.
- WBT/WEPPpy implementation with stable error diagnostics.
- Incident fixture or compact derived fixture with provenance.
- Regression, integration, frontend, and generated-output evidence.
- Updated user, operator, and developer documentation.
- Code-review and QA-review artifacts with findings disposition.

## Follow-up Work

- Consider exposing `max_cost` only as a separately evidenced,
  ADR-governed package; it is not part of this fix.
- Use post-rollout telemetry to decide whether the guidance should link
  directly to the channel delineation help section.
