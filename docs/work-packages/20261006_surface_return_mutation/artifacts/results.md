# hand-to-mouth-drought: corrected-build mutation results

Completed 2026-10-06. All **1,088 eligible mutations and 280 baselines** completed
the full 45-year period; zero model failures. Both sides of every mutation pair
use the surface-return peak correction. The original Ksat ±1% and paired-cover
±0.01 design is preserved. No rrinit or depression-storage changes were made.

## Figures

- [Figure 1 — event runoff](figure-1.png)
- [Figure 2 — event sediment delivery](figure-2.png)
- [Figure 3 — hillslope peak flow](figure-3.png)

All three PNGs were opened and visually checked after generation. The original
plotting floors, mutation markers, response-opacity convention and ratio guides
are retained. Figures 1 and 3 explicitly disclose 86 and 181 eligible pairs
outside the original axis bounds; their statistics include those pairs.

| Figure / response | Eligible positive pairs | Outside 0.5–2× | Outside 0.2–5× |
| --- | ---: | ---: | ---: |
| 1 / runoff | 218,974 | 453 (0.207%) | 34 (0.016%) |
| 2 / sediment | 128,469 | 372 (0.290%) | 90 (0.070%) |
| 3 / peak | 200,932 | 1,021 (0.508%) | 218 (0.108%) |

The complete event ledger has 225,659 outer-paired rows: 225,042 paired,
320 baseline-only, and 297 mutant-only. These are retained separately; they
are not silently converted to zero. Sediment has 549 baseline-positive-only
and 619 mutant-positive-only rows (including zeros or absence on the other
side). Printed EBE sediment remains quantized to 0.1 kg/m; 70,424 plotted
sediment pairs are exact ties.

## Interpretation

The corrected-build peak plot is substantially tighter at high peak rates,
but it does **not** eliminate the broader sensitivity problem. Of the 1,021
twofold departures, 594 retain runoff within 5% of baseline. Those are screening
results, not adjudicated defects.

Relative to the original August census, fivefold peak departures fall from
604/199,086 (0.303%) to 218/200,932 (0.108%). Twofold departures do not fall:
989/199,086 (0.497%) previously versus 1,021/200,932 (0.508%) now. Runoff's
twofold-tail rate is essentially unchanged, while the sediment twofold-tail
rate rises from 0.195% to 0.290%.

Most remaining fivefold departures have **no surface return in either run**:
184 of 218. The other 34 have positive raw surface return on at least one side.
The original census also reported 184 fivefold departures without return.
Current fivefold-tail peaks reach 17.39 mm/h on the baseline side and
21.29 mm/h on the mutant side; the most conspicuous residual tail is not at
the largest modeled peaks. This pattern is consistent with a targeted
surface-return correction leaving other sensitivities unresolved; it is not
mechanism adjudication of individual residual events.

Within the central 0.5–2 peak-ratio band at baseline peaks of 30–100 mm/h,
Ksat incongruence (including ties, as in the original convention) is now:

| Stratum | Current count / denominator | Current share | August share |
| --- | ---: | ---: | ---: |
| Unburned | 165 / 3,529 | 4.68% | 24.1% |
| Burned | 234 / 10,437 | 2.24% | 26.0% |

These historical comparisons are descriptive: although shared input files match
byte-for-byte, the source lineage and observation grain differ. They are not a
same-lineage patch-only causal estimate. This is one enriched-discovery site,
with clustered event rows; no cross-site prevalence, physical-accuracy,
watershed-outlet or return-period claim follows.

## Validation and provenance

The observational companion passed byte-identical parity for seven canonical
outputs on both burned and undisturbed H106 histories. All 1,368 final traces
were checked against generated reports. Maximum absolute differences were
0.000507 mm runoff and 0.000503 mm/h peak, within the declared 0.0006-unit
readback tolerance for 0.001-unit printed precision plus floating-point scaling.
Unique keys, finite/nonnegative values, positive-event coverage, mutation
readback, binary identities and trace hashes were verified.

The execution coordinator was interrupted **after all model runs and independent
aggregation completed**, with no child model process left. It was spending time
fsyncing a progress update for each already completed future. The incomplete
progress acknowledgment count is preserved, not treated as the run count.
Independent final reconciliation verifies exactly all 1,368 expected terminal
identities and their hashes. No model run was terminated by this interruption.

Eight research-harness tests pass. The mutation engine's nonintegration subset
passes 16 tests. The broader focused file had 17 passes and one retained
historical executable-hash integration failure; see [validation review](validation-review.md).
No production source, binary or project was modified or deployed by this repeat.

Authoritative raw evidence: forest
`/workdir/hand-to-mouth-fixed-census-20261006-v2`.
The initial invalid observer attempt is retained separately and excluded.

Compact evidence:

- [Methods and compatibility limits](methods.md)
- [Figure statistics](figure-statistics.json)
- [Final execution reconciliation](execution-summary.json)
- [Event aggregation](aggregation.json)
- [Residual tail context](tail-context.json)
- [Build identity](build.json) and [observer parity](parity.json)
- [Artifact locations and hashes](artifact-manifest.json)
- [Input comparison](input-comparison.json), [frozen plan](plan.json), and [input hashes](inputs.json)
- [Terminal inventory](terminal-inventory.csv) and [report readback](report-readback.json)

The fixed binary is `440fcebb…8b2307`; the observer companion is
`81c83036…d1bdd7` (full hashes in build.json). Compiler: GNU Fortran 13.3.0,
normal fixed-build flags; observer patch is retained. Remote WEPPpy HEAD during
execution was `e4b5dd166db610186affebb6a0ac85f446284d85`; local documentation
checkout was `2ef88fade1136b07cfd51346d3fb60a091177860`. The mutation, planning
and hashing modules match byte-for-byte across the two checkouts.
