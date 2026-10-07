# Mutation repeat tracker

UTC, started 2026-10-06; closed 2026-10-06 20:11 UTC after independent model
reconciliation. Figures and final evidence summary are complete.

- [x] Identify original Figures 1–3 and mutation engine.
- [x] Confirm both source scenarios and corrected binary exist on forest.
- [x] Freeze consumed input snapshot and mutation plan (1,088 eligible / 32 excluded).
- [x] Validate full-precision observer and canonical parity, plus report readback.
- [x] Execute all eligible full-history baseline/mutant runs (1,368 total, no failures).
- [x] Reconcile outer-paired ledgers and render/inspect Figures 1–3.

Decision: same fixed executable on both mutation sides; no rrinit or rill-width
changes. The original Topanga census used this same named project. New evidence
must distinguish current inputs and source lineage from the August census.

## Evidence and issues

Authoritative campaign: forest `/workdir/hand-to-mouth-fixed-census-20261006-v2`.
Every shared source file present in the August snapshot matches byte-for-byte;
three additional shared context files are inventoried separately. Both strata
have identical climate and terrain. The observer adds only a final IRS write.

The first attempt is retained at `/workdir/hand-to-mouth-fixed-census-20261006`:
an early pilot raced build completion, then an observer array lower-bound error
was caught by direct report inspection. Those observations are invalid, not used
for analysis. V2 passes runoff(1)/peakro(1) explicitly and requires report-level
agreement before execution. An arbitrary 1,000 matched-row assertion was also
removed: correctness is coverage of all positive report rows and agreement
within their output precision, not an invented minimum count.

Existing census test run: 17 passed, one historical integration test failed
because its pinned August executable path now has a different hash. Preserve
the failure; the new campaign pins and validates its own executable identities.

Final checks: eight research-harness tests and 16 nonintegration mutation-engine
tests pass. All 1,368 traces pass report readback; exactly 1,368 expected terminal
identities reconcile. The coordinator was stopped only after all models finished
and the independent aggregation passed; it had no child model process and was
draining progress fsync calls. The preserved progress counter is not final status.
See execution-summary.json and terminal-inventory.csv for authoritative completion.

Figures show 218 fivefold peak departures (184 without surface return), but
1,021 twofold departures remain. Historical comparisons cross source lineage and
observer grain, so attribution is descriptive, not a patch-only causal estimate.
No additional scientific fix, release, production mutation or email was made.
