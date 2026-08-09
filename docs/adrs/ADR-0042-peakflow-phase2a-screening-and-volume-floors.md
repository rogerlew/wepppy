# ADR-0042: Peak-Flow Phase 2A Screening and Volume Floors

Status: Accepted
Date: 2026-08-08

## Context

The accepted peak-flow audit protocol requires absolute floors before ratios
are used to screen mutation responses, but it intentionally did not assign
numeric values. The Phase 2A pilot also needs a bounded tolerance for comparing
three-significant-digit interval discharge output with two-decimal daily
channel volumes. Without frozen values, near-zero numerical noise could create
candidate flags or make routing-volume acceptance outcome-dependent.

## Decision

Use fixed SI-unit floors for the Phase 2A diagnostic workflow:

- runoff depth denominator: `1e-5 m` (`0.01 mm`);
- peak-flow magnitude and difference: `1e-7 m/s`;
- surplus-rate denominator: `1e-8 m/s` (`0.036 mm/h`);
- observer no-surplus depth classification: `1e-10 m`; and
- channel interval-versus-daily volume agreement: absolute difference no more
  than the larger of `0.1 m³` or `5%` of reported daily outflow.

These values classify diagnostic evidence only. They do not alter WEPP inputs,
equations, calibration, routing, or production parameter defaults.

## Decision Provenance

Decision Venue: Codex Phase 2A ExecPlan execution, 2026-08-08 17:34 PDT

Participants Present: requesting operator, Codex

Decision Owner(s): requesting operator under the accepted Gate 2.1 protocol

Implementer(s): Codex

## Change Summary

Previously, the protocol required preregistered absolute floors but left them
unset. Phase 2A now applies the values above before evaluating the accepted
25%-peak/5%-runoff, twofold-peak, solver-switch, twofold-surplus-rate, and
expected-response-reversal rules. The routing check applies its tolerance only
after independently validating timestamp order and nonnegative discharge.

## Rationale

The runoff floor excludes responses below `0.01 mm`, the peak and surplus-rate
floors are above the observer's legacy minimum/small-value noise region, and
the volume tolerance accommodates the precision of the emitted text files
without masking material disagreement. The known-positive interval check
exceeds this tolerance by up to `35.7%`, so its failure is not a rounding
artifact.

## Alternatives Considered

1. No absolute floors - rejected because ratios around zero dominated initial
   screening and contradicted the accepted protocol.
2. Data-dependent quantile floors - rejected because mutation outcomes would
   influence classification and undermine preregistration.
3. A looser routing tolerance - rejected because `chan.out` and `chanwb.out`
   claim compatible discharge and volume units, and discrepancies above `5%`
   are operationally material for this pilot.

## Consequences

Candidate classification is deterministic and reproducible across reruns.
Events below a floor remain in raw outer-joined ledgers but do not trigger a
ratio flag. The volume rule can fail current watershed output even when all
timestamps and discharges are valid; that failure withholds the full census
until the two routing outputs share a reconciled volume authority.

## Evidence

- [Phase 2A completed ExecPlan](../work-packages/20260808_peakflow_phase2a_pilot/prompts/completed/phase2a_pilot_execplan.md)
- [Mutation terminal summary](../work-packages/20260808_peakflow_phase2a_pilot/artifacts/mutation-terminal-summary.json)
- [Hydrograph validation summary](../work-packages/20260808_peakflow_phase2a_pilot/artifacts/hydrograph-validation-summary.json)
- [Accepted audit protocol](../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md)

## Risk and Rollback Notes

The main risk is excluding a scientifically interesting response below a
floor. Raw values and mechanism flags are retained so reviewers can audit or
rescreen them. Roll back by revising this ADR and rerunning classification over
the immutable event-pair ledger; model execution does not need to be repeated.

## Implementation Notes

The constants and derived flags live in `tools/peakflow_phase2a_pilot.py`.
Future phases must either reuse these values or supersede this ADR before
changing them.
