# NoDir Canonical Root Projection Contract (Step 2A Revision)

> Normative contract for archive-backed roots projected at canonical in-run paths (`WD/<root>`).
>
> Canonical policy: path-heavy consumers use projected mount sessions, not ad hoc per-file extraction.
>
> See:
> - `docs/schemas/nodir-contract-spec.md`
> - `docs/schemas/nodir-thaw-freeze-contract.md`
> - `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`

## 1) Objective
- Keep `WD/<root>.nodir` as authoritative persisted data.
- Present `WD/<root>` as the canonical runtime filesystem view so legacy path-based code can read with minimal touchpoint changes.
- Replace most `materialize(file)` usage with run-scoped mount sessions.

## 2) Terms
- `projected root`: mounted view at `WD/<root>`.
- `read session`: read-only projection over archive content.
- `mutation session`: writable projection where writes land in an upper layer and are committed to archive only at explicit finalize.
- `archive fingerprint`: `{mtime_ns, size_bytes}` from `stat(WD/<root>.nodir)`.
- `projection key`: `(runid, root, archive_fingerprint, mode)`.

## 3) Canonical Policy
- For path-based consumers (`open`, `glob`, `walk`, legacy helpers), projection is canonical.
- `materialize(file)` is compatibility fallback only and must not be default for high-fanout reads.
- `/browse`, `/files`, `/download` remain archive-native streaming and do not depend on projection sessions.
- `landuse`, `soils`, `watershed`, `climate` all follow the same projection contract.

## 4) Projection Modes

### 4.1 Read Session
- Backing: archive-mounted lower layer, read-only.
- Writes to `WD/<root>` are disallowed.
- Intended for WEPP prep/read flows and other read-only stages.

### 4.2 Mutation Session
- Backing: read-only archive lower layer plus writable upper/work layers.
- Runtime writes go to upper layer only.
- Commit path explicitly converts upper-layer results to refreshed `WD/<root>.nodir` atomically.
- Abort path discards upper/work layers without archive changes.

Note:
- Mutation sessions replace ad hoc thawed-dir persistence while preserving explicit mutation boundaries and lock semantics.
- Archive writes are never direct-in-place writes to zip content.

## 5) Required Utility API
- `acquire_root_projection(wd, root, *, mode, purpose) -> ProjectionHandle`
- `release_root_projection(handle) -> None`
- `with_root_projection(wd, root, *, mode, purpose)` context manager
- `commit_mutation_projection(handle) -> None` (mode=`mutate` only)
- `abort_mutation_projection(handle) -> None` (mode=`mutate` only)

`ProjectionHandle` must include:
- `wd`, `root`, `mode`, `archive_fingerprint`
- `mount_path` (canonical `WD/<root>`)
- `backend` (for example `fuse+overlay`)
- `token`, `acquired_at`

## 6) Locking and Idempotency
- Acquire must lock on `nodb-lock:<runid>:nodir-project/<root>/<archive_fp>/<mode>`.
- Acquire is fail-fast; contention returns `503; code=NODIR_LOCKED`.
- Existing live projection with identical key must be reused with refcount increment.
- Refcount reaching zero must unmount and clean stale state for that key.

## 7) Mixed-State Semantics (Revised)
- Legacy mixed state (`real dir + .nodir`) is replaced by projection-aware checks:
  - `WD/<root>.nodir` exists and `WD/<root>` is a managed mountpoint: valid.
  - `WD/<root>.nodir` exists and `WD/<root>` is a plain directory with unmanaged files: `409; code=NODIR_MIXED_STATE`.
- Recovery policy remains archive-authoritative unless an explicit mutation commit is in progress.

## 8) Error Contract
- Invalid archive or projection backend failure: `500; code=NODIR_INVALID_ARCHIVE`.
- Lock contention or transitioning projection state: `503; code=NODIR_LOCKED`.
- Invalid mixed unmanaged directory state: `409; code=NODIR_MIXED_STATE`.
- Limit/resource guard violations: `413; code=NODIR_LIMIT_EXCEEDED`.

## 9) On-Disk Runtime Layout
- Internal control root: `WD/.nodir/`
- Projection metadata: `WD/.nodir/projections/<root>/<archive_fp>/<mode>.json`
- Lower mounts: `WD/.nodir/lower/<root>/<archive_fp>/`
- Upper layers (mutation mode): `WD/.nodir/upper/<root>/<session_id>/`
- Work layers (mutation mode): `WD/.nodir/work/<root>/<session_id>/`
- Compatibility cache (legacy only): `WD/.nodir/cache/...`

## 10) Security and Validation
- Mount options must enforce least privilege (`nosuid`, `nodev`, `noexec` where compatible).
- Archive entries are untrusted input; traversal forms must be rejected.
- Projection control paths under `WD/.nodir/*` are never browse-addressable.
- Symlink handling must not escape run-scoped allowed roots.

## 11) Observability
Per acquire/release/commit/abort, logs should include:
- `runid`, `root`, `mode`, `purpose`, `backend`
- `archive_fingerprint`, `token`
- outcome: `reuse|mount|release|unmount|commit|abort|fallback_materialize`
- lock status, wall time, and canonical error code

## 12) Performance Expectations
- Repeated prep stages on stable archive fingerprint should be dominated by projection reuse.
- `.nodir/cache` growth should materially decline versus per-file materialization baseline.
- Full-root copy churn should be limited to explicit mutation commit boundaries.

## 13) Phase 6 Compatibility and Revisions
- Phase 6 mutation-owner boundaries remain valid.
- Phase 6 archive-form mutation mechanism (`materialize(root)+freeze`) is superseded by `mutation session + commit`.
- Existing Phase 6 artifacts must be revised where they prescribe thaw/freeze wrappers for read-only or path-heavy consumers.

## 14) Migration Policy
Migration sequence is utility-first:
1. Implement projection utilities and lifecycle controls.
2. Adopt projection APIs in helper layer (`wepp_inputs` and peers).
3. Migrate WEPP and other high-fanout path-heavy consumers.
4. Retain `materialize(file)` as explicit fallback only.
