# Correctness and User-Experience Review - CLIGEN Seed Pipeline

## Metadata

- **Package**: `docs/work-packages/20261005_cligen_seed_pipeline/`
- **Reviewer**: Codex implementation review
- **Date**: 2026-10-05
- **Scope reviewed**: UI, payload validation, durable state, RQ replay, build
  snapshots, adapter argv, batch resync, actual-project output, and defaults
- **Canonical contract**:
  `docs/ui-docs/contracts/climate-cligen-seed-contract.md`

## User Outcome

The user can enter an optional CLIGEN seed, rebuild climate, and prove that the
saved value reached the native executable. Blank retains automatic behavior.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Legacy attribute absent | yes | Behave as automatic/`None` | Parser and facade tests pass |
| Field present but empty | yes | Persist `None`; retain path default | Parser, Jest, and binary tests pass |
| Integer `0..99999` | yes | Persist and forward exactly | Boundary values and actual project pass |
| Existing generated runtime integer | yes | Keep runtime-only; render blank override | Template and batch tests pass |
| Malformed durable override | no | Fail before native execution | Snapshot failure test passes |
| Malformed or out of range | no | Transactional validation error | Parser and route matrix passes |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| User/request intent | Explicit chosen integer | RQ metadata contains `cligen_seed: 24680` | Pass |
| Reloaded persisted state | Exact integer | Detached reload returned `24680` | Pass |
| Generated intermediate | Exact CLIGEN input/command | `cligen_wepp.log` contains exact command | Pass |
| Prepared/executable input | One `-rN` argv | Exactly one `-r24680` | Pass |
| Execution output | Fresh parseable deterministic `.cli` | 365 rows; repeated SHA-256 matches | Pass |
| User-facing result | Climate build completes with retained log | Two normalized-fork RQ jobs finished | Pass |

## Review Checks

- [x] Canonical intent and checkpoint ancestry verified.
- [x] Absent, empty, populated, legacy, and hostile states tested.
- [x] Every applicable CLIGEN adapter carries the seed.
- [x] Direct NoDb persistence and native subprocess boundaries exercised.
- [x] Fresh generated output parsed and deterministic comparison retained.
- [x] Defaults and unrelated climate settings remain compatible.
- [x] Security controls do not interfere with valid values.

## Findings

No High or Medium findings. A planned assertion that the entire source project
remain byte-identical was corrected after observing canonical fork bookkeeping:
the supported route updates only `redisprep.dump` and `rq.log`. A second control
fork proved every other source file remained byte-identical. This is a
documentation correction, not a product defect.

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: none
- **Release recommendation**: broad mechanical gates passed; ready for normal
  review/merge. Deployment remains separate.
- **Reviewer sign-off**: Codex, 2026-10-05
