# Security Review - Batch Climate and RAP NoDb Contention

**Status**: Pending implementation and independent review.
**Security impact**: `high`

Use `docs/prompt_templates/security_review_template.md`. At minimum review
run-tree containment, NoDb lock ownership, atomic persistence, stale-input
rejection, partial artifact publication, worker/subprocess boundaries,
diagnostic leakage, queue failure behavior, and valid-state non-interference.
