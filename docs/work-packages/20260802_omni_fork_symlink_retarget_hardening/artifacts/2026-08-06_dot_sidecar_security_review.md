# Dot-Sidecar Compatibility Security Review

- **Reviewer**: independent security agent `omni_dotlog_security_review`
- **Date**: 2026-08-06
- **Disposition**: approved; no unresolved medium or high findings

The final branch uses descriptor-relative no-follow stat, then ignores a
dot-prefixed entry without opening, following, rewriting, or deleting it.
Non-dot unexpected entries remain fail closed. Removing the abandoned identity
machinery also removed its ancestor-replacement TOCTOU surface.

Accepted residual: all dot-prefixed collection entries are preserved outside
normalization inventory. Historical rsync/archive behavior and access-log
privacy remain separate, unchanged surfaces.
