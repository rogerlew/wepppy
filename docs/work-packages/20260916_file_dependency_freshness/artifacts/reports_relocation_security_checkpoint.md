# Report-local catalog relocation security checkpoint

Independent reviewer: `freshness_security`, 2026-09-17 UTC. Reviewed the final
"Relocated landuse catalogs" canonical amendment and
`reports_relocation_contract_decision.md` before normalization code. This is a
bounded refinement to ancestor `7d78e9810`, not approval of the uncommitted report
implementation or of package/runtime closeout.

## Disposition

**Scoped PASS.** The amendment addresses a confirmed selected-input defect and
does not authorize broader filesystem reads, an on-disk catalog rewrite or a
shared query-engine behavior change. Implementation and actual relocation
regressions remain required.

The independent correctness revision3 probe retains two real failures: a copied
partial archive loses historical access after its old root is removed; a
complete copy with local runoff changed to 900 still reports 100 from the old
root while that root exists. Both hashing and query SQL currently select the
old root. The earlier QA inference of mismatched query/hash selections was
corrected; this review does not repeat that inference.

## Actual authority and compatibility boundaries

`query_engine.core.build_query_plan` uses `catalog.root` to resolve table sources;
the executor's `base_dir` sets DuckDB's home directory and does not redirect that
SQL. One cloned report-local context/catalog must therefore govern both actual
query production and dependency observations. A hash-only correction would be
incorrect. Preserve schema-driven alias metadata in the clone.

Maintained `activate_query_engine` records its requested activation base as the
catalog root. `_canonicalize_nodir_parquets` and `_attach_fs_path` encode inherited
`_pups` assets as absolute parent `fs_path` values. Rebased parent relationships
are consequently supported-input compatibility, not a speculative extension.

Apply current allowed-root selection precedence before translating an old
absolute reference. Only validated old-root or matching allowed old/new `_pups`
parent relationships may be translated. Relative traversal rejection, symlink
escape rejection and existing resolver validation remain active. A missing
individual inherited file differs from the absence of any allowed parent
relationship; a standalone restored child must not silently read its former
parent. Do not rebase arbitrary outside references or infer a new allowed root
from a persisted path. Overlapping old/new ancestors need explicit regression
coverage for the specified current-root precedence.

The context change is local and in memory. It preserves normal read-only report
access and leaves the stored catalog available as original provenance. Dependency
identities remain portable relative paths; attempt diagnostics retain the actual
resolved selections. Query and observation must agree on those selections before
and after production.

## Required implementation evidence

Exercise actual DuckDB results for complete and partially archived copies, with
the original both present and removed; absolute local and inherited-parent
entries; current allowed absolute selections; overlapping roots; denied reads,
invalid traversal and escaping symlinks. Verify no on-disk catalog mutation and
no read from the old project for a rebased source. Retain numerical result and
embedded-proof agreement, native report behavior, publication/mode safeguards
and the existing performance gates. This checkpoint does not close the separate
partial-absence, malformed-proof or read-only historical findings from the
ongoing implementation review.
