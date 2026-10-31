# D2: Equivalent-plane length origin

## Finding and scope

The proposed local transfer reference exposed a smaller, directly testable defect.
IRS passes CDIST2 `SLPLEN(0:mxplan)` to EPLANE, whose dummy was `SLPLEN(mxplan)`.
Dummy index 1 therefore read caller index 0 and shifted local lengths relative
to their hydraulic coefficients. With a zero sentinel and two OFEs, this can
omit the road and assign its length to the fill coefficient. Both declarations
are present at earliest tracked commit `c70bad57b` (2020-08-25); earlier origin
is unknown. IRS is the sole active caller found in the source audit.

The independent integral probe passes 2/8 cases with released source and 8/8
with the corrected bound. The two old passes are homogeneous controls. Corrected
answers are independent of the zero-index sentinel and work for connected groups
starting after OFE 1. See `D2-eplane-probe.json` and `probe_eplane_origin.py`.

## Predeclared factorial results

`U2-U3-science-contract.md` froze the origin-only and combined comparisons before
execution. Each lane ran all twelve retained fixtures for all sixteen years.

| Measure | U2: origin only | U3: origin plus continuous recession |
| --- | ---: | ---: |
| Complete runs | 12/12 | 12/12 |
| Completed hourly accounting states | 210384 | 210384 |
| Negative linked total FIN | 0 | 0 |
| Daily unfunded requests | 0 | 0 |
| Negative incremental recession differences | 295 | 413 |
| Maximum matched-stage stock residual, mm | 0.000298984 | 0.000317930 |
| Invalid published water rows | 0 | 0 |

Every case has the full calendar and verified output hashes. Negative incremental
recession differences are retained; they are distinct from negative total FIN.
No assertion of universal local ownership follows from this bounded panel.
The U1-only unsupported source remains a real rejected control, not erased history.

## Source candidate and validation

The working native source now contains the lower-bound correction and removal
of QINF's extra unity cutoff. No formula coefficients, soil inputs, event-state
rules or output formats change. New permanent native tests pass 13/13; the
instrumented combined candidate passes 75 existing Roads/accounting and delayed
return tests. A clean uninstrumented candidate reproduces every U3 output hash
for all twelve cases. Both executable smoke tests and ELF interpreter checks pass.

Builds must be sequential because the targets copy shared include files.
An initial simultaneous build was discarded. The clean sequential rebuild uses
original watershed and hillslope capacities and restores watershed includes.
`D2-candidate-build.json` records source patch, exact command and binary hashes.
The source fixture/spec and durable contract are in `tests/`, `docs/specs/source/`
and `docs/contracts/hillslope-recession-geometry-contract.md`; WEPPpy ADR-0119 is
proposed. No release files or WEPPpy vendored binaries are changed.

## Remaining acceptance

Full native suite passes 1073 tests (two warnings), watchlist passes 18/18,
and Disturbed passes 99 tests (two warnings). The unchanged 840-case Roads
panel passes every physical audit. Magnitude remains below acceptance: 713/766
meaningful and 31/74 small references, versus 719/766 and 30/74 in revision 2.
Two cases recover and seven regress. Of 96 misses, 48 are meaningful low, five
meaningful high, and 43 small excesses; 71 misses are outunrut configurations.
A uniform erosion reduction therefore has no support from this panel.

Fresh Cedar Creek hillslopes complete 864/864; the 24-year watershed and semantic/
particle/source review remain in progress. Preserve
all existing criteria and withheld materials. The larger cascade redesign is
deferred because the confirmed array-origin defect explains the target failure.
