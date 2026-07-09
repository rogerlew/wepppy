# AgFields UI Spec Verification — Codex Findings and Disposition

**Date**: 2026-07-09
**Reviewer**: Codex (read-only MCP session), dispositioned by Claude Code
**Subject**: `wepppy/nodb/mods/ag_fields/ui_control_layout.md` (committed `849da71a6`)
**Evidence class**: static — Codex read source and reported findings; no code was executed.

Codex verified the spec's technical claims against the codebase and returned 28 findings plus 2 additional risks. All were dispositioned; the spec was amended in place before commit. Summary below; the amended spec text is authoritative.

## Critical finding (real backend bug, not a spec error)

**`run_wepp_subfield` references `self.wepp_instance.wepp_bin` (`ag_fields.py:1046`) from a module-level function.** Verified independently by reading the source: the signature (line 970) has no `self`; every sub-field run raises `NameError` at the `run_hillslope` call. Presumably introduced when the runner was extracted from the class for the thread pool. Disposition: spec §10 item 1, Milestone 1 of this package, blocks UI stage 4.

## Accepted with spec amendments

| # | Finding | Spec change |
|---|---|---|
| 2 | `validate_field_boundary_geojson` returns only duplicates; count/columns/timestamp are route-assembled | §3/§9 upload rows clarified |
| 3 | CRS errors surface at rasterize (inference exists), not upload | Moved to stage 2 failure modes |
| 4 | Re-upload does not invalidate downstream NoDb state | Staleness contract added as §10 prerequisite; snapshot-driven flags in §4 |
| 5 | Schema setters are independent; atomicity is the route's job | §3/§9 amended (validate-then-persist) |
| 6 | `set_rotation_accessor` gives no friendly error for missing observed bounds | Observed-readiness gate derived in state snapshot |
| 8 | `get_unique_crops` does not use `field_id_key` | Stage 3 gating text corrected |
| 9 | No `is_observed` helper; derive from `climate_mode` + parseable bounds | §3/§10 amended |
| 10 | Plant upload nuances: suffix only on flatten conflicts; root same-name and downgrade outputs overwrite; invalid 2017.1 aborts | §3/§10 amended |
| 14 | Failure cancels pending sub-fields; in-flight runs finish | Stage 4 wording corrected |
| 15 | Auto workers = min(sub-field count, CPU count) | Help copy corrected |
| 18 | Peridot asserts flovec.tif AND field_boundaries.tif; latter is job-produced | Stage 2 gate = flovec only; no reliance on Python assert |
| 19 | Maturity label needs `_feature_form_map` entry or explicit `feature_id` | §6 amended |
| 20 | "alpha" invalid; registry-derived labels; AgFields is `maturity: internal` | Grounding + open decision 3 (bump to `experimental` at ship) |
| 22 | Disturbed modal is included unconditionally, self-gates; opener is separate | Grounding/§5 corrected |
| 23 | Runs-page idiom = `show_*` flag + `data-mod-nav` + `data-mod-section` | Grounding corrected |
| 24 | `resolveJobId` matches exact keys | Contractual job keys added (§7) |
| 25 | Map overlay: Roads precedent (resource endpoint + `addGeoJsonOverlay`) | Resolved from open decision into §3/§9 contract |
| 28 | Route precedents: Treatments (upload+enqueue), Disturbed SBS (sync upload), Roads mixed-legacy | §9 preamble names them |
| + | Uppercase `.MAN` silently ignored; deprecated `logger.warn` | §10 items 6 and 11 |

## Confirmed, no change required

`field_id` hard requirement and non-blocking duplicates; `set_field_id_key` semantics; `validate_rotation_lookup` returns nothing; parent `wepp/runs` soil/climate dependency; hydration properties exist at NoDb level; WGS sub-fields GeoJSON output; Batch Runner conventions; no existing AgFields routes or RQ tasks.

## Not applicable

Finding 27 (`agfields_auto_prep` gates only the metrics export family): accurate observation, but the spec makes no claim about it — no change.
