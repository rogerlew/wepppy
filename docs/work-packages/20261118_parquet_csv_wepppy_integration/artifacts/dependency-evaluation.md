# Native compatibility dependency evaluation

Date: 2026-11-18 UTC. Status: conditional on checkpoint and parity/resource gates.

The precedent is the accepted standalone parquet/Arrow 60.1.0 evaluation and
owned GeoParquet preflight. Reuse that stack; no new dataframe engine, service,
Python decoder or geometry library is proposed. Existing real climate files use
ZSTD and existing GeoParquet output uses binary WKB. Disabling ZSTD demonstrably
excludes two inventory files, so enabling the existing parquet codec is necessary.

A temporary evaluation manifest enables parquet's zstd feature and directly names
already-transitive serde 1.0.229 and chrono 0.4.45 for strict request parsing and
timestamp formatting. The resolved graph grows from 81 to 88 third-party crates:
zstd 0.14.4, zstd-safe 8.3.0, zstd-sys 2.1.3+zstd.1.5.7, jobserver, pkg-config,
getrandom 0.4 and r-efi. The codec uses a native C build; the existing Rust builder
needs a C toolchain. It introduces no additional runtime process or data model.
Arrow remains the internal representation. Cargo.lock pins the graph; future
version/feature changes require renewed evaluation, not automatic upgrades.

Cargo audit reports zero known vulnerabilities and the existing Chrono
RUSTSEC-2026-0543 maintenance warning. This warning is retained, not described as
clean maintenance evidence. No additional time library is introduced to duplicate
the already required Arrow dependency. See dependency-audit.json and
 dependency-inventory.json for exact versions/results. Release activity or bus
factor is not independently established; no maintenance superiority is claimed.

Conditional acceptance only: run the retained real ZSTD/WKB/timestamp corpus
through the bounded child, compare exact output against the existing Python3.12
oracle, measure memory/time, and exercise hostile compressed input. Owned page
preflight, cumulative decoded limits and OS ceilings stay mandatory. No codec
marketing claim substitutes for those tests. A parity/resource failure blocks
cutover, with no Python fallback. The permanent manifest is unchanged at this
checkpoint preparation stage.

## Implementation disposition

The locked native graph is integrated. Final Cargo audit reports zero known
vulnerabilities; the existing Chrono maintenance warning remains explicit.
All 46 selected real files pass exact legacy CSV byte parity, covering 43 observed
schema/codec combinations plus affected wide/dictionary files. Focused hostile
ZSTD, structural boundary and lifecycle checks pass. Evidence is retained in
real-file-parity.json, focused-validation.json and integration-benchmark.json.
No additional runtime dependency or fallback is introduced by this disposition.
