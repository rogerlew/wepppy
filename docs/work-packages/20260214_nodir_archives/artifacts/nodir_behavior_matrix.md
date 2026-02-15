# NoDir Behavior Matrix (Step 1)

> Normative matrix for how each surface behaves when `landuse/`, `soils/`, `climate/`, `watershed/` are directory-backed vs archive-backed (`*.nodir`).
>
> See:
> - `docs/schemas/nodir-contract-spec.md`
> - `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`

## 1) Header + Terms
- **Dir form**: `WD/<root>/` exists and `WD/<root>.nodir` does not.
- **Archive form**: `WD/<root>.nodir` exists and `WD/<root>/` does not (and is a valid zip).
- **Mixed state**: both exist.
- **Invalid archive**: allowlisted `WD/<root>.nodir` exists but fails zip validation / path normalization.

Modes:
- `native`: no extraction to disk; list/stat/read via FS (Dir form) or zip central-dir + streamed entry reads (Archive form).
- `materialize(file)`: extract a single entry to an on-disk cache/temp path, then hand a real path to a tool/library.
- `materialize(root)`: thaw entire root to a directory (temp or in-place), then operate; may be followed by freeze.
- `unsupported`: explicit error; no silent fallback.

Canonical error codes (JSON where applicable; echoed in HTML/plaintext otherwise):
- `NODIR_MIXED_STATE` → `409`
- `NODIR_INVALID_ARCHIVE` → `500`
- `NODIR_LOCKED` → `503` (maintenance/materialize lock contention; fail-fast)
- `NODIR_LIMIT_EXCEEDED` → `413` (materialize limits hit)

## 2) Global Rules (Matrix-Relevant)
- Enterable archive allowlist (top-level only): `landuse.nodir`, `soils.nodir`, `climate.nodir`, `watershed.nodir`.
- No nested archive boundaries. `.zip` is never enterable.
- **Mixed state**:
  - Non-admin `/browse`: hide both; direct nav is `409; NODIR_MIXED_STATE`.
  - Admin `/browse`: dual view (`/browse/<root>/...` and `/browse/<root>/nodir/...`).
  - Outside `/browse`: always `409; NODIR_MIXED_STATE` for admin and non-admin, except admin raw download of `<root>.nodir` bytes.
- **Invalid allowlisted `.nodir`**:
  - Archive-as-directory ops: `500; NODIR_INVALID_ARCHIVE` (all roles).
  - Raw download of `<root>.nodir`:
    - admin `200` (stream bytes for forensics),
    - non-admin `500; NODIR_INVALID_ARCHIVE`.

## 3) Matrices
Cell format: `<mode>; <status>; <code>` where `<code>` is `—` on success.

### A) Browse Microservice (HTML + JSON + download-ish)

| Surface | Dir form | Archive form | Mixed state | Invalid archive |
|---|---|---|---|---|
| `GET /weppcloud/runs/<runid>/<config>/browse/<dir>/` (HTML listing) | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/browse/<file>` (HTML preview/render) | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/files/<dir>?…` (JSON listing) | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/files/<path>?meta=1` (JSON meta/stat) | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/download/<path>` (raw download) | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/download/<root>.nodir/<inner>` (download entry) | `native; 404; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/aria2c.spec` (spec generation) | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 200; —` |
| `GET /weppcloud/runs/<runid>/<config>/dtale/<path>` (redirect) | `native; 303; —` | `materialize(file); 303; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/gdalinfo/<path>` (JSON) | `native; 200; —` | `materialize(file); 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| `GET /weppcloud/runs/<runid>/<config>/diff/<path>?diff=<runid>` (HTML bootstrap; Flask) | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `native; 500; NODIR_INVALID_ARCHIVE` |

Admin deltas (mixed state, `/browse` only):
- Directory view: `GET /weppcloud/runs/<runid>/<config>/browse/<root>/...` → `native; 200; —`
- Archive view: `GET /weppcloud/runs/<runid>/<config>/browse/<root>/nodir/...` → `native; 200; —`
- Alias: `GET /weppcloud/runs/<runid>/<config>/browse/<root>.nodir/...` → `redirect (302/307); —; —` to `/browse/<root>/nodir/...`
- Raw `<root>.nodir` download in mixed state:
  - admin: `native; 200; —`
  - non-admin: `unsupported; 409; NODIR_MIXED_STATE`

### B) Query Engine

| Surface | Dir form | Archive form | Mixed state | Invalid archive |
|---|---|---|---|---|
| Activation: `GET|POST /query-engine/runs/<runid>/activate` (HTTP) / `activate_query_engine(wd)` | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| Query execution: `POST /query-engine/runs/<runid>/query` (HTTP) / `run_query(...)` | `native; 200; —` | `native; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |

### C) Backend Tools / Mutations / Maintenance

| Surface | Dir form | Archive form | Mixed state | Invalid archive |
|---|---|---|---|---|
| RQ-engine landuse: `POST /rq-engine/api/runs/<runid>/<config>/build-landuse` | `native; 200; —` | `materialize(root)+freeze; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| RQ-engine soils: `POST /rq-engine/api/runs/<runid>/<config>/build-soils` | `native; 200; —` | `materialize(root)+freeze; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| RQ-engine climate: `POST /rq-engine/api/runs/<runid>/<config>/build-climate` | `native; 200; —` | `materialize(root)+freeze; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| RQ-engine watershed (group): `POST /rq-engine/api/runs/<runid>/<config>/*` (`/fetch-dem-and-build-channels`, `/build-subcatchments-and-abstract-watershed`, `/set-outlet`, …) | `native; 200; —` | `materialize(root)+freeze; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| RQ-engine upload CLI: `POST /rq-engine/api/runs/<runid>/<config>/tasks/upload-cli/` | `native; 200; —` | `materialize(root)+freeze; 200; —` | `unsupported; 409; NODIR_MIXED_STATE` | `unsupported; 500; NODIR_INVALID_ARCHIVE` |
| Mods: treatments landuse `.man` writes; omni clone/copy (python) | `native; n/a; —` | `materialize(root)+freeze; n/a; —` | `unsupported; n/a; NODIR_MIXED_STATE` | `unsupported; n/a; NODIR_INVALID_ARCHIVE` |
| Exports: `export_winwepp`, `gpkg_export`, `prep_details` (python; rq-engine export endpoints call these) | `native; n/a; —` | `materialize(file|root-subset); n/a; —` | `unsupported; n/a; NODIR_MIXED_STATE` | `unsupported; n/a; NODIR_INVALID_ARCHIVE` |
| Migrations: `wepppy/tools/migrations/*` touching these roots (python/CLI) | `native; n/a; —` | `materialize(root)+freeze; n/a; —` | `unsupported; n/a; NODIR_MIXED_STATE` | `unsupported; n/a; NODIR_INVALID_ARCHIVE` |

## 4) Explicit Notes
- **Materialization is prohibited** for `/browse`, `/files`, `/download` (must be archive-native streaming).
- **Materialization is required** for dtale/gdalinfo/exports when the requested object is an archive entry. Parquet under NoDir roots is a WD-level sidecar and remains `native`.
  - Materialization failures MUST be explicit:
    - lock contention → `503; NODIR_LOCKED`
    - limits exceeded → `413; NODIR_LIMIT_EXCEEDED`
  - Step 2 (materialization contract) defines cache paths, fingerprinting, TTL/cleanup, and limits: `docs/work-packages/20260214_nodir_archives/artifacts/nodir_materialization_contract.md`.
- Browse HTML mixed-state warning block: render **below pagination controls** and list affected roots.
