# Run Migration Strategy
> Detect and upgrade legacy, unversioned run directories safely, with rollback and observability.

## Goals
- Detect runs stuck at NoDb version `0` (no `nodb.version` marker) and apply targeted upgrades without risking production data.
- Reuse the existing archive/restore pipeline so every migration is atomic and reversible.
- Produce a reusable corpus of pre-migration snapshots for regression testing future migrations.

## Where versioning is enforced
- `wepppy/nodb/version.py` introduces `nodb.version` and treats runs with `.nodb` files but no version file as version `0`. `ensure_version` is invoked from `NoDbBase.__init__` and `_hydrate_instance` so any writable load runs through the migrator.
- New runs (no `.nodb` artifacts) default to `CURRENT_VERSION` (currently `1000`), so only legacy runs need bespoke traits/migrations.

## How to pull production runs safely
- Use `/workdir/wepppy-win-bootstrap/scripts/wget_download_weppcloud_project.sh` (or sibling download scripts) to copy production runs from `wepp.cloud` onto `forest.bearhive.duckdns.org` for dry-run migrations.
- Store imports as first-class dev runs under the normal root (e.g. `/wc1/runs/<runid>/<config>`), but add provenance markers so we can find them later (see below).

## Existing migration scripts (inventory)
- `wepppy/tools/migrations/README.md` documents runnable utilities:
  - `migrate_watersheds_peridot_tables.py` — normalize Peridot parquet schemas.
  - `migrate_wbt_geojson_ids.py` — fix WhiteboxTools GeoJSON ID typing.
  - `migrate_landuse_parquet.py` — add/normalize `topaz_id`/`wepp_id` in landuse parquet.
  - `migrate_soils_parquet.py` — same for soils parquet.
  - `migrate_ashpost_pickles.py` — rebuild ash outputs from pickles.
- RQ helper: `wepppy/rq/interchange_rq.py::run_interchange_migration` regenerates interchange outputs once prerequisites exist.
- Archive/restore flow: `wepppy/rq/project_rq.py` + `wepppy/weppcloud/routes/archive_dashboard` is the rollback mechanism we should reuse for migrations.

## Trait-based detection and upgrade plan
- **Trait model:** define detectors that flag missing/legacy assets (e.g., `watershed/hillslopes.parquet` absent, `channels.parquet` missing IDs, ash pickles present, GeoJSON IDs as strings). Each trait maps to a migration function and a validation check.
- **Ordering:** traits can be independent; store them as a DAG if dependencies emerge (example: fix GeoJSON IDs before regenerating interchange).
- **Execution contract:** each migration executes inside an archive guard:
  1. Ensure no active `.nodb` locks.
  2. Create an archive (reuse `archive_rq` implementation).
  3. Run the trait migrations sequentially with logging to `<runid>:migration`.
  4. Validate (schema checks, counts, optional spot queries).
  5. On success, stamp `nodb.version` to the new target.
  6. On failure, emit status + offer restore (using existing archives UI).
- **Corpus:** keep the pre-migration archive alongside a normalized “post” archive for regression testing (fixture input/output pairs for future migrations).

## Provenance tracking for imported runs
- Keep runs in the standard tree so `get_wd` needs no special cases. Add a sidecar marker per imported run (e.g. `<wd>/.provenance.json`) with fields like `source_host`, `pulled_at`, `original_path`, `notes`, `version_at_pull`.
- Centralize tracking in the Flask DB (new migrations table) so dev/test-prod/prod share the same schema. Suggested columns: `id`, `runid`, `config`, `local_path`, `source_host`, `original_url`, `pulled_at`, `owner_email`, `version_at_pull`, `traits_detected` (JSON), `last_migration_version`, `last_status`, `archive_before`, `archive_after`, `is_fixture`, `created_at`, `updated_at`.
- Scripts and dashboards read the marker for on-disk provenance and the Flask table for fleet-wide reporting/filtering; runtime loaders ignore both.

## Admin run-sync dashboard + RQ job
- Admin-only panel to import runs from a source host (default `wepp.cloud`) using the wget script or HTTP. Inputs: host, runid, config, target path (defaults to standard root), auth token if needed.
- Focus action: “Sync + register” → uses `run_sync_rq` to download via aria2c inside the container, write `.provenance.json`, and register the run in the migrations table if not already present. Include an owner email field so an admin can assign/run ownership on import.
- Backed by an `run_sync_rq` job emitting to `<runid>:run_sync` channel: steps include aria2c download, checksum/size verification, provenance write, and registration; trait scans/migrations remain separate follow-up actions.
- Dev → prod: admins can point the host to `wc.bearhive.duckdns.org` to push a dev run upstream; keep this guarded by an explicit “allow push” flag.

## Admin run-sync dashboard implementation plan (agent-ready)
- **Scope:** Add a new admin-only dashboard to sync/import runs from remote WEPPcloud hosts, register provenance, and show job status. No migrations run here.
- **Data model:** New Flask DB table (migration) with columns listed in “Provenance tracking” above; add Alembic migration. Seed `owner_email` nullable string; `traits_detected` JSON; `last_status` enum/string.
- **RQ job (`run_sync_rq`):**
  - Location: `wepppy/rq/run_sync_rq.py` (+ stub `.pyi`).
  - Inputs: `runid`, `config`, `source_host`, `owner_email`, `target_root` (default `/wc1/runs`), optional `auth_token`, `allow_push` bool.
  - Steps: build source URL, run aria2c (within container) to mirror into target path; verify size/checksum if provided; write `.provenance.json`; upsert migrations table row; emit status to `<runid>:run_sync`; handle errors with TRIGGER `EXCEPTION`.
  - Helper: reuse archive helpers for path safety; ensure READONLY runs are skipped.
- **Blueprint/UI:**
  - New blueprint under `wepppy/weppcloud/routes/run_sync_dashboard/` with template `rq-run-sync-dashboard.htm`.
  - Expose page route (admin login required) and API endpoints:
    - `GET /rq/run-sync` → render dashboard.
    - `POST /rq/api/run-sync` → enqueue `run_sync_rq`.
    - `GET /rq/api/run-sync/status` → list recent sync jobs + DB records for filtering.
  - Controller JS: add small controller to `controllers_js/` (Pure style) to submit form, stream websocket logs from `<runid>:run_sync`, and refresh status table.
  - Form fields: source host (default `wepp.cloud`), runid, config, target root (default), owner email, auth token (optional), allow push toggle.
- **Provenance writing:**
  - `.provenance.json` content: `source_host`, `pulled_at`, `original_url`, `owner_email`, `version_at_pull`, `notes` (optional), `runid`, `config`.
  - DB upsert on sync completion; set `last_status` and timestamps.
- **Websocket/status:**
  - Mirror archive dashboard pattern: reuse StatusMessenger; channel `<runid>:run_sync`; events: `ENQUEUED`, `DOWNLOADING`, `CHECKSUM_OK`, `REGISTERED`, `COMPLETE`, `EXCEPTION`.
- **Validation/guards:**
  - Require admin auth; refuse overwrite if `.nodb` lock active; allow overwrite of existing run with explicit checkbox.
  - When `allow_push` true and host is `wc.bearhive.duckdns.org`, ensure auth token present.
- **Testing:**
  - Unit: stub aria2c call; assert provenance write and DB upsert.
  - Routes: verify admin-only access; API enqueues job with expected payload.
  - RQ job: temp dir harness to simulate download via a dummy file; ensure `.provenance.json` + DB record.
- **Rollout:**
  - Add Alembic migration, register blueprint in `wepppy/weppcloud/app.py`, add menu link under admin-only navigation.
  - Update docs/README if needed and hook into existing websocket client utilities.

## RQ migration dashboard sketch
- Similar to `rq-archive-dashboard`: lists detected traits per run, shows current version (0 vs 1000), and streams progress via websocket.
- Actions:
  - “Run migration” → enqueues a dedicated `migration_rq` job that wraps the archive+trait pipeline.
  - “Validate only” → runs trait detectors/validators without writes.
  - “Restore last archive” → reuse existing restore route.
- UI lists:
  - Traits detected (with short descriptions).
  - Planned migrations (with links to scripts/helpers).
  - Resulting version after migration.

## Workflow for production catch-up
1. **Collect candidates:** download runs from production to staging using the wget script; group by creation date/config.
2. **Scan:** run trait detectors + `read_version` report to identify version `0` runs and missing assets.
3. **Dry-run migrations:** execute migrations with `--dry-run`/validation-only to surface blockers.
4. **Pilot migrations:** enable archive-guarded migrations on staging; review outcomes and captured before/after archives.
5. **Ship dashboard + RQ job:** deploy to production once the pipeline is vetted; restrict to authenticated admins initially.
6. **Monitor:** track successes/failures via the websocket channel and keep the corpus updated as new traits/migrations land.

## Open questions / decisions
- Define target version increments per trait bundle (e.g., `1001` for parquet schema fixes, `1002` for GeoJSON ID fix + interchange regeneration).
- Decide retention policy for migration-generated archives in production (count or TTL).
- Confirm whether interchange regeneration can be chained automatically after GeoJSON/parquet normalization or left as an explicit action.
