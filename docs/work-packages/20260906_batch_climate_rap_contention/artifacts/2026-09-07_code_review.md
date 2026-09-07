# Code Review - Batch Climate and RAP NoDb Contention

**Disposition**: Pass; no unresolved high or medium findings.
**Independent reviewer**: `/root/qa` (read-only code and QA review), 2026-09-07.

The reviewer confirmed cohesive collector/finalizer boundaries, explicit output
assignments, no stale-object retry or generic result merge, contextual RAP
future labels/progress/retries, and preserved facade signatures. Snapshot
dict/tuple shapes have concise annotations/docstrings; further abstraction was
not requested.

The initial medium finding that the RAP extraction lost year/band/progress and
retry logs was resolved with labeled futures and a logging regression. Worker
exceptions are logged with identity, peer tasks are canceled, and errors are
re-raised. Commit-outcome and worker exception catches are documented deliberate
boundaries, not fallback behavior.

Complexity telemetry is observe-only. The shared publication helper necessarily
models precommit rollback, confirmed commit, unknown outcome, and ownership
loss; retaining this bounded state handling avoids hiding distinct failure
semantics. No user-visible schema, scientific, or queue changes are introduced.
