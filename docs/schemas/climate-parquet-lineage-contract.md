# Climate Parquet producer lineage

Status: implemented PF-R02 behavior; scoped tests/reviews pass. Development-stack
acceptance remains pending in the active freshness package.

## Ownership and identity

`ClimateArtifactExportService.export_cli_parquet` and interchange
`_ensure_cli_parquet` own successful generation of `climate/wepp_cli.parquet`.
Keep current selection precedence, columns, calculations, errors and calendar
fallback behavior. Both producers attach versioned `wepppy_cli_source` JSON
Parquet metadata to the same file as their generated rows. It identifies the
selected CLI path relative to the project, its verified SHA-256, producer and
interpretation version. Interpretation changes require a version change.
Portable selection identity survives copying a project to another root.

Generation parses a retained private CLI snapshot whose verified bytes equal the
selected source at acquisition. Before publication, freshly reload the Climate owner and recheck selected path
and source content; interchange instead reapplies its captured hint/fallback
selection rules, without asserting that they select the Climate owner; changed selection or content rejects the candidate. Reopening the
live path for parsing is insufficient: a change-and-restore race can mix the rows
and receipt. Metadata-only changes with unchanged selected bytes do not reject.
Do not assign provenance to preexisting rows merely by hashing today's CLI.

## Publication and retained evidence

Publish complete rows plus metadata by atomic replacement after all checks.
Create a visible unique attempt below `climate_artifacts/cli_parquet/attempts/`, preserving the
input snapshot, observations, failed candidate and explicit outcome. Failures keep the previous canonical output. Existing explicitly caught
parse/serialization exceptions retain logged-None behavior; other parser errors
(such as IndexError/AssertionError) retain propagation with attempt evidence. No successful receipt is written for failed work.
The guarantee begins at the export entrypoint; earlier climate build directory
cleanup is unchanged and is not covered by rollback claims. The separate visible
Climate artifact directory survives that cleanup, including managed/unmanaged
climate symlink handling. Add it to the canonical skeleton allowlist; archive and
restore retain it. This follows the report-cache separation of retained records
from disposable model working output.

Preserve existing source symlink support, output symlink target selection and
existing output access bits; recheck target selection before replacement. Verify
existing target write authorization by a nontruncating write-open: parent-directory
replace permission alone must not bypass a read-only inode or its ACL. New
outputs follow existing umask. Attempts containing snapshots must not broaden
source/output readability, enforced at creation before any bytes are written. Required permission/read failures remain failures.
Existing path authority is unchanged. Same-filesystem atomic replacement is the
supported publication mechanism; unexpected EXDEV fails explicitly, preserving
prior output, without a speculative external staging layout.

Diagnostic failure after committed replacement must log and cannot remove the
accepted output or report the completed publication as an uncommitted failure.
Overlapping attempts may publish complete generations; next validation always
compares the accepted generation to current selection/content. This does not
promise isolation from arbitrary concurrent writers after the final check.

## Post-fire readiness and legacy behavior

Preserve climate completion ordering relative to watershed abstraction. Replace
CLI-versus-Parquet mtime ordering with validation of embedded producer lineage
against the active CLI selection and current content. Touch/chmod/hard-link
metadata changes do not make matching exports unready; changed bytes, another
selected CLI, missing/invalid proof, unsupported interpretation or failed export
cannot establish readiness for a new post-fire execution. A failed redundant export does not invalidate an older
matching successful proof. Required denied or
malformed reads cannot become ready through a legacy fallback.

Proofless legacy Parquet remains readable by existing report/calendar consumers
and remains archivable/downloadable under their existing contracts. It cannot
establish new post-fire readiness; normal climate regeneration/export establishes
proof. State polling must not regenerate climate, mutate old artifacts or stamp a
receipt onto legacy rows. Existing accepted post-fire result availability retains
its independent recorded source/artifact validation contract. No blanket deletion
or migration is introduced. Interchange's existing-file fast path remains a
calendar compatibility read; it does not certify proofless rows.

The proof is an object with exact fields: integer `version` 1, `source` and
`resolved_source` portable path strings, lowercase 64-hex `source_sha256`, and
`producer`/`interpretation` strings. Accepted combinations are `climate`/`1` and
`interchange`/`1`; booleans are not integer versions. Paths are compared to
observed selections, never opened because a receipt names them. Extra/duplicate
keys, invalid types, unknown combinations or missing proof do not prove readiness.

Readiness validates Parquet framing and bounds footer/proof bytes by existing
rainfall `MAX_TEXT` (1 MiB), in addition to existing file limits, before decoding.
It reads only metadata and validates content from coherent observations. It
must not connect a newer CLI observation to older parsed metadata across an
observable replacement. This includes `content=False` locked authority checks:
metadata must belong to their observed Parquet generation, and active CLI content
is still checked; disabling the full inventory hash map does not disable lineage. Post-fire's existing no-follow/containment authority
remains stricter than generic climate export where it already is stricter.

## Compatibility and regression plan

Metadata is additive: no user-visible column/key is renamed or removed and old
Parquet readers ignore it. Preserve real ClimateFile/PyArrow values and types,
including peak intensities and calendar indices, through both producers and
interchange consumers. No scientific formula/default changes or ADR are needed.

Exercise never-exported, empty/invalid CLI, populated, proofless legacy, malformed
proof, matching proof, changed selection/content, metadata-only operations,
source read denial, actual native write failure, replacement denial, parse-time
and publish-time source changes, source/output symlinks and modes. Verify real
CLI snapshot parsing, native Parquet output, overlapping generation coherence,
archive/restore and generated downstream model artifacts. Retain original
failed probes and partial native output where the backend leaves it available.

Polling performs no producer work or settled full payload/digest rereads beyond
the shared digest admission contract; bounded Parquet footer reads are expected. Measure full readiness and export against
representative files before ratifying a latency budget; no new persistent cache,
daemon, dependency or digest admission policy is authorized here.

Representative local mean budgets (46-year/1.18-MB and 120-year/3.11-MB CLI,
OS cache warm): lineage readiness component <=10 ms settled and <=50 ms with a
cold/evicted digest; zero settled CLI payload rereads, bounded footer reads.
This excludes existing whole-project owner/raster checks, which retain their
separate full-state acceptance gate. Complete snapshot/parse/export/metadata/
publication <=1.5 s for the 120-year case, with <=200 ms added lineage overhead.
Measured prototype: settled1.25–1.44 ms, cold~12 ms, composed export~0.91 s and
added overhead~101 ms. Implementation must repeat these full-path measurements;
prototype timings do not prove final runtime performance or cold NFS behavior.

Budget correction: the original <=5/40-ms prototype budget omitted mandatory
post-fire no-follow directory traversal. The implemented predicate initially
measured8.28/10.78ms settled, with43.85ms in the large eviction case, failing that
budget. Profile-guided same-call parent-descriptor reuse reduced settled means
to5.82/6.98ms while preserving O_RDONLY permissions, leaf opens, containment and
parent/path association checks. No descriptor survives a call. Independent
correctness, security and QA reviews support the explicit10/50-ms correction
instead of weakening authority or adding a cross-request descriptor cache. The
original failures remain evidence. Revised acceptance still requires actual full
predicate measurements, zero settled payload reads, unchanged export budgets and
separate full-state/runtime gates; quick profiles alone do not establish it.

## Daymet acquisition source preservation

Daymet acquisition parquets (`daymet_<start>-<end>.parquet` and interpolated
`daymet_observed_<id>_<start>-<end>.parquet`) are source artifacts distinct from
CLI-derived `wepp_cli.parquet`. After acquisition writes them, downstream PRN
and CLI preparation must treat them as read-only: preserve precipitation in
millimeters, temperatures in Celsius, original radiation, and source columns.
Use a separate working copy for unit conversion. Generated radiation adjustments
and their provenance belong in the existing normalization CSV and CLI, not an
overwrite of the source parquet (ADR-0006).

This preserves auditability: a labeled source column cannot silently become a
converted CLIGEN field. It does not impose filesystem chmod or prevent a normal
explicit climate rebuild from acquiring new source data. Existing artifacts are
not automatically migrated or interpreted by value magnitude. Legacy radiation
provenance columns remain readable and unchanged by downstream preparation;
previously mislabeled precipitation/temperature artifacts require an explicit
rebuild from original data, not an unqualified unit conversion. CLI-derived
parquet producer lineage and interpretation versions are unaffected.

Implementation conformance: source-preservation fix verified by focused tests
and real CLIGEN replay; see the 20260917_daymet_source_preservation work package.
