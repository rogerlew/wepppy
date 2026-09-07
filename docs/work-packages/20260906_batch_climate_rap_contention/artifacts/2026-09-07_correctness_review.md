# Correctness Review - Batch Climate and RAP NoDb Contention

**Status**: Pending implementation and independent review.

Use `docs/prompt_templates/correctness_review_template.md`. Review absent,
empty, populated, supported legacy, malformed, unrelated-rewrite,
relevant-rewrite, collection-failure, and finalization-failure states for both
controllers. Direct evidence must exercise real NoDb hydration, signatures,
locks, and dumps.
