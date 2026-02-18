# Agent Prompt: Phase 3 (Browse/Files/Download Integration)

## Mission
Implement Phase 3: wire browse/files/download surfaces to the shared NoDir core library so allowlisted `.nodir` roots are archive-navigable and archive-readable without extraction.

Phase 2 is complete. Reuse `wepppy/nodir/*` APIs; do not re-implement dir-vs-archive rules in each endpoint.

## Specs (Read First)
Normative:
- `docs/schemas/nodir_interface_spec.md`
- `docs/schemas/nodir-contract-spec.md`
- `docs/schemas/nodir-thaw-freeze-contract.md`
- `docs/work-packages/20260214_nodir_archives/artifacts/nodir_behavior_matrix.md`

Reference:
- `docs/work-packages/20260214_nodir_archives/artifacts/touchpoints_inventory.md`

## Scope Constraints
- In scope: browse/files/download integration only.
- Out of scope: materialization (Phase 4), thaw/freeze mutation workflows (Phase 5), bulk migrator (Phase 7).
- No silent precedence or fallback on mixed/invalid states.
- No extract-to-disk for browse/files/download archive reads.

## Code Targets
Primary integration files:
- `wepppy/microservices/browse/listing.py`
- `wepppy/microservices/browse/files_api.py`
- `wepppy/microservices/browse/_download.py`

Use shared NoDir APIs from:
- `wepppy/nodir/fs.py`
- `wepppy/nodir/paths.py`
- `wepppy/nodir/errors.py`

## Required Behaviors
### 1) Path and View Resolution
- Parse external subpaths with NoDir boundary rules.
- Support archive boundary syntax for allowlisted roots: `<root>.nodir/<inner>`.
- Support admin browse archive alias: `<root>/nodir/<inner>`.

### 2) Non-Admin Mixed-State Semantics
- In listings: hide both `<root>/` and `<root>.nodir` for mixed roots.
- On direct navigation to mixed targets: return `409` with `code=NODIR_MIXED_STATE`.

### 3) Admin Mixed-State Observability
- Admin browse can inspect both:
  - directory view: `/browse/<root>/...`
  - archive view: `/browse/<root>/nodir/...`
- Keep this observability-only; mixed state remains an error elsewhere.

### 4) Invalid Allowlisted Archive Semantics
- Archive-as-directory operations: `500` with `code=NODIR_INVALID_ARCHIVE`.
- Raw `<root>.nodir` bytes download:
  - admin: allowed
  - non-admin: `500` with `code=NODIR_INVALID_ARCHIVE`

### 5) Archive-Native Reads/Listing
- `/browse` and `/files` list/stat/read within archive via Phase 2 APIs.
- `/download/<root>.nodir/<inner>` streams inner entry bytes (no extraction).
- `.nodir` roots should render as directory-like in browse listings and sort with directories.

### 6) aria2c.spec
- `.nodir` archives listed as files only (do not expand inner entries).

## Error Contract
Map NoDir errors to canonical endpoint payloads consistently:
- `NODIR_MIXED_STATE` -> `409`
- `NODIR_INVALID_ARCHIVE` -> `500`
- `NODIR_LOCKED` -> `503` (if surfaced by transitional sentinels)
- `NODIR_LIMIT_EXCEEDED` -> `413` (unlikely in Phase 3 read paths, but preserve mapping)

## Tests (Must Add/Update)
Add/update route-level tests for browse/files/download behavior under:
- Dir form
- Archive form (`<root>.nodir`)
- Mixed state
- Invalid allowlisted archive
- Admin vs non-admin differences

Minimum scenarios:
1. `/files/...` listing inside archive boundary works and shape matches dir listing contract.
2. `/download/<root>.nodir/<inner>` returns entry bytes.
3. Non-admin mixed state direct navigation returns `409 NODIR_MIXED_STATE`.
4. Admin browse alias `/browse/<root>/nodir/...` resolves archive view.
5. Invalid allowlisted archive returns `500 NODIR_INVALID_ARCHIVE` for archive-as-directory operations.
6. Admin raw `<root>.nodir` download allowed while non-admin blocked per contract.

## Commands
Run targeted tests while iterating:
```bash
wctl run-pytest tests/microservices -k "browse or files or download or nodir"
```
Then run broader suite before handoff:
```bash
wctl run-pytest tests --maxfail=1
```

If frontend-controller or JS tests are touched, run:
```bash
wctl run-npm test
```

## Acceptance Criteria
- Browse/files/download conform to the behavior matrix for dir/archive/mixed/invalid states.
- No extraction is used for archive listing/preview/download entry reads.
- Admin mixed-state observability works only in browse; mixed state remains an error elsewhere.
- Added tests pass in containerized `wctl` runs.
