# Correctness and user-experience review

## Metadata

Reviewer: independent `/root/contract_correctness`, 2026-09-09 UTC.
Scope: `project_routes.py` and paired route tests against checkpoint
`bf063ed56`. Authority: RQ response contract, Named-preset creation initialization
diagnostics and Named-preset creation failure coverage; creation policy.
Related artifacts: `20260909_qa_review.md`, `20260909_security_review.md`.

## User outcome and state matrix

Users receive the recognized cause and repair guidance. Every failed response
has searchable correlation. Unknown exceptions receive safe canonical errors;
existing lifecycle behavior, including incomplete cleanup, is preserved.

| State | Required result | Evidence |
| --- | --- | --- |
| Required module/file absent | Cause-specific failure | Real Portland browser/Ron; missing-file route test |
| Optional TTL/README operation fails | Existing 303 success | Optional-failure parameterized regression |
| Populated valid configuration | Existing creation/replay redirect | Existing legacy/project-owned creation tests |
| Legacy module override | Preserve forwarding; explain unavailable module | Override regression |
| Hostile diagnostic string | No arbitrary reflection | Newline, extra text, path, markup, Unicode, oversize/token cases |
| Reserved/conflicting/replayed creation | Existing status and headers | Existing replay/conflict and new Retry-After regression |

Inputs are tested separately through both route aliases, missing/invalid auth
and payloads, authenticated/CAPTCHA paths, and writer enabled/disabled modes.
This is not exhaustive controller-state coverage. No persistence or access
boundary was changed; real Ron and browser creation exercise the failing source.

## Error policy and findings

Recognized infrastructure exceptions are exceptional and use safe stage/cause
diagnostics. Expected auth/validation errors retain their existing status/code.
Optional TTL/README errors remain nonfatal under the canonical coverage section.
Previously unhandled application exceptions use `run_creation_failed`.

COR-03 (medium): raw PresetPolicyError details could expose a private policy
path. Resolved by a separate safe policy diagnostic preserving status/code and
summary, with a private-path/retained-traceback regression. Reviewer confirmed
resolution and passed the correctness gate. Requested missing TTL/README,
in-progress Retry-After, legacy overrides, and CAPTCHA evidence were added.
No unresolved high or medium findings.

The broad suite subsequently found the existing Builder caller of the release
helper. Making the additional ID optional restored its original call/logging
contract; the reviewer inspected all callers and confirmed no blocker. Combined
project/Builder suites then passed all 132 tests.

## Evidence and limits

Focused suite: 113 passed. Initial real browser Portland request returned
`run_initialization_failed` and named `portland`; response ID
`57a515584f58414daf5403b5fb57278c` appears in the original traceback, secondary
cleanup traceback, and status/code summary. A final reload smoke and broad
suite are recorded in the tracker. Existing orphan/reservation handling for
otherwise unhandled post-allocation errors remains separate lifecycle debt.
