# Correctness review - Omni MOFE Disturbed soil repair

## Metadata

- Reviewer: Codex author review; no independent reviewer was used in this
  execution session.
- Date: 2026-11-16 UTC.
- Scope: the shared Disturbed MOFE source resolver, its unit and real-writer
  regressions, the Disturbed README, and this work package.
- Canonical intent: `docs/schemas/mofe-input-identity-contract.md`,
  `docs/schemas/disturbed-mofe-mapping-contract.md`, and
  `docs/schemas/disturbed-treatment-soil-lookup-contract.md`.
- Security: no authorization, route, queue, subprocess, secret, or external
  input boundary changed; no dedicated security review is required.

## User outcome

Ordinary Disturbed builds and later Treatments or Omni builds now use the same
MOFE producer. A clean build keeps its current single-OFE source. Once
`domsoil_d` points at a published `hill_*.mofe` output, the producer recovers the
retained source key from `ssurgo_domsoil_d`, then applies the existing ordered
per-segment management-class and texture lookup. It never submits a combined
MOFE soil as one stack member.

## State matrix

| State | Required behavior | Evidence |
| --- | --- | --- |
| Clean assignment | Preserve current single-OFE source | Existing and focused unit tests |
| Published MOFE with retained source | Rebuild every segment from retained source | Reentry unit and real-writer repeat regression |
| Published MOFE without retained source | Fail before generation with rebuild guidance | Malformed-state unit regression |
| Retained source is itself MOFE | Reject nested generated state | Resolver validation and source review |
| ESDAC quality carrier | Validate against recovered source key | Final ESDAC-focused run |
| Mixed management classes | Preserve numeric segment order and class-specific values | Three-segment generated/prepared artifact readback |
| Formats 9002 and 9005 | Preserve supported writer behavior | Repeat regression at 9002 and targeted prepared-input case at 9005 |

## Failure-class assessment

Production callers of `SoilMultipleOfeSynth` were inspected. Core soil building
normalizes or explicitly passes single-OFE sources. Fuzzing distinguishes
single- and multi-OFE inputs and writes multi-OFE artifacts directly. Agricultural
fields repeat a parent single-OFE `.sol` and remain protected by the existing
writer guard. The confirmed peer defect was the shared Disturbed producer
reusing its own published `domsoil_d` output. Treatments and Omni are consumers
of that same producer, so the repair covers them without a second implementation.

## Generated artifact evidence

The direct regression invokes real `WeppSoilUtil`, `SoilMultipleOfeSynth`, and
normal multi-OFE preparation twice. It parses three class-specific component
soils, the combined `hill_101.mofe.sol`, and prepared `wepp/runs/p10.sol`.
Components each contain one OFE and cite `base.sol`, never
`hill_101.mofe.sol`. Combined and prepared artifacts contain the same three OFEs
in segment order, with expected `ki`, `kr`, `shcrit`, `ksatadj`, `ksatfac`,
`ksatrec`, and upper-200-mm `ksat` values for high-severity fire, thinning, and
prescribed fire.

## Validation results

- Final affected-boundary run: 34 passed, 2 warnings in 41.49 seconds. This
  covered source-resolution units, the ESDAC runtime gate, repeated real-writer
  generation/preparation, and a 9005 thinning MOFE prepared input.
- After strengthening the real-writer case to change segment assignments between
  the first and repeated build, that direct case passed again in 18.59 seconds.
- Earlier adjacent focused run: 134 passed, 5 warnings in 152.04 seconds. It
  covered Disturbed units, trigger routing, ESDAC, Treatments build, and MOFE
  scenario artifacts. The final source-map consistency adjustment was followed
  by the 34-test affected-boundary rerun above.
- Changed-file broad-exception enforcement: pass; Disturbed delta `+0` and net
  changed-file delta `+0`.
- `git diff --check` for package files and changed implementation/tests: pass.
- The full test suite was not run, by explicit operator direction.

## Findings and residual risk

No unresolved High, Medium, or Low correctness finding was found within the
reviewed scope. The implementation depends on the existing retained
`ssurgo_domsoil_d` assignment and matching `SoilSummary`; malformed legacy state
fails explicitly and requires a normal soil rebuild. Local evidence does not
establish deployment, production identity/mount parity, regenerated
`innovative-tailor` artifacts, model execution, or fresh report output.

## Verdict

- Correctness gate: pass for focused local code delivery.
- Unresolved findings: High 0, Medium 0, Low 0.
- Highest supported claim: locally validated generated and prepared inputs.
- Deployment and affected production-run recovery remain separate operator
  actions.
