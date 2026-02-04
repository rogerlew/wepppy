# Mini Work Package: Recorder Async Microservice
Status: On Hold (decisions locked)
Last Updated: 2026-02-04
Primary Areas: `wepppy/microservices/recorder/`, `wepppy/profile_recorder/`, `wepppy/weppcloud/controllers_js/http.js`, `wepppy/weppcloud/controllers_js/recorder_interceptor.js`, `docker/docker-compose.*.yml`, `docker/caddy/Caddyfile*`, `wepppy/config/redis_settings.py`

## Objective
Move `/runs/<runid>/<config>/recorder/events` off the Flask app and make recorder writes asynchronous using a dedicated Starlette microservice plus a Redis-backed queue.

## Cursory Observations
- Recorder writes currently run in the request thread and show up as high 502 volume.
- The client already batches events (default 10 events or 200ms).
- `rq-engine` already issues session tokens; we can reuse that JWT flow for recorder auth.

## Status Update (2026-02-04)
- Production WEPPcloud traffic is recorder-heavy (~87% of requests), but recorder response times are fast and recorder routes only account for ~12% of total request duration.
- We increased worker count by 50% and doubled the cpuset allocation. We will revisit this implementation only if recorder becomes a confirmed bottleneck.

## Scope
- Add a new recorder microservice that accepts recorder event batches.
- Authenticate with JWTs (same validation flow as `/rq-engine/api`).
- Enqueue events into Redis; do not write audit logs in the request handler.
- Ensure recorder processing is idempotent; duplicate stream deliveries must not produce duplicate audit or assembler output.
- Add a background worker that drains the queue and calls `ProfileRecorder.append_event()`.
- Update JS recorder transport to use session tokens (Authorization header) and `fetch(..., { keepalive: true })`.
- Route traffic via Caddy to the new service.
- Initial deployment uses exactly one worker process; multi-worker concurrency is out of scope.

## Non-goals
- Change recorder payload schema or semantics.
- Require new client-side payload fields (legacy `id` is accepted as `eventId`).
- Implement per-event acknowledgments or read APIs.
- Replace the profile recorder assembler or its file format.

## Architecture
### Components
1. **Recorder API service (Starlette)**
   - Accepts `POST /runs/{runid}/{config}/recorder/events` (Caddy strips `/weppcloud`).
   - Validates payload, authorizes the run, enqueues events, returns `204`.

2. **Recorder worker**
   - Long-running process that drains the queue.
   - Writes JSONL audit logs and runs assembler logic via `ProfileRecorder.append_event()`.
   - Uses per-run+config locking to avoid JSONL interleaving when multiple workers are enabled.
   - Preserves audit attribution and assembler override parity with the current Flask route.

3. **Redis queue**
   - Dedicated DB index `RedisDB.RECORDER_QUEUE = 12`.

### Data Flow
1. Browser batches recorder events and sends to recorder microservice with a session token.
2. Recorder microservice enqueues the batch (fast) and returns `204`.
3. Worker pops batches and writes logs/assembler output.

## Auth
- Use `require_jwt()` + `authorize_run_access()` from `wepppy/microservices/rq_engine/auth.py`.
- Tokens are minted by existing `POST /rq-engine/api/runs/{runid}/{config}/session-token`.
- Audience is `rq-engine` (default in `require_jwt`); no additional scope checks.
- This is intentional: run access is the only authorization gate for recorder writes.
- Accepted token classes: `session`, `user`, `service`, `mcp`.
- `runid` is always validated via `authorize_run_access()`, but composite omni/contrast runids require parent-aware handling (see below).
- `runid` validation rules (must be enforced in the recorder API, after URL decoding):
  - Accept either a simple slug (`[A-Za-z0-9._-]+`) or a composite runid per `docs/composite-runid-slugs.md`.
  - Composite format: `<parent_runid>;;omni;;<scenario>` or `<parent_runid>;;omni-contrast;;<contrast_id>`.
  - The parent segment can itself be composite; validation must recurse on the parent portion (strip the trailing `;;omni;;...` / `;;omni-contrast;;...` suffix and re-validate).
  - All segments must be ASCII slugs and MUST NOT contain `/`, `\`, or `..`.
  - **No double-decode:** Starlette path params are already decoded; do not decode again.
  - **Raw-path guard:** reject requests whose raw path contains `%2F`, `%5C`, `%252F`, or `%255C` (case-insensitive) to prevent encoded-slash bypasses.
- **Composite omni/contrast behavior:** compute `parent_runid` by stripping the trailing `;;omni;;...` / `;;omni-contrast;;...` suffix when present.
  - Use `parent_runid` for owner checks and working-directory resolution (matches `docs/composite-runid-slugs.md`).
  - Token validation (session marker + run claims) continues to use the full path `runid` from the URL.
- **Auth flow order (must be explicit in code):**
  1. `claims = require_jwt(request)` (audience `rq-engine`).
  2. `authorize_run_access(claims, runid)` using the **full** `runid` from the URL so run claims are enforced.
  3. If `runid` is composite omni/contrast, compute `parent_runid` and perform an **additional** owner check against `parent_runid` (same logic as `_authorize_user_claims`).
  4. Enforce `config` slug rules and token `config` claim matching (see below).
  5. Reject unknown/missing `token_class`.
- `config` validation rules (must be enforced in the recorder API):
  - `config` must be an ASCII slug (`[A-Za-z0-9._-]+`) and must not contain `/`, `\`, or `..` after URL decoding.
  - If the token includes a `config` claim, it must match the path `config` (applies to `user` tokens too).
  - For `session` tokens, the `config` claim is required and must match.
  - For `service`/`mcp` tokens, a `runs`/`runid` claim is required; tokens without run claims are rejected.
  - For `service`/`mcp` tokens, a matching `config` claim is required.
- Tokens with an unknown or missing `token_class` are rejected (`403`).
- Implementation note: these checks are **additional** to `require_jwt()` + `authorize_run_access()` and must be enforced explicitly in the recorder API handler.
- Deployment note: if any `service`/`mcp` recorder clients lack `config` claims, update token issuance before rollout.
## API
### POST `/runs/{runid}/{config}/recorder/events`
- **Auth:** `Authorization: Bearer <token>`
- **Headers:** `Content-Type: application/json`; `X-Recorder-Keepalive: 1` when the client uses `fetch(..., { keepalive: true })`.
- **Body:** `{ "events": [ { ...event... }, ... ] }`
- **Response:** `204 No Content` on success.
- **Errors:** `400` for invalid payload, `401/403` for auth failures, `413` for oversize payloads (64KB keepalive cap, 1MB general cap), `503` if queue is unavailable.
- **Validation:** each event must include `eventId` or legacy `id`. The server normalizes to `eventId`; if both are missing, return `400`.
- **Error payloads:** Must follow `docs/schemas/rq-response-contract.md`.
- **Methods:** `POST` only; respond `405` for other methods. Allow `OPTIONS` for CORS preflight.

## Queuing Details
- Each enqueue item is one batch (the client already batches).
- Items include `runid`, `config`, and the `events` list.
- Items must also include:
  - `actor`: user/session metadata derived from the JWT claims at enqueue time (user id/email/session id, token class).
  - `assembler_override`: computed at enqueue time using the same `Ron`-based logic as the Flask route.
- **Chosen approach:** Redis Streams with consumer group `recorder`.
  - `XADD recorder:events * runid <id> config <cfg> payload <json>`
  - Consumer group: `XGROUP CREATE recorder:events recorder 0-0 MKSTREAM` on startup.
  - Read: `XREADGROUP GROUP recorder <consumer> COUNT <n> BLOCK 5000 STREAMS recorder:events >`.
  - Ack and delete on success: use a Lua script to `XACK` + `XDEL` + `HDEL` (and decrement a backlog counter) atomically so metrics stay consistent.
- Retry: on failure after lock acquisition and processing attempt, leave the entry pending and increment `recorder:events:attempts` (hash keyed by stream id). The worker must run a reclaim pass using `XAUTOCLAIM` after an idle threshold (default 300s, configurable, must exceed worst-case batch processing time).
- Retry: after worker startup, run a one-time reclaim pass with `XAUTOCLAIM` using `min-idle=0` to drain the PEL immediately, then proceed with the configured idle threshold.
  - The startup `min-idle=0` reclaim is allowed only under the single-worker assumption; if multi-worker is enabled, use `min-idle >= lock TTL` or skip the startup reclaim.
  - Poison handling: after 5 failures, atomically move the payload to `recorder:events:dead` (use `MAXLEN ~ 50000`) and clean up the original entry using Lua or `MULTI/EXEC`: `XADD` to the dead stream, then `XACK`, `XDEL`, `HDEL` attempts, and decrement the backlog counter in one transaction.
  - Crash recovery: unacked entries remain pending and are reclaimed via `XAUTOCLAIM`; per-run+config lock TTL ensures stalled workers do not block replays.
- Backpressure (atomic and bounded):
  - Enqueue must use a Lua script with a dedicated counter (for example `recorder:events:backlog`): if `GET >= 250000`, reject with `503`; otherwise `XADD` + `INCR` and return the entry id.
  - Decrement the backlog counter only when the entry is removed from the main stream (`XACK` + `XDEL`).
  - `XLEN` is informational only and not used for enforcement.
  - Drift recovery: provide a reconcile helper (manual ops) that recomputes backlog and resets the counter if it diverges.
- Idempotency (explicit ordering and tradeoff):
  - Require `eventId` on each event payload.
  - For each event, `SADD recorder:dedupe:{runid}:{config} <eventId>` with `EXPIRE` 7 days on the set.
  - Only append JSONL / call the assembler when `SADD` returns `1`.
  - If a crash occurs after the `SADD` and before append, the event is dropped by design to avoid duplicates.
  - Lock ordering: acquire the per-run+config lock **before** any `SADD` dedupe mutation. If the lock is not held, do not mutate the dedupe set.
- Batch failure semantics:
  - Batches are **not** atomic. The worker processes events sequentially and applies dedupe per event.
  - If an event fails validation, skip it and continue; do not fail the batch.
  - If a storage/append error occurs mid-batch, the worker must treat the batch as failed and leave it pending. On retry, dedupe prevents duplicate writes for events already persisted.
  - Lock contention or lock-renewal failure does **not** increment attempts; leave the batch pending for retry.
- No silent fallback if Redis is unavailable (fail fast with 503, canonical error payload).
- Redis requirement: Redis >= 6.2 is required for `XAUTOCLAIM`.
## JS Transport Changes
- Replace `sendBeacon` usage with `WCHttp.requestWithSessionToken()` so the Authorization header is sent.
- Add a `keepalive` option to `WCHttp.request` and use it only for unload-time flushes.
- Add a hard batch size cap (bytes) for unload keepalive requests; cap `64KB`. If exceeded, drop excess on unload with a logged warning.
- Include `X-Recorder-Keepalive: 1` on unload-time requests; the server enforces `64KB` when that header is present.
- Enforce a general recorder payload cap (default `1MB`) with `413` + canonical error payload.
- Keepalive enforcement is best-effort: if the header is missing (older clients or bugs), fall back to the 1MB cap and log for monitoring.
  - If `keepalive` is used without the header, emit a structured warning (include runid/config) so we can measure client drift.
- Ensure each event includes a stable `eventId` (retain existing `id` values for correlation; `eventId` must be unique within a run+config).
- During the transition, copy legacy `id` into `eventId` when present so both fields are populated.
- Pre-fetch and cache the session token during normal page activity; unload-time flushes must not depend on a token refresh.
- Keep batching and flush interval behavior unchanged otherwise.
## Deployment / Routing
- Add a new service in `docker-compose.*` (`recorder-api` + `recorder-worker`).
- Add Caddy routing to forward `/weppcloud/runs/{runid}/{config}/recorder/events` to `recorder-api` **and** strip the `/weppcloud` prefix so the microservice receives `/runs/{runid}/{config}/recorder/events`.
- Use this explicit snippet (do not use `handle_path` here):
  ```text
  @recorder_events path_regexp recorder_events ^/weppcloud/runs/[^/]+/[^/]+/recorder/events$
  handle @recorder_events {
      uri strip_prefix /weppcloud
      reverse_proxy recorder-api:8000
  }

  @recorder_events_slash path_regexp recorder_events_slash ^/weppcloud/runs/([^/]+)/([^/]+)/recorder/events/$
  handle @recorder_events_slash {
      redir /weppcloud/runs/{re.recorder_events_slash.1}/{re.recorder_events_slash.2}/recorder/events?{query} 308
  }
  ```
- Add an edge guard to reject raw paths containing `%2F`, `%5C`, `%252F`, or `%255C` (case-insensitive) before the Flask fallback to avoid routing bypasses.
  - Edge guard is best-effort; **always** enforce the raw-path guard in the recorder API using `scope["raw_path"]` bytes in early middleware before routing.
  - The recorder API must assume it can be called directly (bypassing Caddy), so raw-path guard + trailing slash behavior must be enforced in-app regardless of edge config.
- Ensure the worker has access to `/wc1` and `/geodata` so it can resolve run paths.
- Ensure the recorder API has the same filesystem access if `assembler_override` computation reads run files (mount `/wc1` and `/geodata` when needed).
- Trailing slash requests are redirected to the canonical path; the microservice only accepts the canonical path.

## Decisions Locked
- Auth flow order:
  - `require_jwt()` then `authorize_run_access()` on the full path `runid`.
  - If composite omni/contrast, compute `parent_runid` and run owner checks against the parent.
  - Enforce `config` claim matching after auth, and reject unknown/missing `token_class`.
- Composite runid validation:
  - Accept simple slugs or composite omni/contrast per `docs/composite-runid-slugs.md`.
  - Parent composite segments are allowed and must be recursively validated.
  - Reject decoded `/`, `\`, `..`, and raw-path encoded slashes.
- Raw-path enforcement:
  - Edge guard is best-effort; recorder API always enforces raw-path guard using `scope["raw_path"]`.
  - Recorder API must assume direct calls (bypassing Caddy).
- Trailing slash behavior:
  - Caddy handles redirects; Starlette `redirect_slashes` is disabled in-app.
- Backpressure drift recovery:
  - Provide an ops reconcile helper to recompute backlog and reset counters.
  - Optional `XTRIM` on the main stream to control tombstone growth.
## Implementation Plan
1. **Redis DB index**
   - Add `RedisDB.RECORDER_QUEUE = 12` in `wepppy/config/redis_settings.py`.
   - Implement `recorder_queue_connection_kwargs()` or reuse `redis_connection_kwargs` with the new DB.

2. **Recorder queue module**
   - New `wepppy/profile_recorder/queue.py` with `enqueue_batch()` and `dequeue_batches()` helpers.
   - Provide stream + consumer group implementation, plus Lua-backed enqueue to enforce the hard cap.
   - On success, atomically `XACK` + `XDEL` + `HDEL` attempts and decrement the backlog counter.
   - Implement `XAUTOCLAIM` path for idle entries.
   - Handle `BUSYGROUP` on startup (create if missing, ignore if already exists).
   - Implement dead-letter handling with `MAXLEN ~ 50000`, using an atomic Lua/MULTI move + cleanup + backlog decrement.
   - Maintain a backlog counter (`recorder:events:backlog`) for backpressure.
   - Provide a reconcile helper for ops that recomputes backlog from `XLEN` + pending entries and resets the counter (manual recovery for drift).
   - Add optional `XTRIM` on the main stream (for example, `MAXLEN ~ <n>`) to prevent unbounded tombstones.

3. **Recorder API service**
   - New `wepppy/microservices/recorder/app.py` (Starlette).
   - Route handler validates payload, checks auth, enqueues, returns 204.
   - Enforce runid format rules (slug or composite runid) and reject decoded `/`, `\`, or `..`.
   - Reject raw paths containing `%2F`, `%5C`, `%252F`, or `%255C` and do not double-decode path params (see Auth).
   - Implement composite omni/contrast parsing:
     - Validate composite runids per `docs/composite-runid-slugs.md`.
     - Compute `parent_runid` (strip trailing `;;omni;;...` / `;;omni-contrast;;...`) for owner checks and WD resolution.
     - Keep the full path `runid` for token validation and queue payloads.
   - Enforce `config` slug rules and token config matching (see Auth).
   - Require `service`/`mcp` tokens to include run claims and matching `config` claim.
   - Enforce request byte caps (`64KB` when `X-Recorder-Keepalive: 1`, `1MB` otherwise).
   - Capture `actor` metadata and `assembler_override` for the queued payload so worker behavior matches the Flask route.
   - Handle `OPTIONS` preflight and return `405` for unsupported methods.
   - Disable `redirect_slashes` in Starlette so Caddy controls trailing slash behavior consistently for `POST` and `OPTIONS`.
   - Use canonical error payloads from `docs/schemas/rq-response-contract.md` (reuse rq-engine `error_response` helper if shared).

4. **Recorder worker**
   - New `wepppy/profile_recorder/worker.py` that drains the queue and invokes `ProfileRecorder`.
   - Uses `RecorderConfig` and a minimal app-like config wrapper.
   - Log failures but do not drop batches silently.
   - Resolve working directories using composite runid rules (`docs/composite-runid-slugs.md`). For omni/contrast runids whose parent is composite, strip the trailing suffix, resolve the parent WD, then append `_pups/omni/{scenarios|contrasts}/<id>`; do not call `get_wd()` with a 5-part composite runid.
   - Acquire per-run+config lock (Redis DB 0, e.g. `locked:recorder:{runid}:{config}`) before any dedupe or append work.
   - Add an idempotency guard while the lock is held: `SADD` the `eventId` before append; only append JSONL + call assembler when `SADD` returns `1`.
   - Lock ownership: store a unique token value; renew and release only if the token matches (Lua compare-and-del).
   - Lock renewal must be compare-and-extend (token-checked `PEXPIRE`/`EXPIRE`) so stale workers cannot extend locks they no longer own.
   - Use a lock TTL (initially 120s) and renew every 30s while processing so mid-write expiration cannot happen.
   - If the lock cannot be acquired or renewal fails mid-batch, do **not** ack/delete the batch and do **not** increment attempts; leave it pending for retry.
   - Persist queued `actor` metadata so audit attribution parity is maintained:
     - Extend `ProfileRecorder.append_event()` (or wrap it) to accept an `actor` object and write it into the JSONL record.
     - For `user` tokens, also populate the legacy `user` field (id/email) so existing tooling stays compatible.
   - Pass through queued `assembler_override` into `ProfileRecorder.append_event()` to preserve parity.

5. **Caddy routing**
   - Add a high-priority `path_regexp` matcher for `/weppcloud/runs/{runid}/{config}/recorder/events` and a trailing-slash redirect.
   - Use `uri strip_prefix /weppcloud` so the upstream sees `/runs/{runid}/{config}/recorder/events`.
   - Keep it before the Flask fallback in the `route /weppcloud/*` block.

6. **JS updates**
   - Update `recorder_interceptor.js` to send via `WCHttp.requestWithSessionToken()`.
   - Add `keepalive` support to `WCHttp.request` and pass `keepalive: true` for recorder flushes.
   - Enforce max payload bytes for keepalive (chunk or drop-on-unload with warning) and send `X-Recorder-Keepalive: 1`.

7. **Compose wiring**
   - Add `recorder-api` service using `uvicorn` directly.
   - Add `recorder-worker` service (plain `python -m wepppy.profile_recorder.worker`).
## Test Plan
### Unit
- Queue: enqueue/dequeue round trip with a temporary Redis instance or stub.
- Auth: recorder API rejects missing/invalid tokens.
- Auth: enforce `config` slug rules and token config matching.
- Auth: reject `service`/`mcp` tokens that omit run claims.
- Auth: reject missing/unknown `token_class` and missing `config` claim on `session` tokens.
- Auth: reject `service`/`mcp` tokens missing a matching `config` claim.
- Auth: reject `user` tokens with mismatched `config` claim.
- Auth: reject malformed `runid` values (`..`, encoded slashes, bad grouped format).
- Auth: composite omni/contrast runid with composite parent validates and resolves `parent_runid` for owner checks.
- Auth: verify `authorize_run_access()` is called with the full path `runid` and owner checks use `parent_runid`.
- Validation: reject raw paths containing `%2F`, `%5C`, `%252F`, or `%255C` (case-insensitive).
- Worker: batch with multiple events writes JSONL and calls assembler hook.
- Idempotency: reprocess the same batch twice and assert JSONL + assembler are only updated once.
- Queue: `XACK` + `XDEL` + `HDEL` updates the backlog counter correctly (Lua path).
- Queue: dead-letter path after 5 failures and attempts hash cleanup.
- Queue: poison handling move is atomic (dead-letter entry + `XACK`/`XDEL`/`HDEL` all applied once).
- Queue: backpressure cap rejects enqueue when backlog counter `>= 250000` with `503` + canonical error payload.
- Dedupe: same `eventId` across different configs does not collide (per-config dedupe key).
- Error contract: `400/401/403/413` responses follow `rq-response-contract`.
- Queue: `XAUTOCLAIM` reclaims pending entries after the configured idle threshold.
- Worker: audit attribution (user/session metadata) and `assembler_override` match the current Flask route behavior.
- Worker: queued `actor` metadata is persisted (and `user` fields are set for user tokens).
- Worker: lock contention/renewal failure leaves batches pending (no ack/drop).
- Worker: lock release only succeeds when the lock token matches (stale unlocks are ignored).
- Worker: lock renewal fails when the token mismatches (stale workers cannot extend TTL).
- Worker: lock renewal success path extends TTL for long batches.
- Worker: lock acquired before any dedupe `SADD`; lock failure does not mutate dedupe.
- Queue: lock contention does not increment attempts.
- Queue: consumer group creation is idempotent (`BUSYGROUP` handled).
- Queue: dedupe TTL (`EXPIRE`) applied as expected.
- Validation: missing `eventId`/`id` returns `400`.
- Methods: non-POST requests return `405`; `OPTIONS` preflight succeeds when enabled.
- Queue: attempts hash cleanup on success (`HDEL`).
- Queue: legacy `id` is normalized to `eventId` when `eventId` is missing.

### Integration
- End-to-end: POST recorder batch with session token and confirm JSONL audit append.
- End-to-end: POST recorder batch for a composite omni/contrast runid with a composite parent and confirm it resolves to the correct child run directory.
- Verify queue backlog is processed when worker starts after a delay.
- Simulate worker crash between append and `XACK` and verify replay does not duplicate outputs (dedupe ledger blocks reapply).
- Verify Caddy strips `/weppcloud` and the microservice sees `/runs/{runid}/{config}/recorder/events`.
- Verify trailing slash redirect behavior.
- Verify trailing slash redirect preserves query parameters when present.
- Verify recorder API does not apply Starlette `redirect_slashes` (no in-app 307/308 on `POST`/`OPTIONS`).
- Verify encoded slashes (`%2F/%5C` and double-encoded variants) are rejected and do not fall through to Flask.
- Verify Redis outage returns 503 with canonical error payload.
- Verify keepalive requests over 64KB return 413 (when `X-Recorder-Keepalive: 1` is set).
- Verify non-keepalive requests over 1MB return 413 with canonical error payload.
- Verify keepalive requests without `X-Recorder-Keepalive: 1` are accepted up to 1MB and emit a warning metric/log.
- Verify retry path: leave a batch pending, run worker reclaim pass (`XAUTOCLAIM`), and confirm poison handling after 5 failures.
- Verify batch failure semantics: a single bad event is skipped while valid events in the same batch are persisted.
- Verify worker startup reclaim path (`XAUTOCLAIM` with `min-idle=0`) drains the PEL immediately after restart.
- Verify `assembler_override` computation works in recorder API when `/wc1` and `/geodata` are mounted (or fails loudly if not).
- Verify backlog counter reconciliation recovers from drift (manual reset path).

### Regression
- Existing recorder tests in `tests/weppcloud/routes/test_recorder_bp.py` remain for Flask route until removed or deprecated.
- JS tests: add a unit test that recorder uses `requestWithSessionToken`, sets `keepalive`, and enforces the keepalive batch cap.
- JS tests: ensure unload flush does not trigger token refresh (cached token only).
- JS tests: verify `X-Recorder-Keepalive: 1` is sent for keepalive flushes.
## Rollout
1. Deploy microservice + worker with no Caddy routing yet (no client change).
2. Add Caddy route with prefix stripping; verify microservice health and logs.
3. Switch JS client to new transport and monitor 502 rate.
4. Keep Flask recorder endpoint present but unreferenced; rollback by removing the Caddy route (no dual writes).
5. Remove the Flask endpoint after one release if stable.

## Risks / Decisions
- Ordering is not enforced; per-run+config locking prevents log interleaving.
- Backpressure: hard cap at `250000` enforced via a backlog counter (`recorder:events:backlog`) updated in Lua on enqueue/dequeue; `XLEN` is informational only.
- Token availability during unload: prefetch and cache session token; unload flush must not trigger refresh; keepalive cap is best-effort and only enforced when `X-Recorder-Keepalive: 1` is present.
- Auth policy: accept `session`/`user`/`service`/`mcp` tokens, require run claims for `service`/`mcp`, require matching `config` claims for `session` + `service`/`mcp`, and require a match when `user` tokens include a `config` claim.
- Service/mcp token issuance must include `config` claims to satisfy the recorder policy.
- Data integrity tradeoff: no duplicates, even if a crash can drop events after dedupe marking.
- Redis 6.2+ is required for `XAUTOCLAIM`.
- Dedupe and locks are scoped to `runid+config`; `eventId` must be unique within a run+config.
- Startup reclaim (`min-idle=0`) is safe under the single-worker assumption; if multi-worker is introduced, gate this behavior or use `min-idle >= lock TTL`.
- If a cached session token expires before unload, keepalive flushes can be dropped; this loss is accepted.
