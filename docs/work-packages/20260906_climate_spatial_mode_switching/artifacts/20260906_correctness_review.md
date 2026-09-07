# Correctness and User-Experience Review - Climate spatial mode switching

## Metadata

- Package: `docs/work-packages/20260906_climate_spatial_mode_switching/`.
- Reviewer: independent Codex reviewer `/root/climate_correctness`.
- Date: 2026-09-07 UTC; package date 2026-09-06 Pacific.
- Revision: working-tree diff against `376c993b13fe9debda301e3d2ab5e2e3377f09a6`, branch `master`.
- Scope: `wepppy/weppcloud/templates/controls/climate_pure.htm`, its new real-template regression in `tests/weppcloud/routes/test_pure_controls_render.py`, controller regression in `wepppy/weppcloud/controllers_js/__tests__/climate.test.js`, and supporting documentation.
- Authority: `docs/schemas/project-owned-config-contract.md` section 9, especially dataset/method adjacency and flattened-project rendering; `docs/ui-docs/controller-contract.md`, "Project-config run authority and refresh"; `docs/standards/contract-first-change-standard.md`, "Conformance Fixes and Urgent Restoration".
- Security artifact: not required; presentation-only change introduces no authentication, persistence, filesystem, or execution boundary.

## User Outcome

An available observed Daymet or gridMET dataset enables Multiple climates
(Interpolated) after the user switches from Vanilla CLIGEN or stochastic PRISM,
without a reload. Selecting it submits existing spatial mode `2`. Switching
back disables interpolation and restores a supported selected mode.

The template now retains the union of modes from selectable datasets in the
supplied catalog, plus the exact stored current mode. It does not consult a
global provider catalog. Per-dataset enablement remains separate from the
rendered union, so union membership does not authorize a dataset/method cross-product.
This is a bounded restoration of existing canonical intent.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence or limit |
| --- | --- | --- | --- |
| New/default run, observed dataset available | Yes | Render mode 2 disabled initially; allow it after switching | New real-Jinja test covers both initial datasets and both observed datasets; new Jest cases exercise switching, selection, and setter submission |
| Catalog absent or present-empty in compatibility context | Existing compatibility state | Preserve the previous template path | Source inspection: unchanged `catalog = climate_catalog or []` and unchanged unfiltered branch when no selected dataset; no new dedicated execution test |
| Populated observed selection with stored mode 2 | Yes | Render mode 2 enabled and checked on reload | Reload assertions in all four available-catalog Jinja cases |
| Restricted catalog without mode 2 adjacency | Yes | Do not invent interpolation | Four restricted-catalog Jinja cases; existing Europe preset rendering coverage |
| Hidden or disabled alternative dataset | Yes | Do not contribute new selectable modes | Eight hidden/disabled-dataset Jinja cases |
| Supported legacy exact-current method outside authority | Yes | Preserve its disabled current display in rendered HTML | Existing `test_run_context_renders_outside_axis_climate_with_ordinary_landcover` checks checked/disabled mode 2; runtime limitation below |
| Malformed authority or unsupported new submitted method | No | Retain explicit server refusal before mutation | No changed server boundary; existing climate route tests cover unsupported graph selections and exact-current compatibility |
| Read-only run | Yes | Retain read-only hooks | Spatial inputs retain `disable-readonly`; no new dedicated browser test |

Input dimensions are independent of stored states: the new render test crosses
two initial datasets, two observed datasets, and four availability conditions
(16 cases). The new controller tests cover each observed dataset with the same
non-interpolating initial fixture. They use the existing real controller and
mock HTTP transport. The Jinja regression directly executes the production
template where the omission occurs. Coverage is not exhaustive across catalogs,
locales, stored states, or browser lifecycle behavior.

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Interpolation unsupported by selected dataset | Expected | Disabled option when another selectable dataset supports it; otherwise omitted unless exact current | Section 9 dataset/method adjacency |
| Stored method outside authority | Supported compatibility | Disabled current display in initial HTML; exact-current server rebuild remains permitted | Shared controller contract, current-state compatibility |
| Unsupported new method submitted directly | Invalid request | Existing diagnostic refusal, without mutation | Section 9 requires the same resolved authority at mutation/build boundaries |
| Existing dataset or spatial setter request fails | Exceptional transport/server failure | Existing controller error handling remains unchanged | No transport or error-contract delta in this patch |

No new exception, partial-write state, retry, cleanup, or readiness behavior is
introduced. Existing dataset and spatial setter lifecycle behavior is outside
the implementation diff.

## Review Checks

- Canonical intent supports conformance classification; no normative amendment or ancestor checkpoint is needed.
- The union excludes hidden, disabled-current, and deprecated single-storm datasets, and excludes disabled spatial methods.
- Exact-current inclusion does not add another selectable method to the union.
- Existing radio names, IDs, numeric values, and read-only attributes remain intact.
- No changed safety or persistence boundary requires an additional unmocked boundary test.
- Observed focused logs: `/tmp/climate-spatial-focused.log` reports 212 passed; `/tmp/climate-spatial-jest.log` reports 17 passed.
- Primary agent additionally reports full frontend validation at 108 suites / 835 tests, lint and documentation checks passed, and bundle rebuild with no generated diff. Broad pytest disposition follows below.

## Findings and Residual Risk

No introduced high, medium, or low correctness findings in the reviewed patch.

Preexisting adjacent limitation: `climate.js:updateSpatialModes` (around line
627) reads `spatial_modes` but does not honor `disabled_spatial_modes` or
`current_selection_disabled`. Bootstrap can therefore re-enable an initially
disabled legacy-current radio. This patch preserves template rendering but does
not repair or validate that existing controller behavior. Track a separate
controller conformance fix with a legacy-current bootstrap test if that workflow
is addressed; do not claim this package establishes runtime disabled-current
preservation.

No live browser dataset-switching smoke or climate-generation job was executed
by this reviewer. The production change is limited to initial markup and help
text; direct Jinja regression plus existing controller execution exercises the
confirmed failing seam.

## Broad Gate Disposition

The broad run stopped at 1 failure after 5078 passes and 50 skips in 648.53
seconds. The reviewer inspected `/tmp/climate-spatial-broad.log` and the
isolated confirmation in `/tmp/climate-spatial-unrelated.log`.

`tests/shape_converter/unit/test_runtime_hardening.py:128` asserts that
`shape-converter` is absent from the production wepp1 overlay, while
`docker/docker-compose.prod.wepp1.yml:146` declares that service. The test only
loads that YAML and checks its service keys. Both files have no diff from the
starting revision. The isolated test reproduces the same failure (1 failed in
9.61 seconds), establishing an existing test/configuration mismatch independent
of the climate template change.

Disposition: this unrelated failed gate does not create a finding against the
bounded climate fix. The package may close with the failure explicitly recorded;
the broad suite is not green and remaining tests after the first failure were
not executed. Resolve the shape-converter expectation separately under its
own deployment contract. This review grants no deployment approval.

## Verdict

- Gate status: `pass` for the scoped conformance fix.
- Unresolved findings introduced by this patch: High 0; Medium 0; Low 0.
- Release recommendation: `ship-with-conditions`; scoped package closeout is acceptable with the unrelated failed broad gate and residual coverage limits documented. No full-suite green or deployment claim is supported.
- Reviewer sign-off: Codex `/root/climate_correctness`, 2026-09-07 UTC.
