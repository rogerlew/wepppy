# Roads DEPEND bounded root-search ablation

- `incident_id`: `20261031_roads_depend_bounded_root`
- `status`: `active`
- `scope`: `hillslope`
- `author`: Codex
- `date_utc`: `2026-10-31`
- `host_scope`: `dev`
- `contract_refs`: `requires_scientific_review`

## Failure and baseline

Generated-soil fill `ksatadj=0`, site / 1718465 / outunrut / gravel / none
fails in simulation year 7 at DEPEND's single-real Newton quotient. The released
revision-3 binary repeats SIGFPE with exact partial-output parity. Actual source
and an observation-only scalar driver repeat it. Trials escape [0.05,1] and
reach 7.24766e32 although the independent 80-digit root is
0.050115891779652795. Production prevalence and defect age remain unestablished.

Portable inputs and baseline receipts are in
`tests/fixtures/roads_native_accounting/depend/`, copied from wepppy commit
3cf0e331d, Roads parameterization program artifacts. Original source hashes and
binary identity are retained. Execute extracted runs/p1.run with a sibling
output directory. Scalar reproduction: `pytest -q
tests/test_deposition_stable_solution.py -k steep_positive_root` (SIGFPE before
repair; root within one coordinate ULP afterward).

## Candidate G1

Retain DEPVAL and valid legacy convergence/endpoint returns. Positive-flow
invalid steps, zero derivatives or exhausted iteration budgets use a sign-bracket
bisection to adjacent float32 coordinates, returning its non-depositing side.
ROUTE calls only with DU<0; DEPEND already checks D(XL)>=0. Check Newton division
in double before any potentially overflowing single-real operation. Preserve
negative-flow clamping and no-root conventions, including terminal-flow limits.
No soil parameter, deposition law, release binary or trap flag is changed.

## Validation and promotion boundary

100 source-based deposition tests pass, including observed float32 neighbors,
steep phi, independent positive/decreasing-flow roots, phi=-1/-2 limits, and
absent/terminal roots. Full fixture and paired controls, native full suite,
watchlist, Disturbed, 840 Roads plus 348 downstream cases and Cedar output checks
are pending. Independent review is required. No promotion until all dispositions
are recorded. Revert only the candidate source hunk to roll back; shipped pair
remains unchanged. Permanent watchlist coverage is required before resolution.

## Failure class and scope

ROUTE is DEPEND's only caller, shared by hillslope and watershed computations;
the defect is not intrinsically Roads-only. DEPEQS/DEPOS evaluate the solution
but do not implement this Newton iteration. Other model Newton routines solve
different equations and are not evidence of this defect. Increasing-flow domain
is [XU,XL]; decreasing-flow has an additional zero-flow endpoint -QOSTAR and
legacy segment-end returns, so no positive-flow bracket is imposed on that branch.
