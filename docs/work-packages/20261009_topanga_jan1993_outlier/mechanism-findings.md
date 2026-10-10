# Mechanism Located: CHRQIN Sample Normalization

2026-10-10 UTC. Status: confirmed unrealistic peak-flow defect, now localized
to a source-reconstruction indexing error. No production repair has been made.

## Result

The large January 18 pulse is manufactured in the rainfall-component
normalization inside `CHRQIN`, before channel routing. On the normal initialized
path, `nt0=1`, the routine subtracts the first valid time sample from its
normalization denominator but still adds that sample to the source array.
For a narrow, small-volume rainfall component, the denominator becomes tiny
and the first sample is multiplied by an enormous factor.

The existing error is exposed by the new separation of returned water from
rainfall runoff. It is not a reason to zero small positive rainfall, discard
the hourly estimator, rebuild routing, or change the physical runoff volume.

## Evidence Chain

The paired old/new 45-year traces use each release's own PASS files. All 284
old undisturbed hillslopes were regenerated with `wepp_260803_hill` and match
the retained old PASS fields. The new trace reuses the previously verified
`wepp_261009_hill` PASS set. Both extended-channel runs reproduce their frozen
outlet EBE date, runoff, peak and sediment fields exactly.

The release difference is already large at element 394: 26.33578 m3/s old
versus 674.06232 m3/s new, for daily volumes 201,330.80 and 200,878.56 m3.
It is not confined to element 406 or the final outlet reaches.

A separate observer-only binary was compiled from a clean copy of the released
source. It adds read-only records for January 16-18, 1993: incoming source
maxima, initial state before/after carry, routing coefficients and final state.
It reproduces all **293 comparable output files byte-for-byte** against the
uninstrumented new-release control over the full 45 years. The diagnostic
source patch and build identity are archived; production source was not edited.

The observer locates two large inputs in channels without upstream channels:

| Receiving WEPP element | Direct top hillslope | Reconstructed top inflow maximum, m3/s | Channel output peak, m3/s |
| ---: | ---: | ---: | ---: |
| 304 | 234 | about 185.00 | about 172.68 |
| 365 | 101 | about 795.74 | about 792.37 |

These top inflows come from the direct hillslope reconstruction plus its small
subsurface/baseflow contribution, not a hidden incoming channel. The original
published new-release hillslope peak scalars are only 0.029799 m3/s for H234
and 0.018921 m3/s for H101.

All 128 channels use one spatial routing segment on January 18. The observer
shows no difference at its printed precision between the legacy linear initial
state and the carried initial state for this date. More decisively, the large
headwater input pulses already exist before that channel-state carry call.
Thus the carry mechanism is not the origin of these observed source pulses;
this is not a universal validation of state carry on all events.

## Exact Arithmetic Boundary

The relevant production code is `src/chrqin.for` in the pointwise-source branch:

```fortran
            do it = nt0, ntchr
              ...
              vsum = vsum + qin0(it)
              ...
            enddo
            vsum = (vsum - qin0(nt0)) * dtchr
            if (vsum.gt.1.0e-32) then
              vf = rainvol / vsum
              do it = nt0, int(td/dtchr)
                qin(it) = qin(it) + qin0(it) * vf
              enddo
            endif
```

When `nt0=0`, subtracting the time-zero endpoint is consistent with integrating
positive-time samples. When `nt0=1`, the accumulated first point is already
the 600-second sample. Subtracting it omits a real contributed sample from
the denominator, then the later addition loop reintroduces it with the inflated
multiplier. Changing precision alone does not repair that index mismatch.

H101's captured operands illustrate the defect:

| Operand/result | Value |
| --- | ---: |
| Total hillslope surface volume | 274.970 m3 |
| Scaled rainfall component volume | 0.090845406 m3 |
| Rainfall-only peak operand | 0.0014701501 m3/s |
| Existing support duration | 1,440 s |
| Routing interval | 600 s |
| Unscaled rainfall sample at 600 s | 0.0003059043 m3/s |
| Unscaled rainfall sample at 1,200 s | 0.0000000000554092 m3/s |
| Faulty single-precision normalization denominator | 0.0000000349246 m3 |
| Applied multiplier | 2,601,187 |

The removed first sample contains almost all the sampled rainfall shape. The
remaining denominator is also subject to cancellation, but the primary error
is subtracting the wrong endpoint. No rainfall contribution was approximated
as zero in this diagnosis.

## Actual-Routine Reproducer

`chrqin_probe.for` links the unchanged production `chrqin.o`, `eqroot.o` and
`mixpass.o`, with the release's floating-point flags. It is not a substitute
hydrograph implementation. Captured EVENT/SRC3 records provide the total
volume, rainfall volume/peak, returned-water volume and hourly weights.

The probe compares the actual initialized `nt0=1` path with an `nt0=0`
endpoint-accounting control, keeping every physical operand unchanged:

| Case | Initialized-path maximum, m3/s | Endpoint-control maximum, m3/s | Initialized-path sampled source volume, m3 | Supplied surface volume, m3 |
| --- | ---: | ---: | ---: | ---: |
| H101 | 795.732666 | 0.0185150 | 477,703.625 | 274.970 |
| H234 | 184.997849 | 0.0285749 | 111,605.898 | 624.320 |

The reconstructed maxima match the large observed channel inputs after the
small subsurface/baseflow terms are added. The source-array volume here is
the diagnostic sum of positive-time samples times 600 seconds, not the
watershed's separately tracked daily ledger. That separation explains why
nearly unchanged reported daily volume did not exclude this source-array defect.
It does not establish comprehensive closure of the rest of the legacy pipeline.

Using the old full-runoff volume and peak operands, both hillslopes instead
take the flat branch (`volume / (peak * duration)` exceeds one). That branch
does not execute the faulty denominator. The probe returns the old peak
operands unchanged for both start-index choices. This explains how a legacy
mistake becomes a release-dependent failure when the rainfall component is
isolated. The flat branch has its own known representation limitations; those
are not repaired or made acceptance requirements here.

The `nt0=0` probe is a diagnostic control, **not a proposed production workaround**.
Forcing that flag globally would alter initialization semantics and is not the
bounded correction being proposed.

## Smallest Candidate

Correct the normalization to count exactly the positive-time samples that are
actually added. In the current structure, exclude index zero only if index zero
was accumulated; do not subtract index one on the initialized path. This is
a local arithmetic/indexing correction in CHRQIN, not a new transport interface,
new parameter, rainfall threshold or routing method.

No behavioral patch or corrected watershed replay has been run yet. Before
acceptance, test both start-index paths, the two captured mixed-flow triggers,
small-positive-rainfall transitions, pure-return/no-return controls and relevant
short-support cases. Then verify the January event and complete Topanga record,
with runoff/volume, timing and sediment consequences visible. Ordinary
non-flat rainfall cases can also use this branch, so do not promise universal
parity or accept merely because the 707 m3/s peak disappears. Retain the
existing bounded baseline standard and independent watershed checks; no strict
zero-residual or universal-convergence campaign is implied.

## Artifacts

- `artifacts/mechanism/`: paired release event rows, old hillslope receipts,
  observer records and channel summaries, observer-neutrality receipt,
  observer-only source patch and build provenance.
- `artifacts/source-probe/`: captured EVENT/SRC3 operands, old-operand controls,
  actual-routine stdin/stdout and hashes.
- Full model runs and observer source/build:
  `/wc1/holdouts/topanga-jan1993-version-trace-20261009`.

The live projects and release binaries are unchanged. No new release, vendoring,
deployment or source-repair claim follows from this diagnosis.
