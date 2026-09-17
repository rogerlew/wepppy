# Report-local relocation correctness checkpoint

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC.
**Scoped PASS** for the final relocated-landuse-catalog section of the report
cache contract and `reports_relocation_contract_decision.md`. No code edits.

The retained actual-report probe confirms the need: after a complete copy with
the original still present, changing local runoff from 100 to 900 produces a
report marked `built` with the original 100 mm result. A partial copy with the
original removed incorrectly reports all three sources absent. Rebasing only
the saved catalog root in a disposable control restores historical availability.
See `reports_implementation_correctness_probe_revision3.json` and earlier logs.

`query_engine.core.build_query_plan` uses `catalog.root` to construct actual SQL
paths; the executor's requested base directory does not replace those paths.
Normalize a cloned report-local context for both observations and queries.
Changing only the hash resolver would create mismatched provenance. Maintained
activation writes its current base as catalog root, while inherited child assets
use `fs_path`, so this corrects stale location metadata without removing a
maintained catalog-root redirection workflow.

The proposed ordering is correct: keep explicit current allowed-root references
first, otherwise translate validated old-root or corresponding old-parent
references. Current precedence handles nested/overlapping old and new roots.
Retain existing relative traversal and resolved symlink checks. An inherited
file need not exist to establish a valid parent relationship; its absence can
be historical. A standalone child lacking that relationship cannot reuse its
former parent's files. Reject external/ambiguous references rather than guess.

Keep this normalization local to the two report operations that must share its
context; do not rewrite disk catalogs or alter shared query-engine behavior.
Preserve identifier alias metadata and reselect/recheck through the same
normalization after query work. Actual normalized paths belong in diagnostics;
portable relative identity belongs in embedded provenance.

Implementation acceptance must use real query results and selected-path/proof
assertions for complete/partial copies, absolute local references, inherited
parent references, already-current absolute entries, overlapping roots, missing
catalog history, and traversal/symlink/external rejection. Shared catalog objects
and stored catalog bytes must remain unchanged by normalization. The existing
performance and publication gates remain in force; this checkpoint does not
approve the outstanding malformed-proof or legacy parser-failure findings.
