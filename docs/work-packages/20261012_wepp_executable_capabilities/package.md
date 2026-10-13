# WEPP executable capabilities and rerun selection

Status: implementation committed (`3c114719b`); Forest acceptance passed, broad Python gate pending. Scope CBEXEC-01 implements operator-requested WEPP 261010 availability, future release selection on existing Config Builder projects, and sidecar-owned MOFE support. Execute this package, not the earlier soil anisotropy package.

Use the existing wepp-forest default-branch worktree at `/home/workdir/wepp-forest-release-20261009` (branch `wepp_260430_negmeltfix_comparator`); preserve unrelated edits in `/workdir/wepp-forest`. Remint and vendor only 260803/261010 sidecars, preserving binary bytes and provenance. No new dependencies, services, queue topology, scientific defaults, or production deployment. Security impact: high by public submission/executable-selection boundary; dedicated final security review required.

Canonical contract: [WEPP executable selection](../../schemas/wepp-executable-selection-contract.md). Active plan: [ExecPlan](prompts/active/wepp_executable_capabilities_execplan.md).
