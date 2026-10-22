# Actual soil/channel coupling control review

Independent scientific review, 2026-10-21. Diagnostic evidence only; no production
source change or new soil/MC storage authority. Native checkpoint: `e6dc19008`.

## Findings and disposition

**High — signed coupling remains unresolved with the actual soil producer.**
Eight complete two-year runs use native WSHCQI, optional WSHIRS, daily/hourly
WATBAL, and MC4 WSHCHR. A naturally dry day generates a material transmission
request without prescribing a loss or activating WSHIRS artificially. Negative
raw outlet states and the existing nonnegative export clipping produce a large
raw/export difference. This is sufficient to keep full-package closure open.
It does not establish that all clipping is caused by signed loss: the wet-day
positive-source controls also clip, and coefficients differ between days.

**High — separate channel-plane/element runoff alias is confirmed.**
An additional read-only writer/read trace proves that a dry receiving channel
can consume the preceding channel's depth through the shared `runoff` array.
This must be isolated before proposing a correction to the apparent positive
post-soil runoff omitted by the `norun` gate. Exporting that inherited value
would not be a defensible repair.

These findings do not reverse the scoped source/publication/reference checkpoint
approval. They identify remaining producer/coupling boundaries; neither the MC
recurrence nor clipping was changed in these experiments.

## Control and evidence integrity

Retained root:
`/workdir/watershed-physical-water-repair-20261021/mc-coupled-soil-control-v1/`.
`receipt.json` contains all five observed days, soil terms, MC increments and
coordinate jumps; `manifest.json` hashes 1,857 source, script, binary, input and
output files. It supersedes `manifest-initial-superseded.json`. Failed deck
preflights are retained separately and excluded from accepted cases.

The native `tools/physical_water_case.py` generator supplies two years, 1980–81,
and unchanged soil/climate parameters. Channel-specific deck records are
duplicated to form H1 → C1 → C2. The paired receiving-boundary hook replaces C1's
hydrograph and volume metadata only while C2 executes on the selected day:

- June 7, day 159: generated rain 25 mm; normal WSHIRS branch executes.
- June 8, day 160: generated rain zero; normal WSHIRS branch remains skipped.
- Early/late six-point pulses at 600-second resolution each integrate to 100 m³,
  including the inherited time-zero half-step. `tmpvol=100` and `watdur=3600`
  accompany the pulse; the native receiving duration rule remains active.
- The original C1 hydrograph, volume and duration are restored after C2 routing.
  This is a synthetic receiving control volume, not a whole-network mass test.
- Both daily and hourly **soil** modes use MC4 and lateral interpretation
  `mofapp=1`; these eight runs do not cover MC5 or lateral mode 2.

All eight runs completed. Independent QA verified 731 exact climate/hillslope
dates and 731 daily rows per channel, ending 1981/day 365. Two independently run
no-hook baselines preserve every C1 hydrograph and channel-balance row across all
eight hook cases. Observer-on/off comparisons match all 300 native file pairs
byte for byte. See `observer-off/receipt.json` and the separate
`mc-coupled-soil-qa-v3/receipt.json` under the experiment parent.

Full `qs` and `q1` arrays include intervals copied by MCFAST. The validator
reconstructs logical recurrence eligibility for every interval; it does not
mistake skipped computation for omitted physical forcing. Header identity,
finite values, complete frames, 144 steps, and soil-fin step sequences are
checked. Early/late soil, transfer, fin and WSHIRS traces are byte-identical
within each day/soil-mode pair.

## Observed receiving-channel event-day accounting

Volumes are m³. “Executed lateral” means signed net forcing inserted in the MC
recurrence; it is not an independently established physical withdrawal.

| Day / soil mode / placement | Soil-derived transmission request | Executed lateral | Raw outlet | Accepted outlet | Export clipping |
| --- | ---: | ---: | ---: | ---: | ---: |
| Wet / daily / early | −0.000008 | 23.121918 | 122.999299 | 126.385057 | 3.385759 |
| Wet / daily / late | −0.000008 | 23.121918 | 107.690494 | 110.979010 | 3.288516 |
| Wet / hourly / early | 0 | 23.103256 | 123.002943 | 126.370953 | 3.368011 |
| Wet / hourly / late | 0 | 23.103256 | 107.695460 | 110.983928 | 3.288467 |
| Dry / daily / early | 37.890755 | −37.678626 | 62.995619 | 101.347475 | 38.351856 |
| Dry / daily / late | 37.890755 | −37.678626 | 47.666610 | 87.035078 | 39.368468 |
| Dry / hourly / early | 38.841900 | −38.626482 | 62.066941 | 101.298528 | 39.231588 |
| Dry / hourly / late | 38.841900 | −38.626482 | 46.738356 | 87.007684 | 40.269328 |

No logical source intervals are skipped on these event days. Point quadrature
includes the inherited lateral endpoint, so its integral need not equal the
negative daily request. That difference is retained, not normalized away.

The dry daily early/late MC increments are −0.674239 / +14.654768 m³; the hourly
values are −0.693435 / +14.635151 m³. Corresponding start-coordinate jumps are
−1.083557 and −1.101775 m³. Therefore a same-day early/late export difference
alone is not a mass-loss result. Event-day summed recurrence residuals are about
1e−5 m³; the algebraic identity includes clipping and all these terms. Its
closure is not proof of nonnegative physical inventory or a complete soil budget.

The dry daily/hourly soil-fin allocation requests are 100.001487 / 98.453385 m³;
Dp is 0.005492 / 0.002801 m³; soil evaporation is 3.614547 m³ in both; lateral
release is 0.001749 / 0.001682 m³. Pre/post liquid stores, frozen stores, rainfall,
melt, transpiration, residue evaporation and surface return are retained in the
receipt. Fin observations are inputs to allocation, not per-layer executed
withdrawals, and do not justify a complete soil-budget closure claim.

## Separate runoff indexing finding and bounded next candidate

Native source chain at checkpoint `e6dc19008`:

1. `src/wshdrv.for:651` resets the shared array each day; `:686` resets `norun`.
2. C1 uses `iplane=1`, `ielmt=2`; `src/wshdrv.for:1004` copies
   `runoff(1)` into `runoff(2)`.
3. C2 uses `iplane=2`, `ielmt=3`. On dry days, the condition at
   `src/wshdrv.for:932` skips WSHIRS and its `src/wshirs.for:172` reset.
4. `src/watbal_hourly.for:352` reads this inherited `runoff(2)`;
   `:359` subtracts it from infiltration. `:896` and `:933` raise `norun`
   for newly generated surface drainage, not for the inherited value.
5. `src/wshdrv.for:980` tests `norun`; its else branch at `:1033` forwards zero.

On dry day 160 the read-only trace records the exact C1 write and C2 pre-soil read
as 0.0013530924916267395 m, with C2 `norun=0`. At C2's area 1144.3000488 m² this
is 1.54834380 m³. On adjacent dry days 158/161/162 the inherited depths correspond
to 4.24448551 / 3.28242424 / 3.20414127 m³; with no new surface return, those
positive post-soil values are not forwarded. On wet day 159 WSHIRS recomputes
the receiving depth. `runoff-alias/receipt.json` retains two full runs and exact
parity against every original native and observer file.

The smallest candidate to test is to initialize the current channel's plane
runoff before the optional WSHIRS calculation, with an accompanying audit of
`chnrun` and other shared plane/element scratch values. First prove that no
legitimate producer is erased and that upstream reports remain intact. Required
causal controls are dry/wet, small/material runon, multiple channel counts and
both soil modes, followed by these eight controls and native gates. Do not fix
this by merely changing the `norun` predicate, and do not reduce `rtrans` after
WATBAL has already credited soil. No candidate behavioral edit was made here.

After the producer boundary is corrected and remeasured, complete signed
coupling still requires an explicit requested-versus-accepted exchange design
that reconciles soil credits with channel acceptance while preserving the
approved MC authority. Scalar hydrograph rescheduling alone does not prove
segment availability. The prior 44-year observations cannot replace this
controlled timing comparison; this control in turn does not replace broader
MC5, mode-2, network and coefficient-transition coverage.

## Reproduction

Frozen scripts are under `scripts/`. Set `COUPLED_CONTROL_ROOT` to a directory
containing those scripts, `WEPP_NATIVE_ROOT` to the native repository,
`WEPP_CANDIDATE_ROOT` to the v5 source/build tree, and `COUPLED_CONTROL_OUTPUT` to
a new output directory. Run `run_coupled_soil_control.py`, then
`extend_coupled_soil_control.py`, `validate_coupled_soil_control.py`,
`check_coupled_observer_parity.py`, `check_coupled_runoff_alias.py`, and
`finalize_coupled_manifest.py`. The initial script refuses an existing output
directory. Final scripts add path overrides only; retained generated artifacts
are the evidence for this execution.
