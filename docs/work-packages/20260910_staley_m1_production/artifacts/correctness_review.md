# Independent implementation correctness and UI review

Reviewer: contract_correctness. Final bounded review 2026-09-10 22:27:11 UTC:
no remaining blocking correctness or UI findings; approval conditional on the
final full suite and strict browser results. Reviewer did not edit implementation.

Closed findings and evidence:

- Owner completion ordering and source association: completed Soils/Climate must
  follow watershed abstraction; raw CLI newer than exported parquet invalidates
  readiness. Actual NoDb owners/RedisPrep regression tests cover these cases.
- K readiness uses its own provenance, POLARIS inputs and used CFVO inventory;
  full RUSLE completion is unnecessary. Subsecond source rewrites and missing
  used CFVO invalidate readiness in production tests.
- Exact planned job receipt is durable before Redis marker persistence; missing
  receipt recovery cannot reuse an earlier completed job. Real Redis/NoDb fault
  injection is retained in runtime_regression.py.
- Publication rechecks sources and ownership; changed uploaded bytes or watershed
  after normalization cannot replace the accepted map. Predictor reuse copies
  only recorded, verified artifacts, ignoring unrecorded files/symlinks.
- Optional-state read does not create NoDb; enabling the feature initializes both
  direct dependencies, POLARIS and RUSLE, through the real module enable path.
- Completion reconciliation preserves the whole worker publication revision,
  avoiding a completed attempt paired with previous accepted output. Both upload
  and model races have regression tests.
- UI displays actionable text, accepted and candidate filenames separately,
  unavailable NOAA, unitized metadata and the nonblocking study-area warning.
  Upload-in-progress and lost preflight/state fetch disable Run appropriately.

The strict browser acceptance subsequently passed with new upload/run IDs,
current accepted results and downloaded bytes; reload, SI/English, ambiguous
replacement/correction and live prerequisite transitions also passed. See
[browser log](browser_smoke.log), [rendered control](control_completed.png),
[live jobs](live_jobs.json) and [validation](validation.md) for final suite status.
Production deployment and the owner's real-basin acceptance remain separate.
