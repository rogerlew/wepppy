# Code Review - Durable Peak-Flow Census Preparation

## Scope

The review covered `wepppy/wepp/peakflow_census/`,
`tools/peakflow_census.py`, the schemas, and the focused tests. The fidelity
authority was `tools/peakflow_phase2a_pilot.py`; routing and adjudication code
were explicitly excluded.

## Findings and Resolution

- **Resolved, high**: initial terminal reuse checked bindings but did not retain
  a terminal when preparation failed before subprocess completion. Execution
  now writes an explicit stopped terminal for expected filesystem, mutation,
  and subprocess-boundary failures. A retry requires all binding hashes to
  match and archives the prior terminal, run directory, and output directory.
- **Resolved, medium**: initial plan validation trusted the serialized plan ID.
  Validation now recomputes the content ID from ordered records and input
  authorities and verifies every readable trial ID and evidence locator.
- **Resolved, medium**: the first generated full plan named an unresolved
  executable locator. It remains under `artifacts/superseded/`; the canonical
  manifest and plan bind an existing executable whose SHA-256 matches the
  accepted Phase 1 build manifest.

No unresolved correctness, compatibility, or maintainability findings remain.
The implementation uses narrow exception handling, standard-library path and
atomic-write primitives, pandas already present in WEPPpy, and no new external
dependency.

## Verdict

**Pass.** The implementation is a faithful extraction with generated behavior,
not a scaffold. Focused tests cover planning, mutation realization, boundary
exclusions, path constraints, pairing, immutable pilot parity, and retry
bindings.
