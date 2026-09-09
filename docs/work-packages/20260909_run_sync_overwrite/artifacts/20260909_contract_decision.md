# Contract decision — 2026-09-09

Starting revision: ce81dbe787f7a7287fe539d02ba07634c5e4e086.
Classification: intended behavior change, not an unchanged-contract repair.
Operator approval: user explicitly requested partial cleanup and replacement of
changed files, then said “yes, please make the changes”. Commit authority has
not been granted.

Canonical delta: new docs/schemas/run-sync-contract.md, replacement semantics,
failures, compatibility and regression obligations. Applicable unchanged
contracts: docs/schemas/rq-response-contract.md and
 docs/schemas/nodir-contract-spec.md (aria2c.spec).

Observed source manifests have no checksums. Therefore refresh all listed files;
retention by size or aria2's already-completed check would violate the approved
intent. No source-side checksum feature is proposed. Local edits to listed files
will be replaced; unlisted files remain. Partial progress is intentionally lost.
No project schema or model parameterization changes are proposed.

Security impact: low, bounded worker filesystem deletion. Validate all paths and
sidecar collisions before deletion, reject symlinks, preserve authentication.
Regression matrix and real-boundary evidence requirements are in the contract.
Two independent read-only reviews and disposition precede a standalone docs
commit; no implementation edits are authorized by this uncommitted checkpoint.

Review refinement: safely stage the downloaded manifest by exclusive creation,
validate payload and control paths together, and reject ancestor conflicts.
These checks are necessary to contain the newly authorized cleanup boundary.
Empty manifests remain valid transfer no-ops. See contract review disposition.
