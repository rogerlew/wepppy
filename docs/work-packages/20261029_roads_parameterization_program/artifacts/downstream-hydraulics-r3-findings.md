# Same-format downstream conductivity controls

All three standalone treatments are rejected. The buffer cap recovers most
meaningful low-load misses but worsens passing controls and does not resolve
small-reference excesses. Combining it with fixed fill conductivity does not
remove that tradeoff. The original generated baseline and acceptance criteria
remain unchanged.

| Treatment | Meaningful high recovered /5 | Meaningful low recovered /48 | Small excess recovered /43 | Passing controls retained /20 | Physical pass /116 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fill adjustment disabled | 0 | 0 | 8 | 19 | 115 |
| Buffer conductivity capped | 0 | 47 | 0 | 17 | 116 |
| Both | 0 | 44 | 0 | 17 | 116 |

Every declared input/output was rehashed, the changed fields were independently
read back and restored against their source profiles, all completed LOSS records
were reparsed, and all completed native physical audits were recomputed.
[Verification](downstream-hydraulics-r3-verification.json) retains 347 physical
passes and the one native failure; the failed run is not counted as zero sediment.

The fill-only control loses Flagstaff sand/outunrut/paved/no traffic: 1.16384
kg/year versus a zero reference (ceiling 1 kg/year). Buffer-only and combined
lose the Denver and Flagstaff counterparts and site sand/outunrut/gravel/high.
The latter increases to 425.276 and 418.810 kg/year respectively, versus a
20.2164 kg/year reference. No full-matrix acceptance or parameter promotion follows.

The failed conversion gate is separate from these results. These 348 runs use
only the original generated 9002 format, changing fill `ksatadj`, upper-200-mm
buffer K, or both. They never substitute legacy role materials or use the new
road-conductivity divisor. See [ADR-0120](../../../adrs/ADR-0120-roads-generated-hydraulic-sensitivity.md)
for the exact hypothesis and limitations.

## Newly exposed native failure

Fill-only treatment of site/1718465/outunrut/gravel/no traffic stops during year 7,
after the 17 January 2006 routing message, with SIGFPE at `depend.for:185`.
The released binary reproduces the same failure and exact partial output hashes
in a fresh directory. GDB identifies `xdend = xdend - f/df` as the failing step:
`f=0.127341852`, `df=-2.80259693e-45`, and `xdend=7.24766e32`.
The quotient exceeds binary32 range. This is a solver step outside its physical
interval, not a water-accounting guard stop.

The native scalar fixture reproduces the failure with the same float32 inputs.
Its observation-only variant visits trial positions 1, 0.0600000024,
1.4788e11, 1.0353e22 and 7.24766e32. Both scalar variants trap. An independent
80-digit integrating-factor solution for this constant-coefficient case gives
an interior root at 0.050115891779652795, within `[0.050000000745..., 1]`.
This establishes that an interior solution exists despite the failed Newton search.

Retained artifacts:

- [Portable full-run inputs](depend-failure-r3-inputs.tar.gz) and [execution receipt](depend-failure-r3-receipt.json).
- [GDB observation](depend-failure-r3-gdb.txt).
- [Scalar fixture and independent root](depend-scalar-r3-result.json) with [reproducer](depend_scalar_repro_r3.py).

No native patch or binary re-release has been made. The current 840-case baseline
still passes its physical checks; this additional experimental configuration
exposes an uncovered solver path. Historical prevalence and production incidence
are not established by this fixture.

## Next action

Prioritize a bounded DEPEND root-search ablation before additional parameter
combinations. Preserve the deposition law and floating-point traps, independently
validate root location and branch behavior, and retain full-run mass/accounting
checks. Do not suppress the exception or cap exported sediment. The next
[solver specification](depend-root-ablation-r3-plan.md) defines the repair gates.
The broader conductivity tradeoff remains unresolved; no generated-soil rule or
UI specification is ready for approval.
