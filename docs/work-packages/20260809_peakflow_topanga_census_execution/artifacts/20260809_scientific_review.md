# Scientific Review - Frozen Topanga Census Execution

## Scope and Evidence

An independent reviewer checked the frozen plan and selection, all 1,088
terminals, mutation realization, trace and hillslope-pass hashes, the outer
event ledger, ADR-0042 screening flags and floors, candidate subset, and all
denominator grains. The generated authorities are recorded in
`topanga-execution-summary.json` and the external version-two denominator and
prevalence ledgers.

## Findings and Remediation

The initial review placed publication on HOLD because exclusion and terminal
status denominators were absent and “local hillslope prevalence” overstated the
estimand. Aggregation now publishes requested, excluded, selected, terminal,
complete, failed, stopped, candidate-event, and candidate-trial counts at
overall, scenario, family, and direction grains. Package language now calls the
results eligible mutation-trial screening prevalence and paired-event-row
screening prevalence.

## Verified Results

- The plan contains 1,120 requested records: 1,088 eligible and 32 excluded.
- All 1,088 selected trials are complete and changed exactly one declared file.
- Every realized mutation matches its frozen expected value. Fourteen Ksat
  values differ only by floating representation, with maximum absolute delta
  `1.78e-15` and no serialization loss.
- The event ledger has 225,654 unique trial-event keys: 225,036 paired, 320
  baseline-only, and 298 mutant-only. Absent-side measurements remain null.
- Every ADR-0042 flag and screening floor independently recomputed with zero
  mismatch. The candidate ledger is the exact 11,506-row subset and covers
  1,027 eligible mutation trials.
- Candidates remain screened, not adjudicated. No routing, channel, watershed,
  or downstream-impact conclusion is made.

## Verdict

PASS. Independent revalidation found zero errors across all 1,088 hardened
terminal checks and all seven denominator grains.
