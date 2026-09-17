# Contract decision

2026-09-17 UTC. Owner explicitly: “please fix it.” Prior incident shows only
active CLI ctime drift during WEPP hard-link materialization. Current contract's
strict active guard causes the failure; amend rather than silently bypass it.
Normative amendment: docs/schemas/file-dependency-freshness-contract.md, active
CLI hard-link amendment. Scope, checks and compatibility are specified there.
No schema/API/formula changes. Fresh coherent uncached content verification is
required only on the narrow mismatch; otherwise preserve strict fast path.
Security/correctness reviews and separate ancestor checkpoint precede code.
Regression: real os.link/unlink during M3 stages, changed bytes with restored
mtime, malformed/hashless snapshots, path/symlink and selection changes.
Runtime: restart workers and overlap real WEPP materialization with real M3.
