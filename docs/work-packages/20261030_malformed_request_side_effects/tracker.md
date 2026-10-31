# MRS-01 tracker

Status: Closed locally 2026-10-30; split-run validation limitation retained.

## Authority and scope

Operator-authorized documentation checkpoints: `3ab204e9c` (initial contract) and
`ca28085ac` (four bounded follow-on field groups). Both are ancestors of the working
implementation. Implementation is uncommitted; no deployment, production jobs,
branch changes or dependency installation. Unrelated Roads and release work remains
outside this package. Historical WAM-01 records remain unchanged.

## Progress

- Discovery and baseline actual-HTTP reproduction complete; 429 source records are a discovery index, not 429 confirmed defects.
- Shared strict JSON/form/boolean validation and typed framework error translation implemented.
- Confirmed direct parsers, early controller writes/recovery, upload promotion, bounded numeric failures and enclosing catches repaired.
- Real WAM-01, input uploads, optional controllers, Flask Ron/Ash, batch directives and treatment raster persistence evidence passes focused tests.
- Independent correctness and QA reviews report no open reviewed-scope findings; security review also passes, including final session-token actual-body inspection.
- Complete microservices/Flask regression: 4,017 passed, 74 skipped.
- Full canonical suite reached 4,117 passes / 125 skips, then collided with an unrelated active pytest NoDb lock. Both failing parameter cases pass with unique temporary run names; remaining collection completed with that isolation. Exact evidence and limitations: [validation](artifacts/validation.md).

## Decisions and discoveries

The [canonical contract](../../schemas/request-payload-contract.md) preserves empty
requests, forms, native/legacy flags and domain-specific null/blank/list semantics.
Malformed syntax cannot become defaults; supplied bounded fields validate before
business mutation. [Follow-on decision](artifacts/followup-contract-decision.md)
records why four additional domain groups needed a second ancestor checkpoint.

Transport buffering is temporary and cleaned; source promotion follows validation.
Sibling staging preserves relative VRT references. Form parser errors survive CSRF
pre-reading, while size limits still reject before buffering oversize input.

## Verification and remaining limits

See [consumer matrix](artifacts/consumer-matrix.md), [validation](artifacts/validation.md),
[correctness review](artifacts/correctness-final-review.md) and
[QA review](artifacts/qa-final-review.md). The default broad-exception gate passes after reviewed exact allowlist location
maintenance and explicit cleanup-boundary entries.
No production observation is claimed. No temporary mitigation requires retirement.

## Closeout

Final isolated suffix: 7,832 passed / 245 skipped / 4,743 deselected. Independent QA
verified distinct-node accounting: 12,451 passes + 368 executed skips = 12,819
collected tests, plus one collection skip. The plain full command remains a failed
invocation; split runs cannot prove uninterrupted same-process suite behavior.
All confirmed MRS-01 findings are closed. Canonical contract, consumer dispositions,
review artifacts and logs are retained; implementation is uncommitted, not deployed.
Follow-up test ergonomics: use unique NoDb run names for real-Redis fixtures.
