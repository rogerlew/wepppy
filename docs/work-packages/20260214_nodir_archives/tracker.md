# Tracker – NoDir: Archive-Backed Project Resources (`.nodir`)

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-02-14  
**Current phase**: Discovery  
**Last updated**: 2026-02-14  
**Next milestone**: Define migration crawler behavior (safety gates + audit logs + resumability) and perf targets.

## Task Board

### Ready / Backlog
- [x] Decide on canonical on-disk naming and precedence rules (`<name>/` vs `<name>.nodir`, and whether both may coexist).
- [x] Inventory read/write/mutate call sites for `landuse/`, `soils/`, `climate/`, `watershed/` (Python + Rust + shell-outs). See `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`.
- [x] Define browse URL semantics for “entering” an archive (path-based boundary).
- [x] Lock behavior matrix (dir vs archive vs mixed vs invalid) for all affected surfaces. See `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`.
- [ ] Add perf targets (browse p95 listing time, inode reduction, archive build time).
- [ ] Specify and implement thaw/modify/freeze state tracking (`WD/.nodir/<root>.json`) and crash recovery rules.
- [ ] Define symlink dereference size thresholds and audit policy (warn at 1 GiB default; allowlist external roots).
- [ ] Lock mixed-state behavior: non-admin hidden + 409; admin dual browse view + mixed-state warning block.
- [ ] Lock NoDir maintenance lock contract: Redis key format + ordering + fail-fast semantics.
- [ ] Lock invalid `.nodir` semantics: admin raw bytes; everyone else 500.

### In Progress
- [ ] Define migration crawler behavior: safety gates, audit logs, resumability, and rollback.

### Blocked
- [ ] Confirm whether any controllers mutate these trees frequently post-creation (affects archive update strategy).

### Done
- [x] Create work package scaffold (2026-02-14)
- [x] Start NoDir contract spec (`docs/schemas/nodir-contract-spec.md`) (2026-02-14)
- [x] Freeze NoDir contract decisions (naming, precedence, URL boundary) and update `docs/schemas/nodir-contract-spec.md`. (2026-02-14)
- [x] Inventory touch points for `landuse/soils/climate/watershed` (see `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`). (2026-02-14)
- [x] Lock NoDir behavior matrix (see `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`). (2026-02-15)
- [x] Update infrastructure note with inode/stat pressure context (2026-02-14)
- [x] Patch omni scenario/contrast shared-input symlinks to prefer `.nodir` when present (2026-02-14)

## Decisions

### 2026-02-14: NoDir resources are server-generated (not user-supplied)
**Context**: Treating generic/user `.zip` files as enterable “directories” expands the attack surface (zip bombs, unexpected paths) and creates confusing recursion questions (`.zip` inside `.zip`).

**Decision**: NoDir archives are created by WEPPcloud tooling only; browse treats only known resource roots as “directory-like archives”.

**Impact**: Security posture stays close to “browse real files under run root”, while still solving inode/stat pressure.

---

### 2026-02-14: Use `.nodir` Extension to Avoid `.zip` Recursion + User Upload Ambiguity
**Context**: The platform already has legitimate `.zip` artifacts (exports) and at least one user-provided `.zip` upload workflow (ag fields plant DB). If browse treats `.zip` specially, it forces recursive rules (“zip in zip”) and widens exposure to untrusted archives.

**Decision**: NoDir archives use the `.nodir` extension. Browse/files/download treat `.nodir` as the only archive boundary; `.zip` remains a normal downloadable file.

**Impact**: Archive navigation remains deterministic and avoids accidental “enterability” of user uploads or unrelated zip artifacts.

---

### 2026-02-14: Representation Is Discovered (Not Serialized in NoDb)
**Context**: Runs may be migrated/archived out-of-band. Persisting “dir vs archive” flags inside `.nodb` payloads will drift and cause confusing partial failures.

**Decision**: NoDb/controller state MUST NOT persist NoDir representation. Always discover via existence checks at time of use. Precedence is directory then archive. Mixed state is tolerated but warned; no runtime cleanup/deletion.

**Impact**: Offline archival/migration is safe; runtime remains read-only with respect to representation selection.

---

### 2026-02-14: Freeze Dereferences Symlinked Files
**Context**: Some run assets are stored as symlinks (e.g., rasters) and would become broken references if the directory tree is removed.

**Decision**: Freeze/migration tooling dereferences symlinked files and stores their target bytes as regular entries inside the `.nodir` (symlink metadata is not preserved).

**Impact**: Archives become self-contained artifacts, but may also import external bytes into the run tree (data governance/security review required).

---

### 2026-02-14: NoDir Maintenance Lock Uses Redis (Per-Root)
**Decision**: Thaw/freeze/migration acquire `nodb-lock:<runid>:nodir/<root>` before modifying NoDir roots.

---

### 2026-02-14: Mixed-State Is Admin-Dual-View + Non-Admin Hidden + 409
**Decision**:
- non-admin browse hides both representations for mixed roots and returns `409 Conflict`,
- admin browse exposes `/browse/<root>/...` (directory) and `/browse/<root>/nodir/...` (archive view),
- mixed-state roots are called out in the browse UI below pagination.

---

### 2026-02-14: Invalid Allowlisted `.nodir` Is 500 (Admin Can Download Raw Bytes)
**Decision**: For invalid allowlisted `.nodir`, admin can fetch raw bytes; everyone else gets `500`.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Zip slip / path traversal via archive entries | High | Medium | Never extract during browse; validate entry paths; reject absolute/`..` segments | Open |
| Zip bombs / decompression DoS | High | Medium | Bound uncompressed byte counts; stream with limits; prefer server-generated archives | Open |
| Partial archive writes (corrupt `.nodir`) on NFS | High | Low | Write to `*.tmp` then atomic rename; include integrity marker/manifest | Open |
| Regression: code assumes directories exist | High | High | Inventory call sites; add NoDir abstraction; add regression tests | Open |
| Data leakage via dereferenced external symlinks | High | Medium | Require explicit allowlist for external roots; audit log includes source realpaths; consider redaction/denylist | Open |
| Unexpected storage blowup from dereferenced symlinks | Medium | Medium | Warn at 1 GiB per symlink target (default); record totals in audit; allow per-run override | Open |
| Regression: ancillary browse actions assume FS paths (`/gdalinfo/`, `/dtale/`, `/diff/`) | Medium | High | Decide per-endpoint behavior (disable/materialize/stream); add targeted tests | Open |
| Query-engine performance collapse if Parquet lives in compressed archive entries | High | Medium | Keep Parquet out of archives or store uncompressed + cache/materialize during activation | Open |
| Browse listing latency for huge archives | Medium | Medium | Central-directory caching; optional per-archive manifest | Open |
| Ambiguity when both `<name>/` and `<name>.nodir` exist | Medium | Medium | Define deterministic precedence; log warnings; migration should avoid mixed state | Open |

## Progress Notes

### 2026-02-14: Initial scoping
**Agent/Contributor**: Codex

**Work completed**:
- Created work package scaffold.
- Started NoDir contract spec draft.
- Updated NFS benchmark note with inode/stat pressure context and archive direction.

**Next steps**:
- Freeze on-disk naming + precedence.
- Decide browse URL boundary for archives (path-based preferred for “seamless” navigation).
- Inventory all mutations for `landuse/soils/climate/watershed`.
