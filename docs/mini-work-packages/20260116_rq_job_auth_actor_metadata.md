# Mini Work Package: RQ job auth actor metadata

**Status:** Draft
**Last Updated:** 2026-01-16
**Primary Areas:** `wepppy/microservices/rq_engine/auth.py`, `wepppy/rq/job_info.py`, `wepppy/rq/rq_worker.py`, `wepppy/profile_coverage/runtime.py`, `tools/wctl2/commands/rq.py`, `docs/dev-notes/auth-token.spec.md`, `docs/schemas/rq-response-contract.md`

## Objective
Add a minimal, safe auth actor footprint to RQ jobs so jobinfo/jobstatus and `wctl2 rq-info` can show who or what enqueued work (user id, session id, or service id + groups) without leaking JWTs or email.

## Scope
### Included
- Define an `auth_actor` schema stored in `job.meta`.
- Capture `auth_actor` during rq-engine JWT validation and inject into enqueued jobs via an RQ enqueue hook.
- Propagate `auth_actor` to child jobs enqueued from workers.
- Expose `auth_actor` in jobinfo payloads (and optionally jobstatus if needed).
- Document the new optional payload field in `docs/schemas/rq-response-contract.md`.
- Update `wctl2 rq-info` to surface runid/description/auth actor (likely via rq-engine jobinfo or a Redis-backed detail view).

### Out of scope
- Changing JWT issuance or scope policy.
- Gating jobinfo/jobstatus behind auth (still unauthenticated for now).
- Storing JWTs, email addresses, or raw Authorization headers.

## Auth actor schema (proposed)
Stored in `job.meta["auth_actor"]` as a small dict:
```json
{
  "token_class": "user|session|service|mcp",
  "user_id": 123,
  "session_id": "sess-abc",
  "sub": "service-name",
  "service_groups": ["culverts", "batch"]
}
```
Rules:
- `user_id` only for `token_class=user` (parse `sub` as int; omit if non-numeric).
- `session_id` only for `token_class=session` (use `session_id` claim or `sub`).
- `sub` only for non-user tokens (service/mcp), avoid email.
- `service_groups` only for `token_class=service`; normalize to list of strings.
- Never store JWTs, headers, or email claims.

## Design notes
- Use a context var to hold the active `auth_actor` for the request lifecycle.
- Install a Queue enqueue hook (similar to `wepppy/profile_coverage/runtime.py`) to merge `auth_actor` into `job.meta` on enqueue.
- In worker processes, read `job.meta["auth_actor"]` at job start and set the context var so nested enqueues inherit the actor.
- Treat `auth_actor` as optional; jobs enqueued outside rq-engine simply omit it.

## Implementation outline
1. **Auth actor module**
   - New helper module (e.g., `wepppy/rq/auth_actor.py`) with:
     - `current_auth_actor`, `set_auth_actor`, `reset_auth_actor`.
     - `install_rq_auth_actor_hook()` to wrap `Queue.enqueue`/`enqueue_call`.
2. **rq-engine integration**
   - In `require_jwt`, derive the sanitized `auth_actor` and set context.
   - Install hook once at rq-engine startup (`wepppy/microservices/rq_engine/__init__.py`).
3. **Worker propagation**
   - In `WepppyRqWorker.perform_job`, set context from `job.meta["auth_actor"]` before running the job.
   - Ensure the enqueue hook is installed in worker processes so child jobs get tagged.
4. **Jobinfo payloads**
   - Add `auth_actor` to `recursive_get_job_details` output; keep optional.
   - If needed for `wctl2 rq-info`, add `auth_actor` to `get_wepppy_rq_job_status` or a new summary endpoint.
5. **CLI surface**
   - Extend `wctl2 rq-info` to show runid + description + auth_actor. Likely options:
     - `wctl rq-info --detail` calls `/rq-engine/api/jobinfo/<id>` per job id.
     - or direct Redis inspection with `rq.job.Job.fetch` inside the worker container.
6. **Docs + tests**
   - Document `auth_actor` as an optional field in `docs/schemas/rq-response-contract.md`.
   - Note the schema in `docs/dev-notes/auth-token.spec.md` (token_class mapping).
   - Add unit/microservice tests for jobinfo payloads including `auth_actor`.

## Risks and mitigations
- **Leakage risk:** ensure auth actor is sanitized (no JWT, no email). Keep fields minimal.
- **Hook collisions:** multiple Queue wrappers (profile coverage + auth actor). Use idempotent flags and wrapper composition.
- **Missing actor:** jobs enqueued outside rq-engine remain untagged; wctl should handle nulls.
- **Meta size:** keep payload short; avoid large lists.

## Success criteria
- `job.meta["auth_actor"]` appears on rq-engine enqueued jobs with correct token_class mapping.
- Child jobs enqueued within workers inherit the same auth_actor.
- `/rq-engine/api/jobinfo/<id>` returns auth_actor when present, omitted otherwise.
- `wctl rq-info` can show runid, description, and actor at a glance.
- No JWTs or emails appear in jobinfo/jobstatus outputs.

## Open questions
- Should `auth_actor.sub` be retained for user tokens when `sub` is non-numeric?
- Should jobstatus also expose `auth_actor` or only jobinfo?
- Should we add a dedicated rq-engine summary endpoint for `wctl` instead of scraping jobinfo?

## References
- `docs/dev-notes/auth-token.spec.md`
- `docs/schemas/rq-response-contract.md`
- `wepppy/microservices/rq_engine/auth.py`
- `wepppy/rq/job_info.py`
- `wepppy/rq/rq_worker.py`
- `wepppy/profile_coverage/runtime.py`
- `tools/wctl2/commands/rq.py`
