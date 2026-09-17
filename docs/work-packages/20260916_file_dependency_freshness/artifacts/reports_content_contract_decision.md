# C08/C09 report provenance checkpoint

Starting implementation: `cf261f6ac`. Status: proposed, implementation pending.
User authorization: execute this package end-to-end; its M2/M3 explicitly includes
confirmed report freshness defects, compatible provenance and checkpoint commits.
No deployment or named-project mutation is authorized by this checkpoint.

Canonical delta: `docs/schemas/report-cache-freshness-contract.md` and linked
Hillslope water-balance section of `docs/schemas/output-scope-contract.md`.
Classification: intended freshness and additive persistence behavior change.
Actual baselines are retained in `reports_freshness_baseline_review.md` and the
native/DuckDB probe, including seven stale cases and historical compatibility.

The new contract binds report rows and provenance inside one atomically published
Parquet. A separate dependency JSON would allow mismatched generations on failure
or concurrent requests; embedding metadata avoids a new multi-file transaction or
lock service. Native H.wat aggregation remains unchanged; only compact output may
be rewritten to attach metadata. Existing version sidecars, columns, calculations,
legacy location, access bits and cache-only availability remain compatible.

Effective source IDs/mapping are retained so settled water-balance cache checks
need not rescan all H.wat rows. Query input resolution follows actual catalog
selection, including permitted parent assets. Missing inputs may permit an
explicitly historical cache read; permission/parser errors may not. A known
changed remaining dependency blocks historical fallback. No newly observed hash
is assigned to a legacy report without rebuilding its rows.

Artifacts: accepted cache/sidecar plus visible UUID attempts under the existing
report cache. Preserve failed native summaries, annotated candidates, observations
and status. Canonical archive, browse and restored-content evidence is required.
Rollback readers ignore added Parquet metadata and still consume the version-1
rows. No mass migration/deletion, schema column change or scientific ADR is needed:
formulas and parameterization are unchanged.

Regression plan: the contract's operation/state matrix, real native and DuckDB
baseline cases, selected mappings/parent sources, read-denial and build mutation,
concurrent coherent publication, historical/native-unavailable compatibility,
failed candidate retention and archive/restore. Producer/prerequisite absence is
not a silent generic exception fallback. Independent correctness and security
reviews approve the scoped design, with measured budgets recorded below.
Implementation follows the standalone ancestor checkpoint.

Review precisions incorporated before implementation: portable run-relative path
identity (including permitted parent relationships); effective catalog SQL alias
identity; explicit translator-resource absence rather than generic RuntimeError
fallback; malformed provenance and verified mismatch cannot downgrade to legacy;
staged native output must retain the canonical destination type/alias/mode checks.

Measured budgets ratified from `reports_performance_baseline_revision3.json`:
C08 added settled validation <=10 ms with persisted summaries, <=30 ms for the
actual parquet fallback (measured composite4.10 ms and fallback14.88 ms).
C09 added settled validation <=10 ms (measured4.08 ms). No settled content reads
and no native ID rescan/DuckDB report query on matching caches. Cold/changed
representative C08 <=2 s with at most two full81.15MB hashes; native ID+summary
~1.01 s, full hash265–294 ms/check. C09 <=100 ms with at most two hashes per
59,450-byte three-file set; existing query~35 ms. Budgets include compact
annotation/publication and are not physical cold-storage/Redis runtime evidence.
Original benchmark output-directory failure and revisions retained.

C09 actual within-project cache-file symlink rebuild is preserved by publishing
to the selected resolved target while retaining the link and checking selection
before commit. C08 keeps its existing native rejection. No maintained writer
creating cross-filesystem report-cache links was found; EXDEV remains an explicit
acceptance risk, not grounds for a speculative external staging topology. Do not
claim that untested layout is preserved or silently add an alternate writer.
A demonstrated real acceptance need requires a separately reviewed refinement.
