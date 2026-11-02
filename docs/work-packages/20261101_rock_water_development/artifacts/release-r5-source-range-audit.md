# Revision-5 native source-range audit

Date: 2026-11-01. Read-only Git/source inspection; no canonical writes, builds, or model executions. Legacy implementation is summarized without reproducing source.

## Exact range

Revision-4 model-source baseline: `b01a739957bef5aacf35b4a89bc13eddc9d94804`.
Verified current HEAD: **`a8e008135f82e6a071acd836672d829e8e9e8e8d`**. The supplied full hash is correct.

The committed source delta contains exactly eight paths under `src`: `contin.for`, `idat.for`, new `interception_budget.f90`, `makefile`, `rochek.for`, `sedout.for`, `watbal.for`, and `watbal_hourly.for`. There is no committed `fpm-src` change. Source-mode restoration commit `21e1f99e1` restores the existing executable modes on five preexisting files; no net mode change remains versus revision 4, apart from the new helper's ordinary 100644 mode.

## Shipped behavior, interface and build changes

| Register group | Exact changed files | Result and compatibility |
| --- | --- | --- |
| Conservative represented interception allocation | `idat.for`, `interception_budget.f90` | Primitive rain, melt, eligible irrigation and carried canopy supply enter an error-free binary64 expansion before capacity comparison. Accepted native REAL canopy/residue stores are bounded by the represented budget and checked against the next representable value. Canopy-first branch priority is retained; no empirical epsilon or storage floor is introduced. IDAT net interception/storm depletion uses the shared signed remaining-supply calculation. |
| Shared interception consumers | `watbal.for`, `watbal_hourly.for`, `rochek.for` | Daily and hourly native water input use the same primitive budget-minus-accepted-store ordering before the explicit REAL conversion. Furrow irrigation stays outside interception and is added at its existing consumer boundary. ROCHEK retains its effective-plane supply and geometry semantics while using the shared signed remainder. Existing unmet-withdrawal guards remain. |
| Fixed-width ELEMENT soil-water printing | `contin.for`, `sedout.for` | The Sm field remains seven characters and keeps its existing fixed-decimal bytes when they fit. Only overflow cases reduce decimal precision or use scientific notation, keeping large finite diagnostics numeric instead of stars. Both event and non-event writers are covered; the physical storage value and neighboring column positions are unchanged. Readers must accept scientific numeric notation in this existing field. |
| Matched-pair build linkage | `makefile` | Both watershed and hillslope link the new allocation object. Its dedicated free-form build rule explicitly disables unsafe-math optimization and floating-point contraction, preserving the expansion's operation ordering. This is a required build contract, not a blanket precision-kind change. |

The allocation helper adds internal module/functions and explicit overdraw/rounding error stops. It does not add user configuration files, CLI prompts, public storage columns, or external libraries. Returned binary64 and persisted REAL fluxes retain explicit rounding boundaries; the release must not claim exact downstream physical conservation from exact represented-store admission alone.

Only commits `1e57cf6fe` (allocation/consumers), `21e1f99e1` (mode restoration), and `a8e008135` (Sm printing) change these final runtime/build sources after the documentation-only checkpoint `c58ad035c`. Frost gate/thermal routines, conductivity policy, rock-cover parameterization, retention formulas, and soil thickness contracts are unchanged in this source range. The experimental frost bypass and Roads-only observation/control stacks are not shipped.

## Tests and reproducible resources

- `tests/test_negative_fin_local_inputs.py` links the new helper into extracted native consumer probes using strict floating-point flags and adds cancellation cases where tiny positive melt must survive cancellation with rain or canopy carry.
- `tests/test_element_sm_format.py` extracts the actual two writer formatting blocks, compiles probes, checks seven-character width and numeric output across normal, large, and negative finite inputs, preserves original bytes when representable, and checks displayed rounding scale.
- `tests/test_retention_volume_watchlist.py` and three committed `tests/fixtures/retention_volume_prototype` decks provide complete-history ordinary-artifact/calendar checks. They are runtime seeds, explicitly not scientific admission of the prototype retention parameterization. The associated watchlist/manifest records fixture provenance.
- `tools/native_melt_support.py` and `tools/audit_native_melt_support.py` promote reusable original diagnostic/audit tooling. `tests/test_equivalent_plane_sources.py` invokes the maintained tools path rather than an archived artifact script. These are validation tools, not additional runtime physics changes.

This audit identifies test coverage introduced in the range; it does not claim the concurrently running final-byte tests have passed. Report their actual final receipts separately.

## Documentation and release-history carryover

Commit `1959d8f61` promotes the already accepted revision-4 pair and report. Because the range begins at the revision-4 source commit rather than its later publication commit, those binary/sidecar/report changes appear in the range but are **revision-4 publication carryover**, not new revision-5 physics.

Intermediate commits record source-free findings and evidence for Roads roughness/routing feedback, rock representation and storage/capacity ownership, native rock-basis interpretation, scalar water accounting, SIFT/frozen mapping, frozen-history/reset/accepted-flux observations, retention-volume prototype, and failed retention/frost admission. Group these as investigation provenance and explicit limitations in the register; do not describe their experimental interventions as adopted behavior.

Final source specifications for the changed allocation/consumer/writer files, the rock-water development incident/evidence manifest, watchlist, and `change-log.md` document the new integration. Preserve earlier evidence packages and revision-1 through revision-4 publications unchanged.

At inspection, working-tree `src/wepp`, `src/wepp_hill`, and native `release/wepp_261029*` binary/sidecar files are modified by the final release build. They are not identical to the committed revision-4 release artifacts merely because the source-range audit ends at HEAD. Revision-5 publication must bind the separately retained actual final-pair hashes/source/build receipt and reviewed report, not infer executable identity from Git's committed release files.
