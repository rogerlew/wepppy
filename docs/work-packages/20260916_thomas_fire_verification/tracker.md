# Thomas Fire verification tracker

Status: Complete (audit only). Started/closed 2026-09-16 UTC. Security impact: none.

## Progress

- [x] Confirmed forest identity, local run path and existing healthy service stack.
- [x] Scoped read-only audit and package-owned evidence.
- [x] Verify accepted M1 attempt, input identity, basin/support and raster predictors.
- [x] Independently check all saved probabilities, inverses and rainfall semantics.
- [x] Establish USGS reference compatibility and quantify attributable differences.
- [x] Record findings, actionability, limitations and unchanged-file proof; close docs.

## Decisions

2026-09-16 UTC: no production changes or live model reruns. Published San Ysidro
69% at I15=24 mm/hour is an initial reference, not an exact acceptance oracle
until original basin/predictors are matched. Keep audit evidence outside the run.

2026-09-16 UTC: original USGS basin 19384 matched by maximum polygon overlap,
not nearest outlet. Metadata names STATSGO. Preserve POLARIS as an accepted
input option; recommend transparent provenance/sensitivity, not restrictive gates.
Use analytical rounding tolerance for USGS table values. Audit closure is not
predictive calibration or remediation completion.

## Handoff

[Findings](artifacts/findings.md): TF-01 soil comparability (high), TF-02 modeled
subdaily provenance (medium), TF-03 terrain parity (medium), TF-04 fixed-intensity
comparison (low). [Numerical evidence](artifacts/saved_run_audit.json) and
[matched reference](artifacts/usgs_comparison.json) retain reproducible values.
No application/run changes, reruns, deployment, commit or push.

## Validation

- `wctl run-python .../artifacts/audit_saved_run.py`: passed all assertions.
- `wctl run-python .../artifacts/compare_usgs.py`: passed spatial-match and
  independently derived source-rounding tolerance assertions.
- Final rehash against retained baseline: 53 monitored files, zero changed.
- Package doc lint: four files, zero errors/warnings; project tracker lint passed.
- Spelling preview and `git diff --check`: clean. ExecPlan moved to completed
  using `wctl doc-mv`, with package link rewritten by the documentation tooling.
- No production-code tests were needed: only audit scripts and documentation
  changed. Existing code-quality report/summary modifications were preserved.
