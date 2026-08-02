# Security Review - Omni Fork Symlink Retarget Hardening

**Status**: Pending implementation review
**Security impact**: high

- [ ] Only allowlisted Omni child locations are rewritten.
- [ ] Old targets are never followed.
- [ ] Target calculation and child names cannot escape the destination.
- [ ] Replacement is atomic and failure cannot publish success.
- [ ] Unrelated links are preserved and cross-run data is not materialized.
- [ ] RQ errors remain explicit and contract compliant.

Release gate: hold pending independent review.

