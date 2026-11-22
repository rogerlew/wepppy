# Large-watershed Parquet interchange

On 2026-11-22 the hillslope PASS child for diagonal-intersection failed on physical row group 32,768. The original model run had 47,582 hillslopes. A row group is a storage unit inside a Parquet file. Each source currently forces at least one group when it has rows.

## Scope and compatibility

Trace every shared native sink, other interchange writers, AgFields publication and completeness, and baseline and Roads totalwatsed3 readers and writers. Keep existing single-file paths, schemas, row order, scientific values, source identity and atomic publication. Allow a physical group to hold consecutive sources or a source to span groups. Bound decoding work for packed inputs and retain ordinary layout where feasible. Compare old and new physical layouts through production readers, including selected hillslopes. Validate public writers beyond the failing boundary and read actual footer counts and data.

Complexity budget covers existing native and Python paths, regression tests and paired build. Security impact is low. There are no new privileges or services. Observe freshly generated artifacts and dependent daily totals during the first large-run replay. A matching footer with missing or duplicate identities is a failure. Production replay is a distinct operational outcome.

See the [execution plan](prompts/active/implementation.md) and [tracker](tracker.md).
