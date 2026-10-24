# Roads GL Dashboard contract security review

## Findings

These are contract gaps and integration hazards for the proposed feature, not
claims that an unimplemented Roads dashboard layer is currently exploitable.

| ID | Severity | Surface and exploit/failure path | Evidence | Required correction | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | An uploaded road name/source identifier containing markup reaches the new hover, persistent details or accessible table. An implementation using HTML interpolation could execute it for another authorized viewer or a visitor to a public run. | Contract Display and interaction requires source labels; `Roads.query_map_segments_geojson` copies uploaded feature properties at `wepppy/nodb/mods/roads/roads.py:1282`. | Require literal-text rendering or the established escaped renderer for every artifact-sourced string. Do not derive executable markup, links, resource URLs or styles from arbitrary properties. Add a real browser hostile-label test proving literal display and no script execution or unexpected fetch. | Closed in contract; runtime evidence pending. |
| SEC-02 | High | A dashboard reads old geometry, another session prepares and successfully runs new geometry with reused sequential IDs, then the first dashboard reads new summary/manifest. Every individual read is authorized/current, but the joined line colors are false. | Lifecycle contract explicitly permits reused preparation-local IDs and forbids cross-preparation joins. `_roads_lifecycle.current_read` guards one operation; `_validate_receipt` at lines 126–147 accepts exactly policy/mode/path fields with no execution identity. Geometry route and query transport are independent requests. | Require all geometry, results, manifest and CRS inputs used in one colored view to be read coherently under the existing Roads shared admission, or another concretely proven existing mechanism. Do not claim equal segment IDs or equal receipt bytes establish a snapshot. Reuse existing transport/guards; no new fingerprint or identity subsystem. Include direct concurrent reprepare/rerun/read coverage with reused IDs and verify an old response cannot overwrite a newer view. | Closed in contract; runtime evidence pending. |
| SEC-03 | Medium | A missing, invalidated or denied optional Roads result read poisons unrelated baseline requests or triggers repeated whole-page reloads. Generic non-OK responses can be treated as empty data. | `static/js/gl-dashboard/data/query-engine.js:12–31` has one shared Roads-unavailable latch and returns null for other non-OK statuses; `static/js/gl-dashboard.js:263–267` reloads the whole page on that latch. | Make the new optional Roads read/error state independent from baseline queries. Preserve 401/403 and transient failures distinctly from absence/lifecycle409; clear only affected Roads visuals, keep baseline and scope-back navigation usable, and reset request state for a new scope/context without a reload loop. Add direct unauthorized/transient/lifecycle tests plus the valid baseline-with-no-Roads case. | Closed in contract; runtime evidence pending. |

## Scope and independence

Reviewer: `/root/roads_dashboard_security`, 2026-10-24 UTC. Starting repository
revision: `5227cb25831a1f86b2a70dd977d1cdad56a236cf`. Reviewed the accepted working
contract, the output-scope amendment, current Roads lifecycle and query-catalog
contracts, and actual route/query/lifecycle/browser code. Parent authors canonical
changes and dispositions; this reviewer edits only this artifact.

This is a read-only contract review. No project mutations, model execution,
runtime changes, live auth changes or production operations were performed.
Runtime acceptance tests listed here are requirements, not completed tests.

## Security triage and boundaries

Impact: **high** for review purposes because the new view combines user-controlled
geometry/labels with current scientific results across independent authorized
transports. The scope switch itself does not add roles, privileges, endpoints,
scope values, write operations or CSRF exceptions. Keep existing same-run
authorization, child-run ownership and physical dataset authorization; current
readiness and catalog freshness are never substitutes for authorization.

Preserve existing logical/physical Roads path admission, `Cache-Control: no-store`
for current-result responses, symlink/traversal restrictions and explicit history
reads. Do not treat an explicitly historical or parent-selected physical source
as the child's current Roads data. New transformed geometry, if needed, remains
an authorized, browsable and archivable artifact under the existing standards.
CRS failure, malformed coordinate types or nonfinite coordinates must fail the
Roads layer explicitly without widening filesystem access or blocking baseline.

## Valid-state noninterference and acceptance

| State | Contract outcome | Required evidence |
| --- | --- | --- |
| Never-used Roads / absent optional state | Ordinary baseline dashboard remains usable; no invented Roads result. | Unmocked baseline route/browser load without Roads files. |
| Prepared geometry but no current results | Geometry/status may remain available; no stale detachment color. | Actual lifecycle read and view invalidation, no whole-page reload loop. |
| Valid empty summary | Explicit empty result, not zero detachment; preserve other layers. | Real parsed empty Parquet plus browser state. |
| Populated current results | Authorized coherent geometry/result join; source labels displayed literally. | Actual producer-to-consumer readback and browser selection, legend and table. |
| Single-storm without mean-annual summary | No detachment coloring; independently valid Roads watershed scope remains governed by its own mandatory resources. | Direct mode/resource checks rather than fabricated receipt alone. |
| Historical beta / stale or failed preparation/run | Remains non-current; explain prepare/run recovery and preserve authorized diagnostics. | Actual current-prefix refusal and explicit-history read, including reused IDs. |
| Unauthorized source or transient transport failure | Retain distinct error state; no absence claim or baseline fallback under Roads labeling. | Real auth boundary and transport failure tests; baseline controls survive optional-layer failure. |
| Hostile labels/paths/geometry or mixed lifecycle inputs | Reject unsafe interpretation; no script, external fetch, path escape or false current join. | Hostile-label browser case, actual path authorization, finite coordinates and concurrent replacement/read case. |

Cross-context acceptance must cover both scope directions, browser reload/deep
link, an Omni scenario/comparison active before Roads selection, child runs with
only parent Roads artifacts, and late async responses after switching scope.
Do not claim these combinations are implemented or validated by this review.

## Initial verdict

Contract gate: **fail pending disposition**. Open findings: high 1, medium 2,
low 0. Implementation/deployment remains on hold. Post-amendment confirmation is
required before contract approval; a later runtime security gate must verify the
actual implementation and the direct boundary tests above.

## Independent amendment recheck

Reviewer: `/root/roads_dashboard_security`, 2026-10-24 05:39 UTC. Re-read the
amended canonical contracts, opt-in response schema, ADR, decision record and
disposition against the existing authorized map route, lifecycle reader and
dashboard request helpers. No canonical or runtime files were edited by this
reviewer. No additional security findings were identified.

| Finding | Closure evidence |
| --- | --- |
| SEC-01 | Dashboard **Integration and acceptance boundary** requires text nodes/equivalent escaping for all artifact-sourced strings and authorized builders for artifact links. **Coherent detachment view payload** reserves computed `roads_detachment` metadata against uploaded properties. Actual hostile-label browser acceptance is required. |
| SEC-02 | Dashboard **Integration and acceptance boundary** binds geometry, prepare CRS, manifest and summary to one existing shared admission held through validation/materialization. The opt-in existing map resource returns the full derived view; details cannot perform late independent profile queries. Lifecycle crosslink preserves this rule and current-resource requirements; real concurrent reprepare/rerun/read coverage is required. |
| SEC-03 | Dashboard **Error isolation and cache behavior** separates optional-layer state and distinguishes denial, lifecycle409, absence and transient failure; it forbids a shared poisoned latch/reload loop and discards stale responses. **Dashboard output-scope switch** preserves authorized lifecycle status/code plus a Baseline escape on initial failure. Output-scope amendment agrees. |

The bounded `resources/roads.json?view=detachment` extension preserves the ordinary
map response and prepared-only behavior when `view` is absent. Unknown views
return 400 after authorization. It introduces no caller-selected source path,
query, new privilege, mutation endpoint or CSRF exception. Existing no-store,
physical-path admission and child-run boundaries remain authoritative. Valid
single-storm and typed-empty states are distinct from invalid continuous-resource
sets; payload state does not bypass lifecycle admission. Source properties remain
untrusted data, and computed values are isolated in the reserved namespace.

Reviewed canonical SHA-256 values:

| File under `docs/` | SHA-256 |
| --- | --- |
| `schemas/roads-gl-dashboard-contract.md` | `e86c6690390c1b84e8402d05d9712f6265486ea8319568d2d90d3814dda7b54f` |
| `schemas/output-scope-contract.md` | `1b01fca3fbf792267764fa6df34fc535f7bed6e7f96a347c2a3a3335ca196358` |
| `schemas/roads-preparation-lifecycle-contract.md` | `6ab24cf434a78db908c50509ccb9ef9588dc38128732f1ec94f4d3da4bea384a` |
| `adrs/ADR-0105-roads-dashboard-detachment-display.md` | `7f9b3dae18eea5c803c235a1ab6babfdba8ec85c7a1f3d2f7c84610f0343dd60` |

Contract security gate: **pass**. Open contract findings: high 0, medium 0, low 0.
No unresolved security risk acceptance was used. This closes SEC-01 through SEC-03
at the specification boundary only. The implementation checkpoint and subsequent
runtime security review remain required; actual reader/UI/auth/race tests have not
been executed and this verdict does not authorize production deployment.

Artifact validation: scoped `wctl doc-lint` passed with zero errors/warnings;
`uk2us` spelling preview was empty and scoped `git diff --check` passed.

## Final editorial-status confirmation

2026-10-24 05:40 UTC: independently confirmed the only subsequent canonical
changes are the dashboard contract status paragraph and ADR status line. Replacing
those strings in memory with their previously reviewed text reproduces both
original SHA-256 values exactly. The output-scope and lifecycle hashes are unchanged.
No normative delta; the contract security **pass** and runtime limitations stand.

| Final file under `docs/` | SHA-256 |
| --- | --- |
| `schemas/roads-gl-dashboard-contract.md` | `3cfb9eb59529fe226551ccfa904da42752b6522c61616f8dcab055f848e2d926` |
| `schemas/output-scope-contract.md` | `1b01fca3fbf792267764fa6df34fc535f7bed6e7f96a347c2a3a3335ca196358` |
| `schemas/roads-preparation-lifecycle-contract.md` | `6ab24cf434a78db908c50509ccb9ef9588dc38128732f1ec94f4d3da4bea384a` |
| `adrs/ADR-0105-roads-dashboard-detachment-display.md` | `f631859edeebcf206dbd637a0392b11958e2b28a0720e9b67c53b53bcab0f178` |
