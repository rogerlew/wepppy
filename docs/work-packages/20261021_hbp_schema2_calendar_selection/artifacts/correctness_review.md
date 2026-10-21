# Correctness and QA review

## Scope and intent

Date: 2026-10-21. Native source HEAD and exact correction are in `provenance.json`.
Reviewers: `/root/f90_correctness` followed by `/root/f90_qa`, applying the native
`.codex/agents/f90_code_reviewer.toml` and `f90_qa_reviewer.toml` roles.
Authority: the new package's ExecPlan Decision Log; correct schema-2 routing date
selection, preserving payloads, calendar policy and unrelated behavior.

## Valid-state and artifact chain

| State or boundary | Required outcome | Evidence |
| --- | --- | --- |
| Undated inspection | Existing sequential slot iteration | Existing direct-reader regressions |
| Paired valid date | Exact year/day record and all corresponding arrays | Generated schema1/schema2 fixtures and production readback |
| Partial or absent date | Explicit failure; cursor unchanged | New negative/recovery regressions |
| Final day and later rewind | Deliver final date; permit dated access after EOF | New multiyear regressions |
| Non-leap padding | Preserve bytes; never substitute padding for January 1 | Controlled HBP parity and date-keyed observations |
| Leap/legacy centurial day 366 | Preserve requested day | 2004 and 1900 dated regression cases |
| Observations off/on | Identical ordinary artifacts | Per-case validation receipts |
| Original input → fresh hillslope → HBP → loaded arrays → outlet | Complete generated-output chain with retained hashes | Input/execution manifests, native independent parser, WCL logs and EBE comparison |

No HTTP/auth/persistence boundaries, new artifact-discovery workflow or deployment
were introduced. Browser/archive validation is N/A; isolated retained project
inputs and outputs use the existing supported fork and filesystem workflow.
No mocked transfer replaces the real PASS writer/reader boundary.

## Findings and dispositions

Primary review found no blocking implementation defect: optional arguments are
checked before use, binary search uses validated ordered keys, the calendar year
is verified, and the cursor advances only after successful loading. Production
COMMON layouts, quantization, calendar rules and payload assignments are unchanged.

The reviewer identified a consecutive-year assumption; it is now explicit in the
reader contract. Arbitrary nonconsecutive year tables are not claimed supported.
The previously missing bridge source spec is restored. Dated centurial coverage
was added. Secondary review caught the same test-fixture year-index mistake found
by the executing agent; the fixture was corrected and the failure log retained.
The test comment now accurately limits distinct signatures to volume/sediment.

Source QA, Fortitude and scoped diff checks pass. The reviewer independently
checked controlled acceptance receipts, ledger hashes, and the exact first
changed EBE date. Broad-suite limitations are independently supported by baseline
comparisons and recorded in `validation.md`; no unrelated test repair is hidden
inside this correction.

## Verdict

**PASS for development-package closure**, signed off by `/root/f90_correctness`
on 2026-10-21 after final generated-output review. No unresolved implementation
blocker remains. The real project completes all 29 cards in both modes; all
28 hillslopes pass every requested day through 2025-365. All 388 ordinary files
match off/on and all 196 hillslope products match baseline. Reviewer verified
ledger hashes and the explicit outlet-only arithmetic limitation.

Source QA passes; a fresh isolated reader suite also passes. Broad native suites
remain limited as documented, and full-domain conservation, historical repair and
release readiness are not established by this acceptance.
No release, vendoring or deployment is authorized by this review.
