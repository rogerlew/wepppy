# Independent contract reviews and disposition

Base revision: `991fc5e2c3f1cd2e5d74169e2d7bccb609203924`.
Reviews completed 2026-11-11 04:08 UTC before source or test edits.

- Correctness reviewer `/root/contract_review_one`: approved. Reviewed decision,
  Bootstrap/browse/freshness canonical contracts, service guidance and matrices.
- Security reviewer `/root/contract_review_two`: approved. Independently reviewed
  scope, ordering, all reader/advertisement boundaries, byte access and exclusions.

## Findings and disposition

- Medium: draft Bootstrap wording required suffix checking on rename/copy paths.
  Corrected to preserve existing blanket rejection; both reviewers verified.
- Medium: freshness contract required supported readers unchanged. Added the
  bounded pickle exception and reciprocal browse cross-link; both verified.
- Low: duplicate browse heading removed and verified.
- Low: Bootstrap user/operator spec discoverability. Added canonical restriction
  link under General safety.

No unresolved medium/high findings. The primary agent accepts both reviews.
The focused-suite waiver is retained. These approvals establish the contract
checkpoint only; implementation and deployment evidence remain pending.

## Supplemental archive clarification, 2026-11-11 04:10 UTC

Both independent reviewers approved preserving retired archive traversal errors
and whole-archive byte download after inspection of `runtime_paths/fs.py` and
existing route tests. The initial plan incorrectly assumed virtual archives were
active. The canonical browse exception and failure-class matrix now distinguish
physical files under NoDir roots from retired archive members. No archive access
is restored; no production implementation preceded this clarification.
