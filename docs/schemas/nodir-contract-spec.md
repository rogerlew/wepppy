# NoDir Contract Spec (Directory vs `.nodir` Project Trees)
> **Archived / Deprecated (Historical, 2026-02-27):** This NoDir specification is retired from active contract flow after the directory-only reversal. It is retained only for historical/audit reference.

> Contract for representing selected run-scoped project trees as either a real directory or a single-file `.nodir` archive (zip container), while preserving “directory-like” semantics for code and the browse service.
> **Work package:** `docs/work-packages/20260214_nodir_archives/package.md`
> **See also:** `docs/schemas/nodir-thaw-freeze-contract.md` (thaw/freeze state tracking + crash recovery)
> **See also:** `docs/schemas/nodir-touchpoints-reference.md` (consolidated module-level projection/mutation/materialization audit matrix)

## Scope
- Applies to run working directories (WDs) returned by `get_wd(runid)` (typically `/wc1/runs/<prefix>/<runid>/`).
- Targets project trees that are currently “many-small-files” hotspots:
  - `landuse`
  - `soils`
  - `climate`
  - `watershed`
- Explicitly out of scope:
  - `wepp/` (WEPP executables require real filesystem paths).
  - Arbitrary user-supplied archives (NoDir archives are server-generated artifacts only).

## Definitions
- **WD**: the run working directory (filesystem root for a run).
- **NoDir root**: one of the logical roots listed above (e.g., `watershed`).
- **Directory form**: on-disk tree rooted at `WD/<root>/`.
- **Archive form**: on-disk archive file at `WD/<root>.nodir`.
- **Logical path**: a `/`-separated path relative to WD that callers use (e.g., `watershed/hillslopes/h001.slp`).
  - Logical paths for NoDir roots MUST NOT include `.nodir`; representation is an internal resolution detail.
- **Mixed state**: both `WD/<root>/` and `WD/<root>.nodir` exist.
- **Admin** (browse service): JWT `roles` claim includes `admin` or `root` (no explicit opt-in query params).
- **Archive boundary**: the first path segment ending in `.nodir` (e.g., `watershed.nodir` in `watershed.nodir/hillslopes/h001.slp`).
- **Inner path**: the remainder of the path inside the archive after the archive boundary (e.g., `hillslopes/h001.slp`).

## On-Disk Layout and Naming
- Directory form:
  - `WD/<root>/...` exists as a normal filesystem directory tree.
- Archive form:
  - `WD/<root>.nodir` exists as a regular file.
  - Zip entry names MUST be stored relative to the root (no leading `/`, no drive letters, no `..` segments).
  - Zip entry names MUST use `/` separators (normalize `\\` to `/` when creating archives).
  - Archive entries MUST represent regular files/directories only (no symlinks, device nodes, FIFOs, sockets).
  - Freeze/migration tooling MUST dereference symlinked *files* and store their content as regular file entries in the archive.
    - Symlink metadata MUST NOT be preserved.
    - Symlinked directories are invalid input unless explicitly supported by the migrator (default: fail fast).

## Representation Selection and Precedence
- Whether a NoDir root is directory-backed or archive-backed MUST NOT be serialized into NoDb subclasses or any `.nodb` payloads.
  - Representation MUST be discovered at time of use via filesystem existence checks.
  - Rationale: runs may be migrated/archived out-of-band; persisted flags will drift.
- If `WD/<root>/` exists and `WD/<root>.nodir` does not exist: `<root>` is **Directory form**.
- If `WD/<root>.nodir` exists and `WD/<root>/` does not exist: `<root>` is **Archive form**.
- If both exist:
  - Implementations MUST treat Directory form as the source of truth (writable, authoritative).
  - Implementations MUST NOT expose two separate logical trees for the same root in non-admin views or public APIs.
  - Implementations SHOULD log a warning (mixed-state run tree).
  - Implementations MUST NOT delete either representation as part of discovery/reads.
    - Cleanup (removing or renaming stale `.nodir`) is a maintenance operation owned by migration tooling after verification.
- If neither exists: `<root>` is missing.

## Path Semantics (Directory vs Archive)
- Logical paths for NoDir roots (`<root>/...`) resolve by representation:
  - Directory form: `WD/<root>/<inner_path>` (filesystem)
  - Archive form: `WD/<root>.nodir` + `<inner_path>` (zip entry)
- Archive-boundary paths (`<root>.nodir/<inner_path>`) are an external syntax (browse/files/download URLs) and MUST normalize to the same archive resolution.
- Archive boundaries MUST NOT be nested (no `a.nodir/b.nodir/...` semantics).
- Inner path normalization MUST reject:
  - Null bytes
  - Absolute paths
  - Any `..` segment

## Required Behaviors (API-Level)

### Minimal NoDir Interface (Recommended)
- Implementations SHOULD expose a small “filesystem-like” API so call sites do not branch on directory vs archive:
  - `listdir(logical_dir)` → immediate children + basic metadata (is_dir, size, mtime)
  - `open_read(logical_file)` → stream bytes
  - `stat(logical_path)` → basic metadata (is_dir, size, mtime)
  - `exists(logical_path)` / `is_dir(logical_path)` helpers
  - `copy_out(logical_path, dst_fs_path)` for bridging to tools that require real filesystem paths
  - `rm_tree(<root>)` for run cleanup (directory: `rmtree`, archive: unlink `.nodir`)
- Per-file mutation primitives (`write_file`, `rm_file`, `mkdir`) SHOULD NOT be the default abstraction for NoDir roots; prefer explicit thaw/freeze workflows.

### Listing
- Listing a NoDir root MUST return “directory-like” entries:
  - `(name, is_dir, mtime, size_or_child_count, ...)` for HTML browse.
  - JSON equivalent for the `/files/` API.
- For Archive form:
  - Directory membership is derived from zip entry prefixes.
  - `size` and `mtime` MUST be populated from zip metadata where available (best-effort).
  - Listing MUST NOT extract the archive to disk.

### Reads
- Reading a file within a NoDir root MUST support both forms:
  - Directory form: read from the filesystem path.
  - Archive form: stream the zip entry content.
- Reads MUST enforce the same run-root security invariants as filesystem reads (no escaping WD).

### Writes / Mutations
- This contract assumes NoDir roots are *mostly immutable* after generation.
- Any feature that mutates a NoDir root MUST define one of:
  - **Thaw/Freeze**: materialize to `WD/<root>/`, mutate, then rebuild `WD/<root>.nodir` and remove `WD/<root>/`.
  - **Directory-only**: require Directory form while editing; Archive form is a post-processing optimization step.
- Implementations MUST NOT attempt in-place zip mutation as a default behavior (zip updates are rewrite-heavy and failure-prone on NFS).

## Thaw/Modify/Freeze Protocol (Atomic Tracking)
Thaw/modify/freeze state tracking, locking, and crash recovery are specified in `docs/schemas/nodir-thaw-freeze-contract.md`.

Key integration hooks (non-exhaustive):
- Per-root state file: `WD/.nodir/<root>.json` (atomic updates via temp + `os.replace()`).
- Maintenance lock: `nodb-lock:<runid>:nodir/<root>` (fail-fast; acquire multiple roots alphabetically).
- Transitional states (`thawing|freezing`) MUST be treated as locked by FS-boundary materialization workflows (`503; code=NODIR_LOCKED`) per `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`.

## Browse / Files / Download Contract

### URL and Routing Semantics
- Browse paths (`/browse/...`), download paths (`/download/...`), and files API paths (`/files/...`) MUST accept archive boundaries in the `subpath` parameter.
- The archive boundary is detected by path segment suffix `.nodir`.
  - Archive boundaries MUST only be recognized for the first `subpath` segment (top-level under the WD).
  - Services MUST restrict archive boundaries to the known NoDir roots:
    - `landuse.nodir`
    - `soils.nodir`
    - `climate.nodir`
    - `watershed.nodir`
  - Any other `*.nodir` file MUST be treated as a regular file (downloadable, not enterable).
  - Generic `.zip` files MUST be treated as regular files (downloadable) and MUST NOT be interpreted as “enterable” directories.
    - Rationale: avoid `.zip` recursion, and keep user-provided `.zip` uploads (for example ag fields plant DB zips) on a separate, stricter rule set.

Examples:
- Browse archive “folder”:
  - `/weppcloud/runs/<runid>/<config>/browse/watershed.nodir/`
- Browse file inside archive:
  - `/weppcloud/runs/<runid>/<config>/browse/watershed.nodir/hillslopes/h001.slp`
- Download file inside archive:
  - `/weppcloud/runs/<runid>/<config>/download/watershed.nodir/hillslopes/h001.slp`
- Download the archive file itself:
  - `/weppcloud/runs/<runid>/<config>/download/watershed.nodir`

### UI Behavior (Browse HTML)
- In a directory listing, a recognized NoDir archive file (e.g., `watershed.nodir`) SHOULD be rendered as a directory entry (clickable with trailing `/`) so users can “enter” it.
- Mixed state (`<root>/` + `<root>.nodir` exist):
  - Non-admin browse listings MUST hide both representations for that root (neither `<root>/` nor `<root>.nodir` is shown).
    - Direct navigation to either MUST return `409 Conflict` (`code=NODIR_MIXED_STATE`).
  - Admin browse MUST expose two explicit views:
    - Directory view: `/browse/<root>/...`
    - Archive view: `/browse/<root>/nodir/...` (read-only; maps to `WD/<root>.nodir`)
      - The path segment `nodir` is reserved for this view under NoDir roots.
  - In mixed state, `/browse/<root>.nodir/...` SHOULD redirect to `/browse/<root>/nodir/...` for admins.
  - Below pagination controls, browse HTML MUST render a mixed-state warning block listing affected roots.
- Browse ordering: NoDir archive roots (`*.nodir`) MUST sort with directories (ahead of regular files) in directory listings.

### JSON Behavior (`/files/`)
- `/files/...` responses MUST treat archive-backed paths as directories/files with the same shape as directory-backed paths.
- The API MUST NOT require clients to understand zip internals; the zip boundary is encoded in the URL path only.
- Mixed-state targets MUST return `409 Conflict` (`code=NODIR_MIXED_STATE`) (observability; no silent precedence).
- In mixed state, admin-authenticated `GET /files/` (root listing) MUST expose both representations (`<root>/` and `<root>.nodir`) for debug observability.
  - This exception applies only to root listing visibility.
  - Mixed-state target navigation under `/files/<root>/...` and `/files/<root>.nodir/...` remains `409 Conflict` (`code=NODIR_MIXED_STATE`) for all roles.

### aria2c.spec
- `aria2c.spec` MUST list `.nodir` archives as files (do not expand inner entries).
- Manifest URLs MUST be site-prefix aware and host-agnostic (no hardcoded `wepp.cloud` assumptions).

### Mixed-State Download Semantics
- If a NoDir root is in mixed state, raw download of `WD/<root>.nodir` MUST be admin-only.
  - Non-admin MUST receive `409 Conflict` (`code=NODIR_MIXED_STATE`).

### Invalid `.nodir` Archives
- For allowlisted NoDir roots, treating `WD/<root>.nodir` as an archive requires validating it as a readable zip with normalized/safe entry names.
- If validation fails:
  - Archive-as-directory operations MUST return `500` (`code=NODIR_INVALID_ARCHIVE`).
  - Raw download of `<root>.nodir` bytes:
    - Admin MAY stream raw bytes for forensics.
    - Non-admin MUST return `500` (`code=NODIR_INVALID_ARCHIVE`).

## Archive Format and Compression Strategy
- `.nodir` is the on-disk extension used for NoDir archives to differentiate them from generic/user `.zip` files.
  - `.nodir` files are zip containers (PKZIP) and may be inspected by renaming to `.zip` for debugging.
- Zip is the baseline container because it has a central directory (fast name->offset indexing) and is easy to stream without extraction.
- Allowed compression methods: `STORE` and `DEFLATE` only (cross-stack compatibility).
- Compression MUST be selectable per-entry.
  - Avoid recompressing already-compressed formats (most rasters) unless there is a measured win.

## Parquet Sidecars (WD-Level, Canonical)
Parquet is treated differently from “many-small-files” trees:
- For allowlisted NoDir roots, `.parquet` files are canonical WD-level sidecars and MUST NOT be stored inside `WD/<root>.nodir`.
  - Rationale: Parquet readers (DuckDB/Arrow) rely on random-access reads; zip entries (especially deflated) are not efficiently seekable, and “extract-to-temp” creates cache/sync churn.
- Sidecar mapping (logical → physical):
  - `landuse/landuse.parquet` → `WD/landuse.parquet`
  - `soils/soils.parquet` → `WD/soils.parquet`
  - `climate/<name>.parquet` → `WD/climate.<name>.parquet` (example: `climate/wepp_cli.parquet` → `WD/climate.wepp_cli.parquet`)
  - `watershed/<name>.parquet` → `WD/watershed.<name>.parquet` (example: `watershed/hillslopes.parquet` → `WD/watershed.hillslopes.parquet`)
- Sidecars are optional; absence is a normal “dataset missing” case (NOT `NODIR_INVALID_ARCHIVE`).
- Resolution precedence for logical `*.parquet` paths under NoDir roots:
  - Prefer the WD-level sidecar if present.
  - If Dir form and sidecar is absent, implementations MAY fall back to the legacy in-root path for compatibility (example: `WD/landuse/landuse.parquet`).
  - If Archive form and sidecar is absent, treat as missing (404 / dataset-not-found at the caller surface); MUST NOT fall back to an archive entry for that logical path.
- Freeze/migration tooling MUST move/rename any in-root parquet to its WD-level sidecar path before archiving and MUST exclude `.parquet` entries from `WD/<root>.nodir`.

## Migration / Archival Rules
- Migration tooling that converts `WD/<root>/` -> `WD/<root>.nodir` MUST:
  - Acquire the NoDir maintenance lock for `<root>` (and fail fast if not acquired).
  - Refuse to run if the root is actively being written (bulk migrators SHOULD require `WD/READONLY`).
  - Build `WD/<root>.nodir.tmp` then atomically rename to `WD/<root>.nodir`.
  - Validate that every archive entry path is safe and normalized.
  - Dereference symlinked files and archive their target bytes as regular entries.
    - Reject symlinks whose targets are missing or not regular files.
    - Validate resolved targets against an explicit allowlist of roots (default deny) to avoid copying arbitrary host files into run artifacts.
    - Record resolved source paths in the migration audit log.
  - Produce an audit record (what was converted, sizes, counts, any skipped files).
  - Only delete the original directory after successful archive verification.

## Security Requirements
- Treat archive entry paths as untrusted input even for “server-generated” archives:
  - Enforce strict normalization and rejection rules on every request.
- Do not extract archives as part of serving browse/files/download.
- When extraction is unavoidable (thaw/materialize workflows):
  - Implement zip-slip defenses (reject absolute paths, `..`, and weird separators).
  - Enforce bounded output (max entries, max total bytes) to reduce DoS risk.
    - Limits MUST be configurable; initial defaults SHOULD be generous.
  - Do not create symlinks from archive metadata.
  - Materialization cache layout, locks, and limits are specified in `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`.

## Gotchas / Regression Traps
- **mtime precision**: zip timestamps may be lower precision than filesystem `st_mtime_ns`; ensure UI/tests tolerate this.
- **Large directories**: current browse listing does `stat()`/`readdir()` and per-directory child counts; archive listing must avoid per-entry filesystem stats.
- **Mixed state** (`<root>/` + `<root>.nodir`): define deterministic precedence to avoid double trees and confusing UI.
- **Symlinks**: existing browse code supports symlinks (with root checks). NoDir roots should avoid symlinks to keep archive semantics simple.
- **Omni child runs**: `_pups/omni/scenarios/*` and `_pups/omni/contrasts/*` share parent inputs via symlinks; when the parent uses `climate.nodir`/`watershed.nodir`, child runs must link the `.nodir` files (not `climate/`/`watershed/`).
- **Ancillary browse actions**: `/gdalinfo/`, `/dtale/`, `/diff/`, and “annotated” views are implemented assuming filesystem paths; decide per-endpoint behavior for archive entries (disable, materialize, or stream).
- **DoS surface**: listing huge archives and streaming large entries can become CPU-bound; add timeouts/limits and consider caching of central-directory metadata.
