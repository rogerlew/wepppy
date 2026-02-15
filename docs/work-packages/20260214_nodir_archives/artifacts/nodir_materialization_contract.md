# NoDir Materialization Contract (Step 2)

> Normative contract for `materialize(file)` / cache semantics used by FS-boundary surfaces (dtale, gdalinfo, exports) when NoDir roots are archive-backed (`*.nodir`).
>
> Note: Query engine Parquet under NoDir roots is a WD-level sidecar (no `.nodir` extraction) per `docs/schemas/nodir-contract-spec.md`.
>
> See:
> - `docs/schemas/nodir-contract-spec.md`
> - `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`
> - `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`

## 1) Terms
- `native`: no extraction to disk; list/stat/read via filesystem (Dir form) or zip central-dir + streamed entry reads (Archive form).
- `materialize(file)`: extract one archive entry (plus required sidecars) to an internal on-disk path and return a real filesystem path to hand to a tool/library.
- `materialize(root-subset)`: extract a bounded set of entries into a temporary directory preserving relative paths; used by exports that require multiple real files.
- `materialize(root)`: thaw entire root to `WD/<root>/` (see `docs/schemas/nodir-contract-spec.md`).
- `archive fingerprint`: `{mtime_ns, size_bytes}` from `stat(WD/<root>.nodir)`.
- `entry fingerprint`: `(inner_path, crc32, file_size, compress_size, method)` from zip central directory.

## 2) Global Rules (Materialization-Relevant)
- Materialization is **prohibited** for `/browse`, `/files`, `/download` (must be archive-native streaming).
- Materialization is **required** for dtale/gdalinfo/exports when the requested object is an archive entry (per behavior matrix).
- Mixed state (`WD/<root>/` and `WD/<root>.nodir` both exist): outside `/browse` MUST fail fast with `409; code=NODIR_MIXED_STATE` before any materialization.
- Invalid allowlisted `.nodir`: archive-as-directory operations and materialization MUST return `500; code=NODIR_INVALID_ARCHIVE`.
- Materialization lock contention or “root is transitioning” MUST return `503; code=NODIR_LOCKED`.
- Materialization limits MUST return `413; code=NODIR_LIMIT_EXCEEDED`.

## 3) Cache Layout (On Disk)

### 3.1 Cache Root (Per Run)
- `WD/.nodir/` is the internal NoDir working directory (hidden from browse due to leading `.`, and MUST NOT be addressable via browse/files/download path resolution).
- Materialization cache root: `WD/.nodir/cache/`.

### 3.2 Cache Keying
- `archive_fp := "<mtime_ns>-<size_bytes>"`.
- `entry_id := sha256(inner_path).hexdigest()[0:32]`.

### 3.3 materialize(file) Paths
- Entry directory: `WD/.nodir/cache/<root>/<archive_fp>/<entry_id>/`
- Extracted primary path: `WD/.nodir/cache/<root>/<archive_fp>/<entry_id>/<basename>`
- Metadata sidecar: `WD/.nodir/cache/<root>/<archive_fp>/<entry_id>/meta.json`

Notes:
- `<basename>` MUST be `posixpath.basename(inner_path)` and MUST NOT contain path separators.
- Implementations MUST NOT embed raw `inner_path` segments into cache directories (hash only) to avoid path traversal and path-length blowups.

### 3.4 materialize(root-subset) Paths
- Temporary extraction directory (unique per request): `WD/.nodir/tmp/<root>/<archive_fp>/<uuid4>/`
- `materialize(root-subset)` MUST preserve relative paths under that temp dir (safe-joined).
- Implementations MUST delete the temp dir on success and failure (best-effort).

## 4) materialize(file) Contract (Algorithm)

### 4.1 Preconditions (Fail Fast)
- Representation MUST already be resolved to Archive form by the caller.
- If `WD/<root>/` exists: do not materialize (caller should use native FS paths).
- If root is in `state in {"thawing","freezing"}` (from `WD/.nodir/<root>.json` when present): return `503; NODIR_LOCKED`.

### 4.2 Cache Hit Rules (Idempotency)
Treat as cache hit and return the extracted path if all are true:
- `meta.json` exists and parses.
- `meta.archive_fingerprint == stat(WD/<root>.nodir)` and `meta.inner_path == inner_path`.
- `meta.zip` matches current central-dir entry fingerprint (crc32, sizes, method).
- All required extracted files exist and sizes match `meta.extracted`.

If any mismatch:
- Treat as cache miss.
- Remove the entry directory (best-effort) before re-extracting.

### 4.3 Locking (Per Entry)
- Before extracting on cache miss, acquire a distributed lock with key `nodb-lock:<runid>:nodir-materialize/<root>/<entry_id>`; if not acquired immediately (fail-fast), return `503; NODIR_LOCKED`.
- Under the lock, MUST re-check cache-hit to avoid duplicate work.

### 4.4 Extraction and Atomicity
Extraction MUST be crash-safe and never yield partial files:
- Create entry directory (parents first).
- Write each extracted file to a temp path under the same entry directory (pattern: `<name>.tmp.<pid>.<rand>`).
- Stream the zip entry bytes to the temp path while enforcing limits.
- Verify extracted byte count matches expected `file_size` (central dir).
- Verify CRC32 when available (zip central dir).
- Install via `os.replace(tmp_path, final_path)`.
- Write `meta.json` via temp + `os.replace()`.

### 4.5 Sidecar Groups (Required)
`materialize(file)` MAY need to extract multiple files so downstream tools see a coherent dataset.

Sidecar rules:
- `.shp` request: MUST also extract these same-directory sidecars when present: `.shx`, `.dbf`, `.prj`, `.cpg`, `.qix`, `.sbn`, `.sbx`, `.fix`, `.shp.xml`; missing `.shx` or `.dbf` MUST be treated as `500; NODIR_INVALID_ARCHIVE`.
- `.tif`/`.tiff` request: SHOULD also extract these same-directory sidecars when present: `.ovr`, `.aux.xml`, `.tif.aux.xml`, `.tfw`.

## 5) Limits (Defaults Are Initial and Configurable)

Materialization MUST enforce bounded output (zip-bomb and runaway extraction defenses).

Defaults (initial; tune later):
| Limit | Default | Error |
|---|---:|---|
| Max uncompressed bytes per extracted file | 16 GiB | `413; NODIR_LIMIT_EXCEEDED` |
| Max total uncompressed bytes per `materialize(file)` request (including sidecars) | 20 GiB | `413; NODIR_LIMIT_EXCEEDED` |
| Max files extracted per `materialize(file)` request | 32 | `413; NODIR_LIMIT_EXCEEDED` |
| Max uncompressed bytes per `materialize(root-subset)` request | 40 GiB | `413; NODIR_LIMIT_EXCEEDED` |
| Max files extracted per `materialize(root-subset)` request | 2048 | `413; NODIR_LIMIT_EXCEEDED` |

Compression-ratio guard (optional but recommended):
- If `file_size >= 64 MiB` and `compress_size > 0` and `(file_size / compress_size) > 200`: reject as `413; NODIR_LIMIT_EXCEEDED`.

## 6) Validation and Security Requirements

### 6.1 Path and Entry Validation
- Inner path normalization MUST reject: any `..` segment, absolute paths, and null bytes.
- Zip entries MUST be treated as untrusted input: reject symlink entries and non-regular file types; reject names that normalize outside the archive root.

### 6.2 Zip-Slip / Traversal Defense (Extraction)
- Extraction destinations MUST be computed from the cache layout only (no raw `inner_path` joins).
- When writing temp files, implementations SHOULD use `O_NOFOLLOW` / equivalent to avoid symlink-clobber attacks.

### 6.3 Permissions
- Do not preserve zip permission bits.
- Extracted files SHOULD be mode `0644` (or stricter) and directories `0755` (or stricter), subject to process umask.

## 7) Cleanup and Invalidation
- Cache directories are disposable: it MUST be safe to delete `WD/.nodir/cache/` and `WD/.nodir/tmp/` at any time (best-effort); code MUST NOT treat caches as source-of-truth.
- Fingerprint invalidation: a new `archive_fp` MUST create a new cache subtree; old `archive_fp` subtrees SHOULD be pruned opportunistically.

Pruning defaults (initial; tune later):
- Keep at most 2 `archive_fp` directories per `<root>`.
- Remove `WD/.nodir/tmp/` entries older than 24 hours.

## 8) Observability (Required Fields)
On every materialization attempt, logs SHOULD include:
- `runid`, `<root>`, `inner_path`
- cache outcome: `hit|miss|rebuild`
- archive fingerprint: `mtime_ns`, `size_bytes`
- zip method, compressed size, uncompressed size
- extracted bytes, wall time
- any limit rejections (`NODIR_LIMIT_EXCEEDED`) and lock contention (`NODIR_LOCKED`)

## 9) Query Engine (Parquet)
- Query engine MUST NOT rely on extracting Parquet from `.nodir`.
- Parquet datasets under allowlisted NoDir roots are WD-level sidecars per `docs/schemas/nodir-contract-spec.md` and should be consumed via native filesystem paths.
