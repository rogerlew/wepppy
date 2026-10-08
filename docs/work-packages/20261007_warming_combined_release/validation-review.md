# Validation review

## Scope and scientific disposition

The requested three-way comparison was executed with the corrected combined
release and the two legacy roughness cases. No model code, default, deployment
or live run was changed. Agreement is tested against a legacy model baseline,
not observations. The yield-preservation hypothesis is supported; negligible
routed-hydrograph change is not supported. The 1994 discrepancy remains an
explicit scientific follow-up, not hidden by a successful process status.

## Evidence checks

The four frozen executable hashes and matching release sidecars identify the
actual binaries. Both release targets link the estimator. Each physical case
ran all 864 hillslopes before its same-build watershed. All 2,596 processes,
including the output-mode control, reported success. The control's canonical
physical-output hashes agree between modes 1 and 3.

Consumed native inputs were hashed and parsed. The two 10 cm cases have exact
input equality. In the 17 cm case, only the 1,885 eligible rrinit records
change; all other management records and physical inputs match. The frozen
snapshot remains unchanged. Both fresh legacy cases reproduce their 6,056
raw historical files exactly. Historical derived interchange files are not
treated as binary-output parity evidence; they were regenerated with the same
current converter for every case.

Every native conversion has 7,573,824 PASS and 16,690,464 WAT records, zero
rejections and complete calendar coverage. Area is constant and identical
between cases. Streamflow components sum correctly; all rates are finite and
nonnegative. Each outlet series has 144 samples on every day. Ledger dates and
element/channel IDs match, and ledger volumes agree with EBE at the documented
printing tolerance. The totalwatsed calculation's baseflow settings match a
readback from the source project.

Six tests cover metric identity, scaling, offsets, undefined reference cases,
invalid arrays and date completeness/order. The raw-output verifier also
recomputes daily NSE/KGE/R² with Python's standard-library statistics and
compares them with the NumPy calculation to 1e-12. This check passes, as do all
18,168 raw-output hash checks and consumed-input/source checks. Final verifier
evidence is retained in [verification.json](artifacts/analysis/verification.json).
The full application suite is not an acceptance oracle for this offline-only
research harness; no application behaviour or integration path was modified.

## Manual assessment

All six images were opened and inspected. Labels, legends and units are
legible, with no clipped panels. Curve overlap is supported by paired data,
not inferred from appearance alone. Event windows and three historically
selected controls are retained as parquet data and JSON summaries. The report
distinguishes daily yield, sampled outlet integral and channel ledger volume.
It explicitly recognises the sensitivity-focused selection of smaller events
and printing/sample limitations on peak timing.

No score is fitted, shifted or recomputed after excluding inconvenient days.
The provisional aggregate limits were declared before model execution and
remain unchanged after their failure for combined-release outlet discharge.
The raw result is not converted into an unqualified release failure: some
departures may reflect intended corrections, and legacy output is not truth.

## Failures and limits retained

The first attempt stopped during staging because a broad management-file
selector included `pw0.man`. It ran no models and remains intact in the
`-attempt1-staging-failure` directory. Numeric hillslope filtering corrected
the harness. A parser pretest exposed a ~4e-9 m² decimal/binary representation
difference in the known watershed area; its absolute check now allows 1e-6 m²,
while between-case area equality remains exact. This is a representation check,
not a scientific tolerance relaxation.

Two documentation lint invocations needed the staging working directory and
sibling package reference present. The actual repository links are valid;
the corrected scoped lint passes. Analysis manifests exclude changing log
files, which remain retained, and are refreshed after the final verifier.

Security impact is none: fixed known model binaries, isolated research paths,
no secrets or attack-surface changes. Production remains untouched. No new
runtime parameters or flags are introduced. HV-02/HV-05 are not closed by
this comparative study, and no additional repair was attempted.

## Final disposition

Research scope complete at 2026-10-07 22:14 UTC. No unresolved defect in the
comparison harness or evidence chain was found in this review. The scientific
non-equivalence and remaining channel discrepancy are findings, not waived
acceptance gates. Six metric/date tests pass; scoped documentation lint and
diff checks pass. Application deployment, full physical conservation closure
and generalisation beyond this site remain outside the completion claim.
