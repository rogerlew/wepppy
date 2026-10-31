# Restriction provenance and boundary-flag control

Completed 2026-10-31 under the Roads program ExecPlan. The experiment retains
`wepp_261029` revision 2, SHA-256
`819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715`.
No native binary, production parameter, acceptance rule or withheld material changed.

## Seven-material provenance audit

Frozen generated `.sol` headers, companion build logs, current SSURGO writer and
native input/drainage code agree on the following lineage. Source file hashes
match the development manifest. This is retained generation evidence, not a new
SSURGO query or independent field verification of geology.

| MUKEY | Header/detector evidence | Emitted profile depth (mm) | Boundary conductivity (mm/h) |
| --- | --- | ---: | ---: |
| 1718465 | R horizon; component metadata Lithic bedrock; 0.42 µm/s | 400 | 0.00151 |
| 1856573 | R horizon; component metadata Lithic bedrock; 0.035 µm/s | 800 | 0.00013 |
| 1718510 | A2 mineral horizon triggers threshold; metadata N/A; 0.91 µm/s | 400 | 0.00328 |
| 53949 | Bt mineral horizon triggers threshold; metadata N/A; 0.91 µm/s | 400 | 0.00328 |
| 2711184 | No threshold-triggered horizon; last Cr Ksat estimated | 1600 | 0.01 |
| 2711250 | No threshold-triggered horizon; last H4 Ksat estimated | 2600 | 0.01 |
| 1718494 | No threshold-triggered horizon | 1600 | 0.01 |

All seven have `slflag=1` and `ui_bdrkth=10000 mm`. The detector uses conductivity,
not restriction type: it retains a first valid low-Ksat horizon, then truncates
before a later horizon below 2 µm/s. Component `reskind` is attached as metadata;
it does not select a different mineral versus lithic boundary formula. `N/A` does
not establish absence of geological restriction. A Cr horizon with estimated
conductivity also illustrates why “no detected horizon” cannot mean proven free
drainage.

For detected restrictions, the writer converts µm/s to mm/h by multiplying by 3.6,
then divides by 1000 as a historical bedrock-proxy heuristic. For no detection it
writes 0.01 mm/h anyway. The documented 2023 writer change established these
rules; this audit does **not** identify the `/1000` as an accidental unit bug.
The imposed 10 m thickness is not measured depth to bedrock. Native `input.for`
converts it to meters and conductivity to m/s; `perc.for` combines boundary and
bottom-soil conductivity differently for hourly and daily modes.

7778 terminal-depth padding is another distinct operation: minimum 210 mm before
rounding upward to a 200 mm multiple, therefore at least 400 mm. It explains the
400 mm profile retained above the low-conductivity A2 in 1718510. The subsequent
200 mm horizon insertion preserves the existing profile depth and restriction;
it did not introduce this truncation/padding. No changes to either operation were
made. Canonical interpretation is clarified in
`wepppy/soils/ssurgo/ssurgo.md`, “Restrictive Layer Analysis” and its provenance note.

## Declared 52-case control

Use all existing diagnostic cases for the three no-detected materials: 2711184,
2711250 and 1718494. Change only `res_lyr.slflag` from 1 to 0 in every OFE. All
stored thickness/conductivity values, generated horizons, normalized 200 mm
breaks, erosion coefficients, road treatment and hourly/PMET/snow inputs remain
exact. Native initialization zeroes/ignores the inactive boundary inputs. This is
an endmember diagnostic, not a conclusion that those materials have no deeper
restriction. Neither mineral nor lithic classes receive the treatment.

This differs from historical boundary screens, which varied conductivity to
source-derived endpoints and encountered subsequently repaired native failures.
The new contrast directly tests the enabled flag on the fixed engine, with no
chosen conductivity magnitude or sediment fitting.

**Result: reject.** 47/52 new runs completed and passed physical checks. None of
the 51 original misses recovered; the one passing control remained passing.

| Original group | Cases | Completed physical passes | Within magnitude criteria |
| --- | ---: | ---: | ---: |
| Meaningful low | 41 | 36 | 0 |
| Meaningful high | 1 | 1 | 0 |
| Small exceedance | 9 | 9 | 0 |
| Meaningful passing control | 1 | 1 | 1 |

Independent readback verified all 52 paired input/output inventories, recomputed
native audits for completed outputs and checked that only the boundary flag
changed in actual soil files. Incomplete native outputs were never counted as
zero sediment or valid comparisons. Among the 47 completed cases, median paired
changes (treatment minus baseline, m³/year) were:

| Role | Lateral outflow | Deep percolation | Surface outflow |
| --- | ---: | ---: | ---: |
| Road | -45.86 | +43.52 | +0.14 |
| Fill | -27.91 | +5.47 | +1.74 |
| Buffer | -53.31 | +47.77 | -0.003 |

This shifts water partition substantially without solving sediment mismatch.
The table excludes five failed cases, so it is descriptive, not a full-panel
water success claim. Internal OFE flows cannot be summed as watershed export;
apparent WAT residuals are not complete water closure.

## Native failures and continuation

Five distinct consumed decks stop at `HOURLY_WATER_UNMET`, all Denver gravel/no
traffic, OFE 2, day 190. They remain failures and have retained decks/stdout/output.

| Material | Designs | Hour | Withdrawal magnitude (mm) | Available stock (mm) |
| --- | --- | ---: | ---: | ---: |
| 2711184 | inbare, inveg, outrut | 18 | 0.440738 | 0.260763 |
| 2711250 | inbare, outrut | 20 | 0.303735 | 0.172346 |

These approximately 0.180/0.131 mm funding deficits are materially larger than
the prior roundoff-scale hourly/Penman failures. `watbal_hourly.for:525–534`
compares signed withdrawal against the available nonnegative layer stock before
allocation and stops when it cannot fund the request. This observation identifies
a failing configuration, not yet a proven cause in the daily producer, hourly
allocation, boundary physics or input assumptions. All corresponding unchanged
baseline cases completed. No guard tolerance, clipping or binary change is justified
by this diagnostic alone.

Next priority: reproduce one exact deck for each material under an isolated native
instrumented build and trace daily runoff/infiltration demand, hourly allocation,
percolation and lateral storage around day 190. Retain the five-deck panel as a
regression target, plus unchanged-boundary controls. Determine whether the guard
exposes an unfunded producer request, a timing mismatch or an invalid parameter
combination before proposing a repair. Keep the released binary pinned and do not
repeat conductivity/flag sweeps as a sediment remedy. Any binary adoption needs
its existing native work-package validation and release evidence; any soil-rule
adoption needs class-specific physical justification and an ADR.

The general magnitude gate remains unmet. Withheld validation and the human UI
specification/layout gate remain intact.

## Retention and reproduction

- `restriction_provenance.py` → `restriction-provenance-v1.json`: seven source
  headers, class interpretation, source hashes and boundary-formula readback.
- `restriction-source-retention-v1.json`: exact source `.sol`, `.log`, writer and
  native snapshots, including original paths. The first audit failed because the
  native checkout was outside the container mount; verified source snapshots
  resolved that. Failed pre-execution logs are retained; no model cases were lost.
- `no_detected_boundary.py --declare`, then without that flag, through
  `wctl exec -T weppcloud /opt/venv/bin/python`: frozen 52-case experiment.
- `analyze_no_detected_boundary.py`: independent native/readback verification.
- `no-detected-boundary-v1-{declaration,summary,analysis,failures}.json`: cases,
  hashes, measurements and explicit failure disposition.
- Verified archive: `/wc1/runs/ro/roads-parameterization-program-20261031/restriction-boundary-v1.tar.gz`,
  manifest/receipt sidecars; repository receipt `restriction-boundary-archive-v1.json`.
  Prior baseline outputs remain at the frozen source paths and earlier receipts.
