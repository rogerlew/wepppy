# Security review — project developer mode

Status: runtime review scaffold; not a security approval. Prepared 2026-10-29 UTC against base `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`.

## Triage and threat model

Impact: high; dedicated review required. New privileged activation route, Dev-only panel access and persistent policy propagation must prevent unauthorized activation without blocking legitimate ordinary operation on an activated project. Mode is not an entitlement to unrelated features. Canonical authority: DM-01 and the checkpoint authority matrix.

## Required surface checks

Use `docs/prompt_templates/security_review_template.md` for the final evidence-backed review. Cover authentication/exact role/project scope/readonly/CSRF, spoofed fields, strict boolean state, concurrency, clone/archive restoration, native argument default and mismatch behavior, observability and valid-state noninterference. Other surfaces (secrets, outbound networking, CI, agent permissions and queue topology) should remain unchanged; confirm against final diff.

## Findings, evidence and verdict

No runtime evidence yet; design reviews are separate artifacts. Gate: **hold** for implementation and direct unmocked valid/hostile boundary checks. All medium/high findings must close before package closeout. Security review does not replace correctness review. Reviewer sign-off and package-owner acknowledgment: pending.
