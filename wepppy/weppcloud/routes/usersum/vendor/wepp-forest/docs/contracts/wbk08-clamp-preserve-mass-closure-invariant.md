# WBK08 Clamp-Preserve Mass-Closure Invariant

## Purpose

Define a review invariant for water-balance kernel changes that combine input clamps with output-preservation logic.

This note captures the defect pattern observed in incident package:
- `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/`

## Invariant (Normative)

If a step clamps or suppresses any input term used in closure accounting, then the same step must reconcile dependent output terms and storage deltas so that closure remains conservative on the normalized domain.

For WBK08 process closure:

`residual = inputs_total - outputs_total - storage_delta`

Required condition after normalization/clamp:

`inputs_total(normalized) - outputs_total(reconciled) - storage_delta(reconciled) ~= 0`

within configured tolerance.

## Defect Pattern: Clamp + Preserve

Observed failure class:

1. Upstream/raw input is non-zero (`raw_wmelt > 0`) under inconsistent state.
2. WBK01 applies clamp (`WBK01_MELT_SNOWPACK_CAP`) and sets `normalized_wmelt = 0`.
3. WBK08 preservation path retains a downstream output term (`WBK08_OUTPUT_SCALED_D06_PRESERVED`).
4. Closure sees normalized inputs suppressed but preserved outputs retained.
5. Residual exceeds threshold by construction.

This is a structural reconciliation defect, not a threshold-selection defect.

## Review Gate for Future Changes

Any change to WBK01/WBK08 or adjacent producers must pass all checks below.

0. Producer correctness check
- Clamp statuses are defensive guards against producer-contract violations.
- Producers shall not emit clamp-bait values (for example, positive melt with zero snowpack) during normal execution.
- Clamp fires on production inputs are defect signals to investigate upstream producers, not normal steady-state behavior.

1. Clamp propagation check
- For each clamp status that changes normalized inputs, verify dependent flux producers or reconciliation paths consume normalized values (not stale/raw values).

2. Preserve-path safety check
- For any `*_PRESERVED` path, prove conservation under input suppression.
- If proof is conditional, encode the condition and fail or rescale when unmet.

3. Closure-on-normalized-domain check
- Demonstrate closure with normalized inputs on targeted tuples and non-regression cohorts.

4. Event telemetry check
- Emit machine-readable counters for clamp events and preserve events.
- Emit co-occurrence counter for `clamp_fired && preserve_fired`.

## Phasing: Observation -> Enforcement

1. Phase 1 (current): observation infrastructure
- Land a non-fatal, env-gated co-occurrence counter for `(WBK01 clamp) && (WBK08 preserve)`.
- Also emit preserve-lane raw-input cohort rows (`event_basis=raw_preserve`) when preserve fires with non-zero raw melt but zero clamp suppression, so silent-pass tuples are visible in the same telemetry stream.
- Record suppressed raw-input magnitude buckets (`>=10`, `>=1`, `>=0.1`, `<0.1` mm), max tuple, and status-pair population.
- Preserve existing closure hard-stop behavior and residual threshold unchanged.

2. Phase 2 (after Track 1 producer fix): baseline contraction
- Target watchlist expectation: `>=1.0 mm` bucket converges to zero.
- Remaining events should be noise-floor-only (`<1.0 mm`) and explicitly explained.

3. Phase 3 (promotion gate): structural enforcement
- Promote clamp+preserve co-occurrence to hard error when `|raw_input_suppressed| > gross_error_floor`.
- Set `gross_error_floor` empirically from Phase 1/2 distributions; do not guess.
- This enforcement is independent of, and tighter than, residual-threshold policy:
  - residual threshold remains gross-error guardrail,
  - clamp-magnitude gate is structural invariant enforcement.

## Minimum Instrumentation Expectations

For incident triage and release review, provide at least:

- Boundary probe row at normalization site (raw vs normalized terms).
- Pre-assert closure tuple row (inputs/outputs/storage/residual).
- Preserve-path status rows with tuple keys (`year`, `day`, `ofe`).
- Per-run counters for:
  - clamp events by `status_message`
  - preserve events by `status_message`
  - co-occurrence events (`raw_input > 0 && normalized_input = 0`)

## Policy Guidance

- Do not treat threshold relaxation as remediation for this class.
- Threshold sweeps are diagnostic tools for boundary mapping only.
- Remediation is complete only when the clamp+preserve path conserves mass on normalized inputs and clears non-regression gates.

## Rain-Routing Contract (2026-05-15)

- Candidate 1 contract: rain water enters the kernel via the rain channel; `wmelt` carries only energy-balance snowmelt.
- Rain-on-snow energy interactions remain in producer-side snowpack state updates; they do not alias rain mass into `wmelt`.
- Track 1D implementation evidence/report:
  - `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1D_rain_routing_fix.md`
- Promotion note:
  - Candidate 1 resolved the original day-84/day-347 hard-stop in staged replay, but did not yet satisfy Phase-2-style contraction targets (`>=1.0 mm` co-occurrence buckets still non-zero).

## Current Status (2026-05-15)

For `insensible-aliquot` `p26`:

- Boundary probe confirmed `raw_wmelt > 0` and `normalized_wmelt = 0` on failing tuple.
- WBK08 preserve status recurred pre-failure.
- Phase 1 landed: env-gated WBK08 clamp+preserve surveillance counter with bucketed suppression telemetry and per-run summary.
- Track 1 producer trace landed (diagnosis-only): `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1_wmelt_producer_diagnostic.md`.
- Track 1B rain-on-snow conflation falsification landed (diagnosis-only): `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1B_rainmelt_conflation.md`.
- Track 1C rain-routing contract determination landed (diagnosis-only): `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1C_rain_routing_contract.md`.
- Track 1D Candidate 1 producer fix attempt landed (implementation lane): `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1D_rain_routing_fix.md`.
- Track 1G WB30 bisection and Gate-2 fix landed (implementation lane): `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1G_wb30_fix.md`.
- Track 1H Phase 3 promotion landed (implementation lane): `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1H_phase3_promotion.md`.
- p26 package disposition: **resolved under Candidate 1** (`rain -> rain channel`, `wmelt -> melt-only`) for the incident closure defect class.
- Gate 2 (`preserve-path conservation under input suppression`) is satisfied at production-cohort scale for this defect class (`477/477` replay pass after WB30 Shape-A fix).
- Phase 3 is now operational by default (not env-gated): clamp+preserve+suppress `> gross_error_floor` emits `WBK08_PHASE3_FAILFAST...` and `ERROR STOP 206`.
- Chosen `gross_error_floor`: `0.1 mm` (`wbk08_clamp_preserve_bucket_low_mm`), justified by zero-event post-Shape-A representative baseline and stable pre-declared bucket boundary.
- Correctness-over-completion is now an explicit operational invariant: tuning `gross_error_floor` to suppress firings is prohibited.
- Gate 0 (producer correctness) resolution lineage:
  - **Delivery-side enforced** under c2f2bf6d ("Candidate 1 rain-routing contract"; same package as Tracks 1A–1J above). Rain water enters the kernel via the rain channel under all conditions; `wmelt(iplane)` carries only energy-balance snowmelt.
  - **Consumer-side admission gate — tri-hillslope-validated, vendoring blocked.** R01 (package `docs/ablation/20260516_carved-letter_hillslope_runoff-amplifier-c006-bisect/`, status `vendoring-blocked-cohort-regression` as of 2026-05-16). The `sumrun` rain-event admission gate consuming producer event classification (`norain(iplane)`) was validated locally against H347 (16-OFE cascade-tail amplifier exemplar), p26 (rain-routing fix non-regression), and H16 (normal baseline). Phase 6 vendoring attempt against a 40-hillslope WB-05B sample (10/project) revealed catastrophic closure-residual regression on 30 of 40 hillslopes (residuals jumping 100–58,000% on cochlear-beriberi/moth-eaten-blackhead/ordained-incentive projects; only uninsured-deformation passed cleanly). R01 source changes remain in the `/tmp/wepp-forest-r01-current/` worktree and are NOT committed to master. The consumer-side admission gate is therefore NOT enforced in production; the producer-correctness Gate 0 line of work for the cascade-tail amplifier case is open pending cohort-regression triage of R01.
  - **Dry-day case open** under follow-up package `docs/ablation/20260516_carved-letter_hillslope_dry-day-mass-balance-defect/`. R02 Phase 5 evidence in the R01 package shows a separable mass-balance violation on days with no rain anywhere on the hillslope; it predates R01 and persists after R01 (R01 slightly improves it but does not close it). B.1 Phase 1 localized the dominant bucket to `Total-Soil` at the daily-update boundary (`watbal_hourly.for` end-of-day epilogue) on both H347 cascade-tail OFEs and the six watershed-outlet recession-dip dates. The retired `20260516_carved-letter_pw0_watershed_recession-dips` package's watershed-side `wsarea`-clobber hypothesis was superseded by hillslope-side R02 P5 cross-link evidence; key dip-date evidence preserved under the B.1 package's `artifacts/logs/inherited/`.
  - **Abandoned reference**: `docs/ablation/20260515_winter_producer_overcomputation/` was abandoned 2026-05-16. Its premise (live `WBK08_PHASE3_FAILFAST` firings to triage) was contradicted by its own `O1_phase3_firing_manifest.csv` showing `phase3_fired=False` on all six probe cases. The narrative built on top of that manifest is treated as agent hallucination. Directory preserved on disk with an `ABANDONED.md` marker for audit traceability; do not cite as evidence. Legitimate producer-side winter investigation continues under `docs/ablation/20260516_winter_day_end_melt_aggregation_sign_defect/`, which uses source-verified `winter.for` `ngtvML/pstvML` math-defect evidence from the Dun-dissertation crosswalk (`docs/winter-codes-scientific-review.md` §4.A) as its evidence base.
  - **Winter producer math defect (latent in production)**: 2026-05-16, `winter.for` `ngtvML/pstvML` signed-comparison + multiplier-sign math defect identified via Dun-dissertation crosswalk (`docs/winter-codes-scientific-review.md` §4.A) and remediated under `docs/ablation/20260516_winter_day_end_melt_aggregation_sign_defect/`. Empirically latent: WB-05B `1166`-hillslope cohort scan showed `class2=class3=0` across `21.7M` winter-active rows (`snowd` does not produce negative `hrmlt` in current production data, so the patched branch is unreachable). Fix is correct-when-it-fires, no-op otherwise.
- Track 1J broader sweep executed at `64b86eaf` against the four-project WB-05B forest cohort (`1166` numeric hillslopes): `1166 ok / 0 failed / 0 ERROR STOP 205 / 0 ERROR STOP 206 / 0 Phase 3 firings`.
- Track 1J outcome artifact: `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1J_broader_sweep.md`.
- Release artifacts rebuilt from the same commit and tag anchor (`wb-p26-shapeA-functional`):
  - `release/wepp_260514` sha256 `364ee4e83be687444e835d3ca78fb3f9b56b8fb4842b32fc5504d136cc6b68d3`
  - `release/wepp_260514_hill` sha256 `cc08f4941684ff61c20ad13e938dfdc468515acf57ea90067a32c3c0857e3086`
