# Hillslope recession and equivalent-plane geometry

Status: accepted for the owner-authorized Linux `wepp_261029` artifact revision 3.
Source `6112b68bce0e21a77f510bde5c24af067a47a647`; release delivery gates remain separate.

## Equivalent-plane array contract

IRS passes the whole CDIST2 `SLPLEN(0:mxplan)` array to EPLANE. EPLANE must
use the same zero-based dummy bound; index zero is not an overland flow element
(OFE). `ALPHA` remains one-based. Every index from `IBPLN` through `IEPLN`
must pair that OFE's local length with its own hydraulic coefficient. Do not
substitute cumulative or reporting lengths. Changing the index-zero sentinel
must not affect the answer, including when the connected group begins after OFE 1.

The former one-based dummy shifted lengths relative to coefficients. Homogeneous
coefficients can conceal the error. Both declarations already occur in the
first tracked source commit, `c70bad57b` (2020-08-25); this does not establish
when the defect originated outside this repository.

## Recession contract

For positive infiltration rate, QINF uses its existing FTEST branches on both
sides of `tstar=1`. The extra unity cutoff is removed; coefficients, existing
nonpositive-rate handling and output formats are unchanged. The documented
constant-excess, uniform-plane recession solution is continuous at unity
(Stone et al., 1993, DOI 10.13031/2013.28470; WEPP Chapter 4, equations
4.4.28–29). Heterogeneous and unsteady routing remains an approximation requiring
whole-model validation.

Soil storage sufficient to fund a negative local exchange does not establish a
physical surface-water source. Keep Hortonian runoff, lateral soil input and
surface return accounting separate. Negative FIN is not globally prohibited;
any source must be supported by the corresponding process. Do not clip exchanges
or change event ownership to make a regression pass.

## Validation and adoption

`tests/test_hillslope_recession_geometry.py` exercises the actual native routines
with heterogeneous lengths, nonzero connected roots, sentinel invariance,
threshold continuity and zero infiltration. Existing Roads accounting and
hourly-return fixtures remain required. The active open-boundary funding
package records U2 (origin only) and U3 (origin plus continuity) independently.
Both pass the twelve-case physical screen; that is not a universal validity claim.

WEPPpy ADR-0119 records the decision and rejected alternatives. Independent AI
scientific acceptance binds the final source and matched pair in the native
open-boundary package's `artifacts/D2-final-scientific-acceptance.json`. All final
native/watchlist/Disturbed/Roads physical gates pass; fresh Cedar reproduces all
6,057 reviewed files exactly. Class-sign checks span 24 years; local source/bed
checks cover 34 declared dates, not a whole-watershed budget.

Classify the array-origin correction as interface correctness and the unity
transition as `bounded_transition` within the uniform-plane constant-forcing
scalar domain. Neither establishes the separate soil-capacity-order contract or
universal heterogeneous cumulative ownership. Preserve valid signed exchanges:
93 audited negative total FIN states outside linked QINF have explicit surface
return support; 413 negative incremental recession differences remain disclosed.

Roads magnitude targets remain unmet (713/766 meaningful and 31/74 small).
This native repair does not approve parameter defaults or a user interface.
QINF changes affect single-OFE and non-Roads simulations as well: 29/481 Cedar
single-OFE water files change. Regenerate the matched hillslope/PASS/watershed
chain when using the revision-3 pair.

## Shared callers

QINF is called by IRS, CONRUN (contour runoff) and WSHIRS (channel-surface
runoff). Its positive-rate recession extension therefore affects those paths
outside Roads. EPLANE has one active IRS caller. Actual WSHIRS execution is covered by existing channel tests and fresh Cedar.
Dedicated complete CONRUN event coverage remains absent in this campaign;
the contour-flag test covers GRNA storage aggregation only. Scalar QINF tests
and this bounded scientific acceptance must not be described as empirical
contour-routing validation. Retain this coverage limitation for future studies.
