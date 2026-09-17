# Remaining post-fire freshness boundary review

Independent M1 discovery by `freshness_security`, 2026-09-17 UTC, working tree
after checkpoint `dd5d09ca7`. No production/test edits or named-project mutations.
All probes create disposable local files; this is not implementation approval.

## Findings first

| ID | Severity | Confirmed boundary and disposition |
| --- | --- | --- |
| PF-R01 | Medium, OPEN | Accepted M3 source equality embeds raw soil inode/timestamp and SQLite main/WAL/SHM identities. Seven real operations preserve consumed rows/schema but change accepted equality, including byte-identical link/chmod/touch/replacement. This is remaining false-stale behavior; SQLite execution guards must not be removed to repair it. |
| PF-R02 | Medium, OPEN | Climate readiness uses parquet mtime >= active CLI mtime rather than producer association. A touch rejects identical input. A valid equal-size/restored-mtime CLI precipitation change from 4 to 8 mm leaves the actual exported parquet at 4 mm while the actual readiness check remains true. |

PF-R02 is a false-current **prerequisite**, not evidence that the already
accepted result survives the byte change: the new accepted-source hashes
correctly mark that prior result stale. It can still admit a new attempt whose
rainfall reader consumes the old parquet, so hashing CLI and parquet separately
does not prove that one was derived from the other. Neither finding is an auth
bypass or a demonstrated arbitrary concurrent-writer exploit.

## Real evidence and limits

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/postfire_remaining_probe.py -v -s --maxfail=1
```

`postfire_remaining_probe.log`: **8 passed**, 13 warnings, 16.81 seconds.
These are defect-characterization assertions, not fixed acceptance tests.

Seven SQLite cases invoke actual `snapshot_cache`, `production_soils.inventory`,
`_source_snapshots_current` and `verify_snapshot`. In each case the consumed
`source_schema` and typed logical table hashes agree before/after, but inventory
and accepted equality differ. Link, chmod, touch and copy2/replace preserve main
file bytes. VACUUM, committed-WAL checkpoint and an unrelated-table write change
physical main bytes without changing consumed rows/schema. Strict
`verify_snapshot` rejects all seven; that is expected under its existing
transaction contract. The accepted comparison fixture holds all nonsoil inputs
constant; it is not a full M3 numerical execution or accepted NoDb migration.

The climate case uses the existing real NoDb owner/RedisPrep fixture, the actual
`ClimateArtifactExportService.export_cli_parquet`, real ClimateFile parsing and
the actual `production.sources` function. A touch makes `checks['climate']`
false while accepted content equality remains true. Rewriting a valid CLI at
the same length and restoring its original mtime leaves the parquet unchanged,
produces native parsed precipitation 8 rather than 4, and leaves climate
readiness true. No readiness or parsing function is mocked. It is an isolated
owner fixture, not a complete new WEPP/debris-flow run.

Additional command:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/postfire_sqlite_collision_probe.py
```

`postfire_sqlite_collision_probe.log` records **300 real committed row changes,
zero identical complete inventories and zero false-current comparisons** on
the container temporary filesystem in DELETE journal mode. The probe restores
mtime without faking ctime or sleeping. This bounded negative result does not
prove stat-key collision immunity for SQLite, WAL or NFS. A SQLite false-current
cache collision is **not established** by this review and must not be reported
as if the ordinary-file collision probe had demonstrated it.

## Supported producers and distinct guards

`production.sources(model='M3')` places `production_soils.inventory` in
`selections['soil_inputs']`. The new `_source_snapshots_current` strips ordinary
file timestamps but compares selections exactly. Thus this soil selection
remains metadata-sensitive even when ordinary source/artifact content handling
passes. `inventory` includes present/absent dependency metadata, prepared evidence
hashes and `soil_snapshot.source_state` for main, WAL and SHM. It does not
recompute the logical SQLite core during polling.

`soil_snapshot.snapshot_cache` refuses rollback journals and symlinks, bounds
regular inputs to 512 MB, copies main and present WAL through `open_local`, and
opens only the disposable copy in a read transaction. It disables extension
loading/trusted schema, bounds table content, and compares source identities
around the complete copy/read. It sorts typed rows deterministically and hashes
the consumed component/chorizon columns and their declared schema. SHM is a
coherence/presence observation, not the scientific table payload. `verify_snapshot`
and locked publication retain source identity checks after logical comparison.

The supported SSURGO collection writer in `wepppy/soils/ssurgo/ssurgo.py`
(`_connect`, `_configure_sqlite_connection`, `_ensure_wal_mode`) normally uses
WAL for project caches. Acquisition commits both scientific table rows and
`bad_*` bookkeeping table changes; read connections and connection closure can
affect WAL/SHM lifecycle. Actual SQLite checkpointing is therefore a relevant
physical/logical distinction. This review does not claim that an application
calls explicit VACUUM; that case demonstrates supported SQLite storage equivalence.
No reviewer connected to or checkpointed a named source database.

`source_preparation.prepare_local_sources` embeds schema/raw-state/logical hashes
in receipt `cache_identity`; `promote_local_sources` and
`production_soils.activate_sources` verify it against authoritative basin data.
`prepare_soil` tracks optional presence and dependencies; `verify_soil` repeats
logical and source checks outside result acceptance, then publication checks
strict snapshots under the controller lock. Those receipt/coherence/ownership
checks must remain distinct from accepted-result scientific equality.

For climate, `ClimateArtifactExportService.export_cli_parquet` parses the active
CLI and writes event parquet, but records no source-content receipt. Its logged
export-error boundary returns None; `ClimateBuildRouter.build` and
`Climate.set_user_defined_cli` can subsequently timestamp overall climate
completion. The existing production M1 contract explicitly introduced the mtime
guard to reject old parquet after failed export. `production.sources` therefore
conforms to that guard today; changing it requires a reviewed domain amendment.
The rainfall backend consumes `paths['cli']` (parquet). Active CLI bytes are
tracked as a dependency, but their independent hashes do not establish lineage.

## Smallest compatible fix constraints

For PF-R01, first ratify accepted **scientific** soil identity separately from
live main/WAL/SHM state and transaction receipt identity. Existing logical
schema/table hashes are a useful primitive, but not yet a cheap status API.
Preserve explicit collection evidence, source paths, MUKEYs, raster masks,
THICK identity/units/grid/bounds, missing optional inputs and policy version.
Do not replace SQLite state with a hash of only its main file, treat a live WAL
database as immutable, or strip raw identity from copy, promotion, finalization
or rollback checks. Hashing the whole physical database would still stale on
the proven checkpoint/VACUUM cases.

Any reusable logical observation must first come from the current coherent
snapshot mechanism and validate its complete source set. A cache hint is not
accepted science or permission to ignore a new WAL/journal. State reads must
remain bounded/local, perform no source write, checkpoint, schema migration,
acquisition or soil build, and preserve visible diagnostics/failed copies.
The frequency, artifact placement and cost of logical revalidation need their
own measured checkpoint; this review does not authorize a polling-time SQLite
copy or a new persistent cache.

For PF-R02, the smallest meaningful correction is producer-owned evidence tying
the active CLI content to the successfully exported parquet, then consumer
verification of that association. Merely remove the mtime condition or hash both
current files independently and the failed-export case remains unsafe. Bind
source selection, successful output content and relevant exporter interpretation;
publish evidence only after a coherent successful export. Preserve receipts,
calendar/peak-intensity semantics, read-only state polling and the explicit
export failure path. Sidecar versus parquet metadata and atomic publication
details require a concrete checkpoint, not a new workflow inferred here.

## Legacy and unproven assumptions

- Existing soil snapshots can lack logical accepted identity, prepared source
  metadata or the cache entirely. Missing model remains M1. Do not invent old
  source hashes from present bytes or reject legitimate absent/fallback states.
- Some retained soil manifests already contain logical hashes; any reuse or
  migration must prove that they belong to the accepted result and full relevant
  source inventory. Their mere presence is not migration authority.
- Existing climate parquet has no demonstrated source receipt. The current
  timestamp guard cannot be promoted to proof by hashing today's files. Decide
  legacy behavior explicitly, retaining historical reports/downloads and avoiding
  silent climate rebuilding during state reads.
- NFS visibility, logical recheck latency/working-set cost and native end-to-end
  result propagation remain unmeasured here. Prepared raster dependency closure
  is still separately open. The negative SQLite collision sample establishes
  no general collision theorem and no arbitrary writer isolation.

PF-R01/PF-R02 remain OPEN for the main package. Preserve the existing SQLite
safety tests for committed WAL, rollback-journal spill, concurrent read mutation,
symlink swaps, absent sources and retained incomplete attempts in any next wave.
