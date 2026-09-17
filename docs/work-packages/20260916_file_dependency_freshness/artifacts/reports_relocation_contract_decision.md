# Report-local catalog relocation refinement

Base `7d78e9810`; current report implementation is uncommitted and contains no
catalog-root normalization. Authorization remains execution of the full freshness
package, including compatible archive/restore. Scope: C09 selected context only.
Current canonical amendment: final section of
`docs/schemas/report-cache-freshness-contract.md`.

Independent actual copied-run probes show stored catalog.root selects old inputs
or reports all inputs missing after relocation. The current implementation's
hashes and query both select that old root; changing only the hash resolver would
create mismatched provenance. Query-engine build_query_plan uses catalog.root;
executor base_dir only sets DuckDB home_directory. The initial QA message that
inferred a query/hash mismatch was corrected after tracing those actual calls.

Normalize one cloned report-local context/catalog for query and observation,
without disk writes or shared query-engine edits. Relative selections retain
existing checks; explicit current allowed-root entries win, otherwise translate
validated old-root/old-parent paths by their known relocation relationship.
Actual child inheritance uses absolute parent fs_path, so that case is required.
No arbitrary external rebase or new containment capability is authorized.

Compatibility/regression plan: present and partially removed relocated sources;
absolute local entries; inherited parent inputs under matching _pups roots;
current allowed absolute entries; invalid traversal, symlink escape and external
selection; unchanged portable cache identities and actual query result/proof
agreement. Historical reads with absent catalogs must not require activation or
write access. Full provenance validation and malformed/read-denied source handling
are conformance fixes under the existing checkpoint, not new fallback authority.
Retain original failed probes. Performance budgets and publication schema remain
unchanged. Independent correctness/security review precedes the ancestor commit.
