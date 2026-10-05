# Correctness and User-Experience Review - CLIGEN Binary Provenance and Runner Identity

## Metadata

- **Package**: `docs/work-packages/20261005_cligen_binary_provenance/`
- **Reviewer**: Pending independent review
- **Date**: Pending
- **Scope reviewed**: Pending exact implementation revision
- **Commit/branch context**: Pending
- **Canonical contracts**: `package.md` and the active ExecPlan
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
| `cligen532` and sidecar absent | no | Explicit pre-execution failure | Pending |
| Binary present, sidecar absent | no | Explicit pre-execution failure | Pending |
| Matching clean optimized pair | yes | Verified log then execution | Pending |
| Supported legacy binary without sidecar | yes | `legacy_unverified` log then execution | Pending |
| Malformed or tampered pair | no | Bounded failure before process start | Pending |
| Binary replaced after prior verification | only if new pair verifies | Recompute identity; reject mismatch | Pending |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Required 5.3.2 sidecar missing | Exceptional | Actionable provenance error, no child process | Strict package contract |
| Binary digest/size mismatch | Exceptional | Actionable integrity error, no child process | Prevent untraceable execution |
| Sidecar reports dirty source | Exceptional | Actionable release-policy error, no child process | Release must use committed inputs |
| Legacy selector has no sidecar | Expected | Run with `legacy_unverified` identity | Backward compatibility boundary |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| User/request intent | Selected CLIGEN version and seed | Pending test/command | Pending |
| Reloaded persisted state | N/A; no new persisted setting | N/A | N/A |
| Generated intermediate | `.inp`/`.par` reflect requested run | Pending readback | Pending |
| Prepared/executable input | Exact verified binary path and command | Pending identity log | Pending |
| Execution output | Fresh parsed `.cli` from candidate | Pending semantic comparison | Pending |
| User-facing result | Existing climate workflow consumes generated file | Pending focused workflow | Pending |

- **Direct unmocked failing boundary**: Pending tampered-copy test.
- **Actual-project/environment evidence**: Pending local WEPPpy candidate run.
- **Highest completion claim supported**: Scaffolded only.
- **Deployment/recovery still outstanding**: All deployment and historical
  climate regeneration are outside this package.

## Review Checks

- [ ] Valid, absent, legacy, malformed, tampered, and replacement states tested.
- [ ] Every 5.3.2 process launcher verifies before process creation.
- [ ] Every launcher writes the stable identity fields to its durable log.
- [ ] A direct unmocked test covers binary and sidecar consumption.
- [ ] A fresh `.cli` is parsed at the consumer boundary.
- [ ] Positive-seed output impact is documented and semantically bounded.
- [ ] Error messages identify the failed artifact and recovery action.
- [ ] Integrity evidence is not mislabeled publisher authentication.
- [ ] Completion language distinguishes local validation from deployment.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Pending | Pending | Pending | Review not yet performed | Pending | Independent review | Open |

## Verdict

- **Gate status**: `fail` (implementation and review pending)
- **Unresolved findings**: Pending
- **Release recommendation**: `hold`
- **Reviewer sign-off**: Pending

## Artifact Observability Gate

- [ ] Run-local identity logs are retained with normal climate artifacts.
- [ ] Archive/restore behavior for the existing log path remains covered or is
      explicitly shown unchanged.
- [ ] No sidecar contents expose secrets or require hidden-only evidence.
