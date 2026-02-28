# NoDir Shared Interface Spec (Python)
> **Archived / Deprecated (Historical, 2026-02-27):** This NoDir specification is retired from active contract flow after the directory-only reversal. It is retained only for historical/audit reference.


> Normative spec for a shared Python implementation of the NoDir interface so browse/files/download/query-engine/controllers do not each re-implement “dir vs `.nodir`” rules.
>
> See:
> - `docs/schemas/nodir-contract-spec.md`
> - `docs/schemas/nodir-thaw-freeze-contract.md`
> - `docs/schemas/nodir-touchpoints-reference.md`
> - `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`
> - `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`

## 0) Goals / Non-Goals
Goals:
- One shared, unit-testable implementation for:
  - representation discovery (dir vs archive, never persisted),
  - path parsing (logical vs archive-boundary vs admin-browse view),
  - archive-native list/stat/read (no extract-to-disk),
  - materialization (dtale/gdalinfo/exports bridge) and Parquet sidecar resolution.
- Enforce the locked error contract (`409/500/503/413` + codes) deterministically.

Non-goals:
- FUSE / OS-level virtual filesystems.
- Generic enterable `.zip` support (only allowlisted `.nodir` roots).
- “Silent precedence” in mixed state for public surfaces (observability first).

## 1) Terms (Interface-Level)
- NoDir roots: `landuse`, `soils`, `climate`, `watershed`.
- Dir form: `WD/<root>/` exists and `WD/<root>.nodir` does not.
- Archive form: `WD/<root>.nodir` exists and `WD/<root>/` does not (and archive validates).
- Mixed state: both exist.
- Invalid archive: allowlisted `WD/<root>.nodir` exists but fails zip validation/path normalization.
- Parquet sidecar: WD-level `.parquet` file that is logically under a NoDir root but is stored outside the `.nodir` archive (see `docs/schemas/nodir-contract-spec.md`).
  - Mapping is deterministic (examples): `landuse/landuse.parquet` → `WD/landuse.parquet`, `watershed/hillslopes.parquet` → `WD/watershed.hillslopes.parquet`, `climate/wepp_cli.parquet` → `WD/climate.wepp_cli.parquet`.

Views:
- `effective`: normal public behavior (enforces mixed-state/invalid errors).
- `dir`: force directory view (admin browse or maintenance workflows).
- `archive`: force archive view (admin browse).

## 2) Package Layout (Proposed)
New package: `wepppy/nodir/`
- `wepppy/nodir/__init__.py` exports the public surface (no Starlette/Flask imports).
- `wepppy/nodir/errors.py` typed errors with `{status, code}`.
- `wepppy/nodir/paths.py` path normalization + boundary parsing.
- `wepppy/nodir/fs.py` resolver + list/stat/open_read.
- `wepppy/nodir/materialize.py` implements Step 2 cache/lock/limits.

## 3) Canonical Errors (Must Match Docs)
Every error raised by this package MUST provide:
- `http_status: int`
- `code: str` (one of below)
- `message: str` (short)

Codes:
- `NODIR_MIXED_STATE` → `409`
- `NODIR_INVALID_ARCHIVE` → `500`
- `NODIR_LOCKED` → `503`
- `NODIR_LIMIT_EXCEEDED` → `413`

JSON payload shaping is owned by the caller (browse/files/rq/query-engine), but the code+status MUST remain stable.

## 4) Public API (Normative)

### 4.1 Types
`NoDirRoot = Literal["landuse","soils","climate","watershed"]`

`NoDirView = Literal["effective","dir","archive"]`

`NoDirForm = Literal["dir","archive"]`

`@dataclass(frozen=True)`
`ResolvedNoDirPath`:
- `wd: str` (abs)
- `root: NoDirRoot`
- `inner_path: str` (posix rel, `""` means root)
- `form: NoDirForm`
- `dir_path: str` (abs, `WD/<root>`)
- `archive_path: str` (abs, `WD/<root>.nodir`)
- `archive_fp: tuple[int,int] | None` (`(mtime_ns,size_bytes)` when archive exists)

`@dataclass(frozen=True)`
`NoDirDirEntry`:
- `name: str`
- `is_dir: bool`
- `size_bytes: int | None` (files only; archive-derived is best-effort)
- `mtime_ns: int | None` (best-effort; zip timestamps may be coarse)

### 4.2 Path Parsing / Normalization
`normalize_relpath(raw: str) -> str`
- Convert `\\` to `/`.
- Strip leading `/`.
- Reject `\x00`, absolute paths, and any `..` segment.
- Return `"."` for empty.

`parse_external_subpath(rel: str, *, allow_admin_alias: bool) -> tuple[str, NoDirView]`
- Input: request `subpath` relative to WD as seen by browse/files/download/dtale/gdalinfo.
- Output:
  - normalized relpath (no leading `/`, posix separators),
  - requested view (`effective|archive|dir`) inferred from explicit syntax.

Rules:
- Archive-boundary syntax (any role): `<root>.nodir/<inner>` requests `view="archive"` if `<root>` allowlisted.
- Admin browse alias syntax (admin only): `<root>/nodir/<inner>` requests `view="archive"`.
- Otherwise: `view="effective"` and the normalized relpath remains in the logical namespace (`<root>/...`).

### 4.3 Resolver
`resolve(wd: str, rel: str, *, view: NoDirView = "effective") -> ResolvedNoDirPath | None`
- Returns `None` only when `rel` is not under an allowlisted NoDir root (caller should treat as normal filesystem path).
- MUST implement representation discovery via `exists()` only (no NoDb serialization).
- MUST enforce:
  - Mixed state in `view="effective"`: raise `409 NODIR_MIXED_STATE`.
  - Invalid allowlisted archive in `view in {"effective","archive"}`: raise `500 NODIR_INVALID_ARCHIVE`.
  - `view="dir"` requires `WD/<root>/` exists else behave like normal “missing path” (`None` or a typed not-found error owned by the caller).
  - `view="archive"` requires `WD/<root>.nodir` exists.

Parquet sidecar rule:
- For logical `*.parquet` paths under NoDir roots, resolution MUST prefer the WD-level sidecar mapping (and MUST NOT fall back to a zip entry in Archive form).

### 4.4 Directory-Like Operations
`listdir(target: ResolvedNoDirPath) -> list[NoDirDirEntry]`
- If `target.inner_path` names a file: caller error (not-a-directory, owned by caller).
- Archive form:
  - MUST be derived from zip central directory; MUST NOT extract to disk.
  - Directory membership is derived from entry-name prefixes.
- Parquet sidecars MUST NOT be synthesized into directory listings for browse/files.
  - Browse is an observability-first file browser: truth-on-disk is the listing source of truth.
  - Sidecar parquets remain visible as WD-level files (example: `WD/landuse.parquet`), not as “virtual” `WD/landuse/landuse.parquet` entries.

`stat(target: ResolvedNoDirPath) -> NoDirDirEntry`
- Archive form:
  - For files: derive from central directory entry metadata.
  - For “virtual directories” (prefix-derived): `size_bytes=None`, `mtime_ns=None` is acceptable.
- For Parquet sidecars, stat/open_read MUST target the sidecar filesystem file when present (even though directory listings will not imply membership under `WD/<root>/`).

`open_read(target: ResolvedNoDirPath) -> BinaryIO`
- Archive form: stream zip entry bytes (no extract-to-disk).
- SHOULD enforce a maximum uncompressed size check using central-dir `file_size` before streaming:
  - reject with `413 NODIR_LIMIT_EXCEEDED` when configured max is exceeded.
- For Parquet sidecars, reads MUST open the sidecar filesystem file when present (no zip streaming).

### 4.5 FS-Boundary Bridge
`materialize_file(wd: str, rel: str, *, purpose: str) -> str`
- Purpose examples: `"dtale"|"gdalinfo"|"export"`.
- MUST implement the Step 2 contract (`nodir_materialization_contract.md`):
  - cache layout under `WD/.nodir/cache/`,
  - per-entry distributed locks (`nodb-lock:<runid>:nodir-materialize/<root>/<entry_id>`),
  - sidecar extraction rules,
  - limits and explicit errors.

Note: materialized paths are internal (`WD/.nodir/...`) and MUST NOT be exposed as user-addressable paths or URLs.

## 5) Surface Integration Rules (Call-Site Contract)

### 5.1 Browse / Files / Download
- `/browse`, `/files`, `/download` MUST use `resolve()+listdir/stat/open_read` for NoDir roots.
- They MUST NOT call `materialize_*` for these surfaces (matrix).
- Mixed state (non-admin): hide both in listings; direct nav returns `409 NODIR_MIXED_STATE`.
- Mixed state (admin browse): caller selects view explicitly:
  - directory view: `view="dir"`
  - archive view: `view="archive"` via `<root>/nodir/...` or `<root>.nodir/...` alias
- Mixed state (admin `/files/` root listing): expose both `<root>/` and `<root>.nodir` for debug observability.
  - This visibility exception is limited to `GET /files/` root listing.
  - Mixed-state target navigation under `/files/<root>/...` and `/files/<root>.nodir/...` remains `409 NODIR_MIXED_STATE`.

### 5.2 D-Tale / GDALInfo / Exports
- These endpoints MUST:
  - resolve the request path in the logical namespace, then
  - call `materialize_file(..., purpose=...)` when the resolved form is archive-backed.
- They MUST NOT treat “archive form” as “path does not exist”.
- They MUST enforce mixed-state/invalid semantics per the behavior matrix.

Security note:
- browse-service hidden-path forbids user-subpaths containing `.nodir/` (cache dir) and MUST remain enforced.
- FS-boundary endpoints MUST validate the user-requested logical path, not the internal cache path.

### 5.3 Query Engine
- Activation: catalog natively (no full extraction); resolve logical `*.parquet` dataset paths to WD-level sidecars (native filesystem paths).
- Queries: MUST NOT extract Parquet from `.nodir` or per-query; Parquet access is via sidecars or is “dataset missing” when absent.

### 5.4 Mutations / Maintenance
- Mutations targeting NoDir roots (controllers, RQ jobs, migrations) follow the thaw/modify/freeze protocol.
- Maintenance code MAY use `view="dir"` while the root is thawed and directory is authoritative.
- Public APIs MUST NOT silently pick a side in mixed state; that is limited to maintenance workflows.

## 6) Acceptance (Doc-Level)
- Public API above is sufficient to implement browse/files/download + dtale/gdalinfo + query-engine without per-surface “dir vs zip” branching.
- Mixed-state behavior can only be bypassed by an explicit caller choice (`view="dir"` or `view="archive"`).
- Materialization contract is referenced, not redefined.
