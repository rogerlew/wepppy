# Security review

Reviewer: independent `ttl_contract_security`, 2026-11-06.
Checkpoint: `5e35c480e`; impact high by existing public catalog-route scope.
Gate: PASS; no unresolved findings.

Server and post-bulk partitions preserve rows, scope and TTL state. Unknown
metadata never implies protection. Help retains its same-origin `url_for`
destination and text rendering stays safe. Scoped CSS/colgroups introduce no
mutation, external resource or authorization boundary. Existing bulk response
validation, CSRF, generation guards and retries remain intact. Tests exercise
both directions, unknown/disabled groups, bulk reordering, pointer/keyboard
navigation, owner layouts, wrapping, pagination and narrow displays. The forest
log demonstrates restored real navigation; its development worker reload is
separate operational evidence and not a production rollout claim.

See validation.md for exact outcomes and the documented broad-suite omission.
