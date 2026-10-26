# Independent implementation and security reviews

Date: 2026-10-26 UTC. Reviewers were read-only and independent of implementation.

## Correctness review — browse_contract_review

Approved subject to recording broad-suite outcome. Two medium findings resolved:
retain ordinary isfile/404 handling when removing the Roads download wrapper,
with a directory-download regression; update retired archive-member expectations
to physical-filesystem 404 while raw files and metadata are accessible. D-Tale's
existing HTTP200/success=false changed_source envelope remains unchanged.
No remaining blocking contract/correctness findings. Approval does not certify
production rollout or Friday's historical HTTP 500.

## Security review — browse_security_contract_review

Approved subject to relevant tests, which subsequently passed (333 tests).
The same directory-download finding is resolved. Authentication and shared path
security helpers are unchanged. Download, preview and files routes retain
containment and sensitive-target checks. D-Tale retains private dataset scope,
reauthorization and derived-viewer scope inheritance. Normalization still rejects
traversal, NUL and Windows absolute paths. Raw archive-looking names are physical
entries; virtual archive extraction is not enabled. No references remain to the
removed Roads helper. No remaining concrete security finding.

## QA disposition

Targeted suite: 333 passed, 13 warnings in 22.48 seconds via wctl. Covers browse
routes/auth/security/files, D-Tale/freshness, normal/dedicated downloads, Roads
lifecycle and runtime_paths. New physical-state tests use actual files/symlinks
and an actual flock, and read delivered bytes. Existing negative auth/PII/path
cases remain. Large-project collector readback: 155,573 entries in 2.192 seconds.
Broad-suite result is recorded separately in execution_evidence.md.
