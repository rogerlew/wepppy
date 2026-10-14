# EDDE-WEPP-01 independent contract correctness review

Reviewer: independent `reviewer` agent. Reviewed before runtime implementation, against starting revision `6acfb3d23` and the proposed contract checkpoint. Scope: application contract and affected authorities, input/persistence compatibility, real acquisition and CLIGEN/WEPP consumers. No implementation changes made.

## Initial disposition: changes required

Three medium findings need a normative disposition before the ancestor checkpoint. They concern inherited execution semantics, not the accepted raw-EDDE or station-hybrid scientific policy.

1. **Medium — enumerate supported precipitation scaling for future EDDE.** `docs/schemas/edde-v2-weppcloud-contract.md`, **Acquisition, eligibility and execution**, currently preserves existing user-selected scaling without restricting AnnualMonthlies. `wepppy/nodb/core/climate_scaling_service.py:217` obtains historical reference series using `observed_start_year`/`observed_end_year`; future parsing clears those fields. An inherited AnnualMonthlies selection is therefore neither a valid future-data operation nor a usable build. Specify EDDE's supported modes and prerequisites, reject unsupported AnnualMonthlies before enqueue with parser rollback, and retain the previous selection until the user explicitly chooses a valid one. Do not silently select another scaling method or introduce historical-total bias correction.

2. **Medium — make the publication boundary include selected scaling.** The contract promises prior publication survives failure, but its phrase “post-build precipitation scaling” can be implemented as the existing router sequence. `wepppy/nodb/core/climate_build_router.py:160` calls scaling after the mode-specific builder has published. `ClimateScalingService.scale_precip` and related methods then write selected files and controller state separately. For EDDE, clarify that selected scaling and required output validation occur on staged files before the sole publication transaction; later optional report exports must have an explicit disposition and cannot imply a full rollback that did not occur. Test a scaling failure after successful replay/PRISM and a superseded build immediately before publication, comparing previous CLI bytes, mappings and provenance after durable reload.

3. **Medium — define optional seed behavior without contradicting the experimental ADR.** The new application contract allows blank seed, while `docs/adrs/ADR-0091-edde-v2-experimental-daily-replay.md`, **Decision**, requires an explicit station and seed and the standalone adapter declares `seed: int`. The canonical seed authority is `docs/ui-docs/contracts/climate-cligen-seed-contract.md`; its automatic behavior is path-specific and does not choose a new EDDE numeric default. State that the application uses the existing replay default by omitting `-r` when no override exists, preserve explicit values unchanged, and record whether the seed was automatic or explicit. Amend the applicable ADR/application boundary; do not silently resolve blank to an invented fixed or random seed. Require actual command evidence for blank and explicit overrides.

## Additional required clarification

The **Choices and compatibility** normal preflight currently names finite values and positive reference precipitation. Preserve the standalone adapter's existing normal validity checks when selecting the generic native writer: twelve values per field, nonnegative target precipitation, ordered monthly Tmin/Tmax, matching normal periods and units, and retained acquisition identities/hashes. `wepppy/climates/edde/cligen.py:revise_prism` currently checks those inputs; the generic native writer does not replace application eligibility validation. This avoids admitting finite nodata sentinels or mislabeled normal inputs, especially at PRISM coverage edges. This clarification preserves existing behavior and needs no new scientific correction.

## Accepted design and required implementation evidence

- Raw EDDE precipitation/temperature, disclosed grid and bias limitations, station-derived auxiliary fields, and optional Multiple PRISM conform to operator decisions. No source correction or auxiliary-weather feasibility expansion is requested.
- Additive mode/catalog/projection state, an ordinary and single-input capability reader floor, exact stored-graph preservation, and atomic parser rollback are appropriate. Verify old graph identities and reopening rather than reconstructing old graphs with the new live catalog.
- Land-mask eligibility for every required point, per-year private source caches, retained point CSV/manifests and explicit failed attempts fit the existing client. Preserve failing object/year identity before temporary source bytes are discarded.
- Finalization must compare fresh durable projection, period, seed/station, scaling, geometry and acquisition inputs and apply only derived fields. Reports must identify the actual published generation, not relabel an old CLI from a pending form selection.
- Existing router cleanup only preserves selected attempt prefixes. Regression coverage must show EDDE attempts survive both another EDDE build and switching to an older mode.
- Actual Canadian geometry, a PRISM-negative case, authenticated submission/live worker execution, prepared WEPP input hashes, fresh outputs and report/archive/download readback remain required. Standalone feasibility files and successful job status do not substitute for these boundaries.

## Residual risk and coverage limits

This is a preimplementation review, not an implementation or deployment approval. No new runtime code, live request, native execution, publication, archive or report behavior has been tested by this review. Final correctness and security reviews must assess those results and the production-equivalent execution receipt. The known CLIGEN quality/quantization limits remain documented scope, not new blockers.

## Final contract disposition: pass

Re-reviewed the amended EDDE application contract, ADR-0091 application seed amendment and active ExecPlan on 2026-10-14 UTC, before runtime edits. The three medium findings are resolved at the contract level:

- **Scaling envelope:** None, Scalar, Monthlies and Spatial retain their existing prerequisites; AnnualMonthlies explicitly fails local validation before enqueue.
- **Publication:** selected scaling and final CLI validation occur in the EDDE stage, the router skips its second scaling pass, and scaling failure preserves previous files and derived state. Implementation evidence must distinguish subsequent report-export outcomes from that completed climate transaction.
- **Seed:** blank explicitly omits `-r`, explicit overrides pass unchanged, and ADR-0091 now distinguishes application behavior from reproducible experimental runs. Automatic/null provenance cannot claim an explicit seed.

The normal-validity clarification is also incorporated: ordered monthly temperatures, nonnegative target precipitation, positive reference precipitation, matched normal period/units and retained identities/hashes. Source-cache failure diagnostics must be copied into retained attempts before temporary bytes disappear.

No open medium/high contract correctness findings remain. The ancestor checkpoint may proceed. This disposition does not certify implementation, actual-project acceptance or deployment; the evidence requirements and residual coverage limits above remain in force.
