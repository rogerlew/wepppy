# NoDir: Archive-Backed Project Resources (`.nodir`)

**Status**: Closed - Canceled (2026-02-27)

## Cancellation Notice
This package is canceled and superseded by the full rollback package:
`docs/work-packages/20260227_nodir_full_reversal/`.

No further implementation should be scheduled under this package. Historical artifacts are retained for audit/reference only.

## Overview
WEPPcloud run trees on NFS accumulate a crippling number of small files (notably in `landuse/`, `soils/`, `climate/`, `watershed/`). This drives inode consumption and browse latency (metadata `stat()`/`readdir()`), blocking larger watershed support (10k+ hillslopes).

This package defines and implements a “NoDir” contract: treat selected project resources as directory-like logical trees that may be stored either as real directories or as single-file archives (`.nodir`, zip container) with seamless access via internal APIs and the browse service.

## Objectives
- Reduce inode count and metadata round-trips on `/wc1`/`/geodata` run trees by archiving high-fanout directories.
- Preserve existing run semantics for tooling that expects paths, while enabling archive-native reads for browse/files/download endpoints.
- Provide a safe migration tool to archive existing runs under `/wc1/runs` (and legacy `/geodata/wc1/runs` if present) without breaking provenance.
- Add regression coverage for the exact failure modes (browse listing, downloads, controller mutations).

## Scope

### Included
- Resources: `landuse`, `soils`, `climate`, `watershed` (directory or archive representation).
- NoDir is preferred (new runs should default to `.nodir` for allowlisted roots where safe), but directory form remains first-class for unmigrated runs.
- Browse microservice: directory listing + file preview/download for archive-backed trees.
- A crawler/migrator that can convert existing directory trees to `.nodir` archives (atomic replace, resumable, audit log).
- Contract docs: `docs/schemas/nodir-contract-spec.md`, `docs/schemas/nodir-thaw-freeze-contract.md`.

### Explicitly Out of Scope
- `wepp/` directory (WEPP executables require real file paths).
- Kernel/executable changes that require FUSE or OS-level virtual filesystems.
- Arbitrary user-uploaded archives (NoDir archives are server-generated artifacts only).

## Stakeholders
- **Primary**: Roger
- **Reviewers**: Ops + security
- **Informed**: Anyone working on browse/files services, NoDb controllers, or run lifecycle tooling

## Success Criteria
- [ ] A run with archive-backed `landuse/soils/climate/watershed` loads and functions (controllers + browse) with no manual steps.
- [ ] Browse can “enter” an archive-backed directory (HTML + JSON files API) and list/paginate entries with correct size/mtime.
- [ ] Download endpoints can stream a single file from inside an archive (no extract-to-disk required).
- [ ] Mixed state is deterministic + observable:
  - non-admin `/browse` hides both representations for mixed roots and returns `409` on direct navigation,
  - admin `/browse` exposes both `/browse/<root>/...` and `/browse/<root>/nodir/...`,
  - endpoints outside `/browse` fail loudly (no silent precedence) on mixed-state targets.
- [ ] Invalid `.nodir` handling is explicit:
  - non-admin gets `500` for invalid allowlisted `.nodir`,
  - admin can download raw bytes for forensics.
- [ ] A migration pass over a representative large run reduces inode usage materially (documented before/after).
- [ ] Security invariants hold: no traversal outside run root, no zip-slip extraction, bounded decompression.
- [ ] `wctl run-pytest tests --maxfail=1` passes (plus targeted new tests).

## Dependencies

### Prerequisites
- Agreement on on-disk naming and precedence rules (`<name>/` vs `<name>.nodir`) per `docs/schemas/nodir-contract-spec.md`.
- Rust zip writer integration in Peridot (candidate: `zlib-rs` + zip writer) or equivalent tooling for fast/controlled archive creation.

### Blocks
- Larger watershed support (10k+ hillslopes) on NAS-backed NFS remains constrained until inode/stat pressure is addressed.

## Related Packages
- Related: browse service security and error handling (`docs/dev-notes/endpoint_security_notes.md`).
- Related: NFS metadata benchmarks (`docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md`).

## Timeline Estimate
- **Expected duration**: 2-4 weeks (multi-PR)
- **Complexity**: High
- **Risk level**: High (storage + security + backwards compatibility)

## References
- `docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md` - small-file metadata benchmarks on NFS.
- `wepppy/microservices/browse/listing.py` - current directory listing + manifest behavior.
- `wepppy/microservices/browse/files_api.py` - JSON file listing contract (needs archive support).
- `docs/schemas/nodir-contract-spec.md` - NoDir contract (this package owns it).

## Deliverables
- NoDir contract + implementation + migration tooling + regression tests.

## Closure Notes
**Closed**: 2026-02-27 (Canceled)

**Summary**: The initiative direction changed from NoDir rollout to NoDir abandonment. Ownership moved to `docs/work-packages/20260227_nodir_full_reversal/`, which defines the phased rollback back to directory-only behavior.
