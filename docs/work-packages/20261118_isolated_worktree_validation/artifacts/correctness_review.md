# Correctness review: isolated-worktree validation

Reviewer: Codex primary integrator (self-review). Date: 2026-11-18 UTC.
Contract: tools/wctl2/docs/worktree-tests.md. Related review: security_review.md.

## User outcome and failure-class coverage

A developer invokes one supported command for the actual candidate checkout.
Runtime omissions are reported before pytest collection. Candidate-built assets,
explicit compatible dependency reuse, short temporary paths and source-integrity
receipts replace per-task wrappers. Legacy run-pytest behavior is preserved and
its mismatch message directs users to the new command.

The confirmed class includes ignored controller output, Node/Chromium assets,
both native parser/provenance pairs, stale database columns, an incomplete profile
fixture, long AF_UNIX paths and source-writing tests. The implementation prepares
or checks each applicable runtime requirement. Profile fixture coverage passes
all 49 tests. Source-writing tests fail the integrity receipt; arbitrary import
side effects are not automatically repaired. Catalog timing under broad load is
not an environment prerequisite and remains outside this tooling change.

## State matrix

| State | Required behavior | Evidence |
| --- | --- | --- |
| No candidate-generated bundle | Build from candidate and read back | Real browser run |
| Dependencies absent | List missing prerequisites; no tests started | Real broad negative receipt |
| Compatible explicit dependency checkout | Read-only mounts; real Chromium launch | Browser suite, 24 passes |
| Existing parser/image assets | Validate binary/provenance and candidate source | Native suite, 315 passes |
| Stale package lock or Rust sources | Reject, do not silently reuse | Unit cases using real files/hashes |
| Stale database schema | Read-only report; no migration or pytest | Prepared broad attempt |
| Existing receipt | Refuse overwrite | Unit test |
| Source/runtime changes during test | Exit 3 despite pytest success; retain changed files | Mutation tests |
| Shared-container legacy invocation | Existing nonce and behavior retained | Complete wctl suite |

## Generated artifact evidence

Intent is recorded as profile/test arguments and candidate HEAD/source hashes.
The actual candidate controller builder renders and reads back the JS consumed
by the browser tests. Real browser and parser consumers run, not mocks. Receipts
record runtime file hashes and actual user/group identities, then recheck source
and runtime fingerprints. Readiness-only output explicitly differs from test
success. Incomplete receipts are never promoted to passes.

## Verdict

Pass for local tooling acceptance; no unresolved medium/high findings. The full
repository suite remains unavailable against the stale shared test database.
This is an explicit, correctly detected prerequisite failure, not a green broad
suite. Database migrations and performance investigation require their owning
scope. No source or execution threshold was weakened to obtain acceptance.
