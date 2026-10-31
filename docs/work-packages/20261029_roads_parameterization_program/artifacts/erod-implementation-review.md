# Independent EROD interval-support implementation review

Reviewed `src/erod.for` SHA-256
`fff9125e81e3eb1d9e237e7cb492f8ae68ae61fef1456c0ee65f2da2e2944dd8`,
`tests/test_erod_interval_support.py`, the existing RUNGE/ROUTE contracts and
`erod-subgrid-ablation-plan.md`.

No blocking implementation finding in this candidate.

The branch at EROD lines 135–185 acts only on nonempty intervals preceding the
next publication grid point. It starts integration from the actual LDLast
boundary state and leaves ILAST unchanged. The original grid-containing path
is unchanged. RUNGE's endpoint detachment cache supplies the terminal DL;
repeat root trials always integrate from the immutable upstream state and so
cannot accumulate trial loads. When endpoint load exceeds capacity, the
transition search brackets the change within the interval, bisects to adjacent
representable coordinates, and returns the corresponding load without leaving
its domain. The dry-side cutoff retains the existing Case-4 zero-load convention.

Independent verification:

- `PATH=/usr/bin:/bin:$PATH pytest -q tests/test_erod_interval_support.py
  tests/test_deposition_stable_solution.py`: **131 passed in 2.12 seconds**.
- Eleven additional boundary probes cover zero upstream load, an internal start,
  the last physical subgrid interval, root at the upstream endpoint, initially
  above-capacity load, zero capacity, zero source, and float32 endpoint-crossing
  neighbors. All behaved consistently with their constant-source references.
  Probe retained at `/tmp/erod-review-probe.py`.
- `git diff --check` passed for the reviewed source and tests.

The initially missing wet/dry, last-grid and nonzero-rill coverage is now present.
The nonzero-rill tests use the independent linear-ODE solution rather than RUNGE
as an oracle. ILAST=101 corresponds to the end of normalized physical domain;
its only physical remainder is zero-width, which the new test preserves.
Unsupported extrapolation beyond x=1 remains outside this candidate.

Residual risk: this review validates the bounded source mechanism, not release
acceptance. Restoring omitted detachment changes loads and may expose other
particle/source-accounting failures. Full-period seed/control replays and the
expanded particle/class-mass audits, native suite/watchlist, Roads, Disturbed
and matched Cedar gates remain required. Existing RUNGE discretization and its
legacy minimum interrill-load rule remain unchanged; this patch does not prove
all variable-coefficient or stiff cases scientifically accurate.
