# Correctness and User-Experience Review - CLIGEN Binary Provenance and Runner Identity

## Metadata

- **Package**: `docs/work-packages/20261005_cligen_binary_provenance/`
- **Reviewer**: Codex implementation self-review
- **Date**: 2026-10-05
- **Scope reviewed**: CLIGEN release pair, vendor tool, runtime verifier, five
  launcher families, focused tests, and generated-climate evidence
- **Commit/branch context**: WEPPpy `master`, scaffold `a2337a6eb`,
  implementation `a1747a6e1`
- **Canonical contracts**: `package.md` and the completed ExecPlan
- **Related QA/security artifacts**: Security artifact not required (`low` triage)

## User Outcome

- **User goal**: Tie each generated climate to the verified CLIGEN binary and
  exact source claim used to create it.
- **Success presented to the user as**: A successful generated `.cli` and a
  durable identity log line whose hashes match the vendored binary and sidecar.
- **Failures that may reach the user**: Missing, malformed, mismatched, dirty,
  or unsupported 5.3.2 sidecar state; subprocess failures remain unchanged.
- **Partial-state behavior**: Verification failures occur before process start
  and must not leave a newly generated `.cli`.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| `cligen532` and sidecar absent | no | Explicit pre-execution failure | Missing-binary and missing-sidecar unit cases |
| Binary present, sidecar absent | no | Explicit pre-execution failure | `test_strict_identity_rejects_invalid_release_states[missing-*]` |
| Matching clean optimized pair | yes | Verified log then execution | Real `run_multiple_year` integration |
| Supported legacy binary without sidecar | yes | `legacy_unverified` log then execution | Legacy unit cases, including stray unsupported sidecar |
| Malformed or tampered pair | no | Bounded failure before process start | Malformed, binary, dirty, role, manifest, and traversal tests |
| Binary replaced after prior verification | only if new pair verifies | Recompute identity; reject mismatch | In-place replacement and vendor rollback tests |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Required 5.3.2 sidecar missing | Exceptional | Actionable provenance error, no child process | Strict package contract; direct no-Popen test |
| Binary digest/size mismatch | Exceptional | Actionable integrity error, no child process | Prevent untraceable execution; tamper test |
| Sidecar reports dirty source | Exceptional | Actionable release-policy error, no child process | Release must use committed inputs; dirty test |
| Legacy selector has no sidecar | Expected | Run with `legacy_unverified` identity | Backward compatibility tests |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| User/request intent | Selected CLIGEN version and seed | Exact default, `-r0`, `-r12345` commands | pass |
| Reloaded persisted state | N/A; no new persisted setting | N/A | N/A |
| Generated intermediate | `.inp`/`.par` reflect requested run | Real `Cligen.run_multiple_year` fixture | pass |
| Prepared/executable input | Exact verified binary path and command | `cligen_verified.log` readback | pass |
| Execution output | Fresh parsed `.cli` from candidate | Real 365-day parse plus 366-row comparison | pass |
| User-facing result | Existing climate workflow consumes generated file | `ClimateFile.as_dataframe()` succeeds | pass |

- **Direct unmocked failing boundary**: Tampered temporary `cligen532` is
  rejected before the patched `Popen` records a call.
- **Actual-project/environment evidence**: Exact vendored binary generated and
  parsed a one-year climate in the WEPPpy development container.
- **Highest completion claim supported**: Implemented and locally validated.
- **Deployment/recovery still outstanding**: All deployment and historical
  climate regeneration are outside this package.

## Review Checks

- [x] Valid, absent, legacy, malformed, tampered, and replacement states tested.
- [x] Every 5.3.2 process launcher verifies before process creation.
- [x] Every launcher writes the stable identity fields to its durable log.
- [x] A direct unmocked test covers binary and sidecar consumption.
- [x] A fresh `.cli` is parsed at the consumer boundary.
- [x] Positive-seed output impact is documented and semantically bounded.
- [x] Error messages identify the failed artifact and recovery action.
- [x] Integrity evidence is not mislabeled publisher authentication.
- [x] Completion language distinguishes local validation from deployment.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Host vendoring | Initial tool import loaded the heavy CLIGEN package and failed on a host without NumPy. | First real vendor command | Load the standalone verifier directly without package initialization. | Resolved |
| COR-02 | Medium | Pair replacement | Two files cannot be replaced in one atomic filesystem operation. | Plan/code review | Stage and validate both; fail closed during replacement; restore both after caught failure; test rollback. | Resolved |
| COR-03 | Medium | Positive seed output | `prism_mod` defaults to `-r12345`, so the new binary intentionally changes time to peak. | Exact baseline/candidate semantic comparison | Retain compatibility artifact and require explicit release note. | Resolved |
| COR-04 | Medium | Source release publication | Committing generated release artifacts advances the checkout beyond the source commit recorded in the sidecar. | Post-publication real vendor command | Verify the recorded commit/tree and committed manifest bytes directly, and require that commit to be an ancestor of both checkout tip and remote default. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: `ship` for repository/local scope; deployment
  remains separately authorized
- **Reviewer sign-off**: Codex, 2026-10-05

## Artifact Observability Gate

- [x] Run-local identity logs are retained with normal climate artifacts.
- [x] Archive/restore behavior is unchanged because existing log names and
      locations are preserved.
- [x] No sidecar contents expose secrets or require hidden-only evidence.
