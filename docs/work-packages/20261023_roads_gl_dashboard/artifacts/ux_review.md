# Roads GL Dashboard contract: independent UX review

## Scope and evidence

Reviewer: `/root/roads_dashboard_ux`. Date: 2026-10-24 UTC. Starting implementation
revision: `5227cb25831a1f86b2a70dd977d1cdad56a236cf`. This is a read-only review of
the accepted contract, existing source and user specification; no runtime or
canonical contract files were edited by this reviewer.

Reviewed: [Roads dashboard contract](../../../schemas/roads-gl-dashboard-contract.md),
[output-scope contract](../../../schemas/output-scope-contract.md),
`docs/ui-docs/gl-dashboard.md`, the dashboard template and orchestrator,
`static/js/gl-dashboard/scenario/manager.js`, `state.js`, module README,
`layers/renderer.js`, and `routes/gl_dashboard_flow_duration.py`.

Operator choices are accepted requirements: visible Baseline/Roads navigation,
road centerlines only, labeled full-profile mixed metrics, area-weighted
aggregation, remainder exclusion, existing jet2 palette and linear range with
maximum override. This review does not reopen those choices. The road overlay
and scope switch are not implemented. Agent review is not a human usability
study, accessibility certification, owner ratification or runtime validation.

## User task walkthrough

The primary task is to open a run, choose Roads output without editing a URL,
and inspect road detachment while understanding which model results are shown.
A separate road visibility checkbox is justified: watershed output scope and
road-line diagnostics answer different questions. Reusing the existing palette
and legend maximum avoids an unnecessary new configuration system.

The contract correctly requires a labeled current scope, independent channel
visibility, no graph/year-slider activation from the mean-annual road layer,
persistent segment details and a keyboard-accessible table. It retains scientific
limits: lines do not map modeled off-road rectangles, mixed rates are explicitly
full-profile values, and detachment is not sediment export or incremental impact.

Review dimensions are scope (Baseline/Roads), map scenario (base/named/comparison),
graph (none/supported in target scope/unsupported), Roads artifact state
(never used/prepared-only/empty/current/stale or failed/malformed), and access
(authorized/denied/transient error). This is a contract matrix, not executed tests.

## Findings

| ID | Severity | Exact contract/source surface | User consequence | Smallest improvement | Observable acceptance check |
| --- | --- | --- | --- | --- | --- |
| UX-01 | Medium | Roads contract, **Dashboard output-scope switch**, paragraph starting "Roads scope uses"; existing `gl_dashboard.htm` Scenario/Compare controls and `gl-dashboard.js::bindScenarioSelector` / `bindComparisonToggle` | Entry to Roads clears an Omni selection, but subsequent scenario/comparison selection while Roads remains active is unspecified. Users could enter an unsupported combination or see a misleading scenario label. | Keep incompatible map scenario/comparison controls unavailable while Roads scope is active, with a short inline reason; re-enable them in Baseline. Apply the same rule during initialization or restored state, not only the scope-change event. Do not change graph-specific scenario semantics implicitly. | Exercise both sequences: scenario/comparison then Roads, and Roads then attempt scenario/comparison. Roads remains current-run output, no difference badge or incompatible query survives, and switching back to Baseline makes the existing controls usable. A restored incompatible selection cannot override the displayed Roads scope. |
| UX-02 | Medium | Roads contract, **Dashboard output-scope switch**, "Preserve map position and compatible display choices"; existing `gl_dashboard_flow_duration.py::flow_duration_context` and user spec **Daily flow duration** | An active graph may be incompatible with the target scope. Flow Duration is explicitly Baseline-only; graphs also have scenario choices separate from the map selector. The contract does not say what the user sees when such a panel loses compatibility. | Define a visible unavailable/cleared graph state with a concise explanation when scope invalidates its active selection; remove stale graph values and graph-only sliders without resetting the map or silently selecting another graph. Preserve supported graph selections. Keep each graph's existing scenario/scope contract. | Open Flow Duration in Baseline, switch to Roads, and observe an explicit baseline-only explanation with no old curve presented as Roads data. Map and scope switch remain usable. A supported graph survives a round trip with its scope-specific data refreshed. |

No additional optional controls or deferred features are recommended. The
existing requirements for visible unavailable reasons and keyboard selection
are adequate at contract level; implementation must make those reasons readable
without relying on hover over a disabled option.

## Initial verdict

Contract UX gate: **hold pending UX-01 and UX-02 disposition**. There are no high
findings and two medium findings. Both are small clarifications of accepted
scope behavior, not changes to scientific formulas or requests for new services.
Post-amendment review must verify their closure before this artifact is treated
as approval. Implementation, browser/keyboard testing and production validation
remain separate future gates.

## Post-amendment disposition

Rechecked 2026-10-24 05:37 UTC against the current canonical contract, shared
output-scope amendment, ADR-0105, package brief, decision record and review plan.
This section supersedes the initial hold above.

| ID | Disposition | Independent confirmation |
| --- | --- | --- |
| UX-01 | Resolved | **Dashboard output-scope switch** now disables incompatible map scenario/comparison controls while Roads is selected, explains why, rejects incompatible restored/hash selections before queries, and re-enables controls in Baseline. The shared output-scope contract repeats this boundary. Graph-specific scenario rules are explicitly preserved. |
| UX-02 | Resolved | The same section explicitly clears an unsupported active graph with an explanation, identifies Flow Duration as baseline-only, preserves supported graph choices and graph-specific rules, and prevents invented slider context. The shared output-scope contract carries the same requirement. |

The added initial-unavailable view preserves the lifecycle error status while
retaining a Baseline navigation link, so an invalid Roads bookmark does not trap
the user. Optional layer errors no longer imply clearing valid baseline layers
or entering an automatic reload loop. A coherent guarded detachment response
feeds the legend, hover, details and table together; this removes the risk of
showing a selected road's details from a different preparation than its map line.
The materialization detail adds no new user control. The corrected distinction
between continuous-mode summary requirements and valid single-storm scope is
consistent with the upstream lifecycle and avoids promising an invalid state.

ADR-0105 preserves accepted full-profile meanings, centerline-only geometry,
jet2, project-specific scaling and explicit numeric/accessible equivalents.
It makes no new claim of comparative color meaning across projects. No new
blocking UX finding arose from these amendments.

Reviewed file SHA256 values:

- `docs/schemas/roads-gl-dashboard-contract.md`: `e86c6690390c1b84e8402d05d9712f6265486ea8319568d2d90d3814dda7b54f`
- `docs/schemas/output-scope-contract.md`: `1b01fca3fbf792267764fa6df34fc535f7bed6e7f96a347c2a3a3335ca196358`
- `docs/adrs/ADR-0105-roads-dashboard-detachment-display.md`: `7f9b3dae18eea5c803c235a1ab6babfdba8ec85c7a1f3d2f7c84610f0343dd60`

Final contract UX verdict: **pass**, no unresolved high or medium findings.
Approval is limited to the reviewed specification. The acceptance checks in
the initial findings remain required implementation tests, including keyboard
navigation, both scope-transition orders, unsupported graph clearing, narrow
screens and visible unavailable reasons. No browser behavior or accessibility
conformance has been established by this document review.

Final COR04 amendment rechecked: nullable per-profile `segment_length_m` is
labeled **Modeled source road-segment length**; missing values remain unavailable.
Uploaded source length stays separately identified and cannot substitute for or
be summed into a prepared segment length. This clarifies provenance without
adding a control or implying surveyed geometry. No new UX concern; the contract
hash above reflects this final amendment. Implementation should verify a
multi-profile segment and a missing-length row show these distinctions.
