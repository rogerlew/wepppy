# Close the query-engine run access and filesystem boundary

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, a person can query a public WEPPcloud run anonymously, or a
private run when their existing WEPPcloud identity grants access, without the
query-engine accepting arbitrary filesystem locations. An anonymous or unrelated
person receives a bounded denial before the service opens a catalog, dataset, or
exception log. Existing dashboards continue to call the Starlette query-engine
directly; no Flask data proxy or new identity service is introduced.

The observable proof is an HTTP matrix through the production-equivalent Caddy
route: public read succeeds; private owner read succeeds; anonymous and unrelated
private reads fail; hostile paths fail; denied requests leave no changed catalog
or log artifacts. A controlled wepp1 validation is required before claiming the
finding deployed or resolved.

## Progress

- [x] (2026-11-11 00:59 UTC) Fetch `origin`; record `origin/master` at `ef5b4e289`.
- [x] (2026-11-11 01:03 UTC) Confirm F1 source path and scaffold the package.
- [x] (2026-11-11 01:25 UTC) Prepare exact canonical HTTP contract and cross-contract amendments; review source compatibility with two independent reviewers.
- [x] (2026-11-11 01:26 UTC) Both independent contract reviews passed; retain disposition and reviewed contract digest.
- [x] M0: operator ratified revised contract; standalone checkpoint `2f9401f93`.
- [x] M1: retained original anonymous-private failure; added real resolver/JWT/catalog regression matrix.
- [x] M2: strict checked targets, current authorization and scoped catalog sources implemented; review fixes under validation.
- [ ] M3: deliver the query-engine browser cookie bridge, activation method/CSRF
      posture, exact CORS policy, and direct-browser regressions.
- [ ] M4: complete focused/broad gates and independent correctness, QA, code, and
      security reviews.
- [ ] M5: validate in a production-equivalent environment and perform an
      explicitly authorized containment-safe wepp1 rollout.

- [x] Review fixes: preserve external DEM skip semantics and parent `.nodir`
      links; bound post-admission authorization-backend failures; preserve log
      creation mode under the existing umask.

## Surprises & Discoveries

- M0 review (2026-11-11): `get_wd` performs Omni link fixups and WD-cache writes;
  `prefer_active=False` alone is not side-effect-free. Admission needs a pure
  mode and checked paths shared by every authorization recheck.
- M0 review: normal/direct dashboards do not invoke the existing no-config
  cookie bridge. Parent-path cookies do not reach composite child URLs; all
  run/config query cookies need hashed names and the query prefix. Retain the
  existing four-day lifecycle and test real multi-run header/cookie limits.
- M0 review: PCV-01 explicitly preserves ownerless ordinary results and current
  PortlandGroup catalog grants. Ownerless ordinary is not private-owned state;
  query admission must preserve that distinction without treating DB failure or
  an arbitrary empty directory as ownerless data.
- M0 review: MCP uses the shared resolver with bare IDs; scenario selection can
  follow symlinks before auto-activation; canonical parent-backed data includes
  landuse/soils. These are explicit regression obligations, not unaffected cases.

- Observation: `require_root()` in
  `wepppy/query_engine/app/feature_access.py` authorizes batch and culvert roots
  but returns without a decision for ordinary `/wc1/runs` projects.
  Evidence: every ordinary HTTP handler calls it after `resolve_run_path`, but
  its loop only names `BATCH_RUNNER_ROOT` and `CULVERTS_ROOT`.
- Observation: `resolve_run_path()` treats route text as a possible absolute or
  root-relative filesystem path after `get_wd` fails.
  Evidence: `Path(runid_param).is_absolute()` and `Path("/" + runid_param)`
  branches return any existing directory.
- Observation: direct browser compatibility needs explicit work. The existing
  run-session cookie is HttpOnly and path-scoped under `/weppcloud/runs/...`, so
  browsers do not send it to `/query-engine/runs/...`.
  Evidence: `browse_cookie_path()` and `_set_run_session_jwt_cookie()`.
- Observation: explicit activation is exposed as GET and POST, while normal
  read paths can also auto-create catalog cache artifacts.
  Evidence: route registration in `server.py` and `auto_activate=True` calls.
- Observation: feature-access governance names query-engine as a protected read
  surface. This package must consume that policy, not create a competing one.

- Implementation review: native catalog scans and schema reads precede response
  filtering. Retained sibling-source tests justified a ContextVar scope around
  synchronous catalog/query work, reusing native scans and existing policies.
- Actual Omni links include parent metadata, archived climate/watershed inputs,
  and `wepp/runs`. External DEM links are skipped by the native scanner and must
  remain skipped during pending refresh inventory as well.
- The prior test spy patched an unused server alias; it now wraps the actual
  context resolver and checks populated catalog/log bytes on denial.

## Decision Log

- Decision (2026-11-11): set query-engine Uvicorn H11 incomplete-event buffer to
  131072 bytes (old 16384) in dev/prod only. A real browser retained 100 cookies,
  totaling 63600 bytes, then failed with HTTP2 protocol error; query-engine
  reported an invalid HTTP request. Evidence: `forest_browser_header_failure.txt`
  and `forest_header_failure_service.txt`. Independent security review reproduced
  rejection at 16384, acceptance at 131072 and rejection of an oversized
  incomplete event. This preserves cookie transport with at most 112 KiB extra
  incomplete-event buffer per connection; it is not a total-header limit. Caddy
  limits stay unchanged. Revert restores the known capacity failure.


- Decision (2026-11-11): raise only WEPPcloud Gunicorn request-line cap from
  implicit 4094 to explicit 8190 bytes in dev/prod Compose. Real 100-run browser
  acceptance failed at 5537 bytes before cookie issuance; retained evidence is
  `artifacts/forest_browser_collection_failure.txt`. The accepted contract permits
  a bounded limit expansion after such evidence. Smaller fixture IDs would hide
  the supported collection failure; transport redesign adds unnecessary cost.
  Existing header/body limits, service identities and topology remain unchanged.
  Rollback restores the old cap and the known 100-run URL limitation; validate
  the candidate before any production rollout.


- Decision (2026-11-11, Codex proposal): use the exact new HTTP contract and
  revised decision artifact for ratification. Preserve ownerless/PCV access,
  use all-hashed query-prefix cookies with existing lifetime, and specify the
  cookie activation exception. These correct ambiguities in the initial draft;
  operator ratified these exact choices before checkpoint `2f9401f93`.
- Decision: inspect fetched changes without integrating them. The two commits
  affect declarative DEM and snapshot metadata, not this boundary. Stay on the
  existing branch and preserve unrelated working-tree changes.

- Decision: F1 means the ranked audit's query-engine authorization/path finding,
  tracked here as `SEC-F1`.
  Rationale: it is the audit's first and only Critical finding.
  Date/Author: 2026-11-11, operator request interpreted by Codex.
- Decision: preserve direct browser-to-Starlette queries and reuse existing JWT,
  session-marker, run-ownership, and feature-access decisions.
  Rationale: the nearest WEPPcloud instructions prohibit a Flask query proxy;
  reuse minimizes new security machinery.
  Date/Author: 2026-11-11, Codex planning recommendation.
- Decision: filesystem path text is not a supported HTTP identifier. Resolve a
  parsed run ID only through `get_wd(prefer_active=False)`, then prove the result
  is inside the exact root allowed for that identifier class.
  Rationale: removing only one fallback would leave alternate-path and poisoned
  cache risks; broad root allowlists can still cross tenants.
  Date/Author: 2026-11-11, Codex recommendation, ratified by operator at checkpoint `2f9401f93`.
- Decision: use a separate query-engine-audience token in an HttpOnly cookie
  scoped to the query route. Do not reuse a JavaScript-readable token.
  Rationale: audience and path confinement preserve least privilege without
  breaking direct dashboard calls.
  Date/Author: 2026-11-11, Codex recommendation, ratified by operator at checkpoint `2f9401f93`.

## Outcomes & Retrospective

Contract accepted and committed as `2f9401f93` before source/test changes. Strict
HTTP resolution, current authorization, scoped catalog source checks, browser
cookie bridge, POST activation and exact CORS are implemented. Focused tests and
independent reviews found compatibility defects; fixes and expanded tests are
in progress. Frontend lint/test (124 suites, 1069 tests), stub hygiene and helper
stubtest passed. Broad Python and final focused gates are running. Browser,
100-run cookie capacity and production-equivalent validation remain pending.
No production deployment or incident-resolution claim is made.

## Context and Orientation

Work from `/home/workdir/wepppy`. The production target is wepp1, deployed through
the installed `wctl` preset and `scripts/deploy-production.sh`; do not invent a
registry/Kubernetes path for wepp.cloud. Read the root and nearest `AGENTS.md`
before editing. Preserve unrelated working-tree changes and do not create or
switch branches unless the operator asks.

Caddy forwards public `/query-engine/*` requests to the standalone Starlette app
in `wepppy/query_engine/app/server.py`. `handle_path` removes the external prefix.
The HTTP handlers receive a greedy `{runid:path}` value that normally contains
`<runid>/<config>`. They call
`wepppy/query_engine/app/helpers.py:resolve_run_path`, which first tries
`wepppy.weppcloud.utils.helpers.get_wd` but then accepts filesystem paths.

`get_wd` is the canonical identifier resolver. It rejects slash, backslash, NUL,
dot, and empty components and supports ordinary, legacy, batch, culvert, Omni,
and profile-playback run identifiers described in `docs/composite-runid-slugs.md`.
It can also read a Redis working-directory cache. Treat its result as untrusted
until the identifier-specific root and symlink-resolved containment are proven.

The current `require_root` helper in
`wepppy/query_engine/app/feature_access.py` applies special feature checks only
under batch and culvert roots. It does not authorize ordinary runs. Existing
shared authorization lives in `wepppy/microservices/browse/auth.py` and
`wepppy/microservices/rq_engine/auth.py`; it validates JWTs, revocation, token
class, session markers, ownership, public state, and feature access.

WEPPcloud renders private project pages in
`wepppy/weppcloud/routes/run_0/run_0_bp.py`. Its browse/RQ session token is
HttpOnly and scoped to the `/weppcloud/runs/` route. Query dashboards call
`/query-engine/` directly, so a compatible fix must mint a separately
audience-scoped token cookie for that prefix after the Flask page has already
authorized the run. Public reads do not require token minting.

Catalog activation writes generated cache beneath `_query_engine`. A denial must
happen before `resolve_run_context`, `activate_query_engine`, `visible_entries`,
dataset path resolution, or `_log_exception_details`. MCP routes already have a
separate scoped-token layer; preserve it and test it for non-regression rather
than replacing it with the browser HTTP guard.

## Plan of Work

### Milestone 0: Ratify the contract and optional containment

Review `artifacts/20261110_contract_decision.md` with the operator. Promote the
approved behavior into a new canonical
`docs/schemas/query-engine-http-access-contract.md` and align
`wepppy/query_engine/README.md`, `docs/composite-runid-slugs.md`,
`docs/schemas/weppcloud-session-contract.md`,
`docs/dev-notes/auth-token.spec.md`, and
`docs/schemas/weppcloud-csrf-contract.md` where their current contracts are
affected. State that conformance is pending.

The contract must define the route grammar, valid run classes, public/private
read matrix, token audiences/classes/scopes, cookie name/path/SameSite/HttpOnly
properties, exact CORS origins, status behavior, catalog side effects, explicit
activation method and same-origin/CSRF posture, and MCP non-regression boundary.
Retain current public-run policy and feature entitlements. Do not use this package
to make private projects public or to grant new feature access.

Obtain two independent read-only contract reviews, disposition every finding,
and commit the package decision, canonical amendments, and review disposition as
a standalone ancestor. Record its SHA in this plan and `tracker.md`. No
implementation file may change first. If the operator selects immediate Caddy
containment, use the canonical production deployment path, retain the rendered
config and anonymous/private response evidence, and record an owner/removal gate.

Milestone acceptance: the operator-approved matrix and two reviews exist; the
ancestor commit precedes all implementation edits; any containment is explicit,
bounded, and rollback-safe.

### Milestone 1: Capture the failure class with red tests

Extend `tests/query_engine/test_server_routes.py` and add narrowly named helper
tests as necessary. Tests must exercise every HTTP entry point: run info, schema,
query console, query POST, and explicit activation, with and without trailing
slashes. Test the handler before mocking catalog resolution; otherwise the test
does not prove ordering.

Build independent matrices for request input and stored state. Inputs include an
ordinary ID/config, each supported composite form, bearer and cookie token
classes, absolute and root-relative paths, dot/traversal, percent-encoded
separators, NUL, missing config, extra segments, and symlink escape. States
include absent, present-empty, populated, public, private owner, private unrelated,
supported legacy root, stale/revoked session, poisoned WD cache, and malformed
catalog. The bounded failure-class matrix is
`artifacts/20261110_failure_class_matrix.md`; update dispositions with actual test
names and results.

For denied requests, snapshot catalog and exception-log existence/hashes before
and after. Assert that authorization runs before catalog creation, dataset open,
or log append. Use real temporary directories and real path resolution at the
boundary; mocks may observe downstream non-calls but cannot replace the resolver
or authorization decision being certified.

Milestone acceptance: tests fail on the original implementation for the exact
missing-auth/path reasons, valid-state expectations are explicit, and no case is
called unaffected without direct evidence.

### Milestone 2: Implement strict resolution and authorization

Replace the permissive resolver in
`wepppy/query_engine/app/helpers.py` with a small typed target parser or an
equivalent explicit result containing the canonical `runid`, `config`, resolved
run path, and authorization parent. The route value must be parsed as an
identifier/config pair; it must never be retried as a filesystem path. Use
`get_wd(runid, prefer_active=False)` with an explicit side-effect-free mode;
reject a missing/non-directory result and preserve defaults for other callers.
Keep HTTP grammar separate from MCP bare-ID resolution. Validate body scenario
selection before context preparation and bind all auth rechecks to checked roots.

Validate the resolved path after `Path.resolve()` against the exact approved
root for the identifier class. Ordinary IDs may resolve under the primary,
legacy, or configured playback-run roots according to the canonical contract.
Batch, culvert, profile tmp/fork/archive, simple Omni, and batch Omni forms must
remain inside their documented parent/root. A symlink or poisoned cache that
escapes the authorized root fails. For child datasets, prove they remain within
the authorized run/parent sharing contract; do not use broad `/wc1` membership as
tenant isolation.

Generalize the existing shared run-request authorization only as much as needed
to accept an explicit JWT audience and route behavior while preserving its
current defaults for browse/RQ consumers. The query HTTP layer must request the
query-engine audience, enforce operation scopes from the ratified contract, and
map `BrowseAuthError`/`AuthError` to stable 401/403 responses. Public anonymous
reads follow the existing on-disk public decision. Private access follows current
owner/Admin/Root/service and feature-access policy.

Call target resolution and authorization at the top of every handler, before
context/catalog/dataset/log work. Keep authorization across any async/threadpool
boundary and force-refresh callback so a stale precheck cannot authorize a later
different target. Do not weaken the independently authenticated MCP routes.

Milestone acceptance: all M1 tests pass; owner/public results preserve semantic
content; denied requests have no side effects; supported run forms match the
ratified matrix.

### Milestone 3: Complete the browser and mutation boundary

In every admitted WEPPcloud run-page/direct dashboard/report/viewer response
path, mint a separate existing-lifetime
session token with audience `query-engine` and only the approved read/query
scopes. Reuse the same user/run authorization, `jti`, session marker, revocation,
Secure, SameSite, and HttpOnly behavior. Use hashed cookie names for every run/config and the semicolon-safe
`/query-engine/runs/` path per the revised contract. Validate browser/ingress
cookie capacity for 100-run collections; public/ownerless reads need no mint. Do not
place tokens in HTML, JavaScript, URLs, or logs.

Change the explicit force-activation route and query-console affordance to the
ratified POST behavior. Cookie-authenticated mutation must pass the exact
same-origin/CSRF rule in the amended canonical contract; bearer clients must
present the activation scope. Normal authorized read preparation may create a
catalog only as explicitly allowed by the contract. Ensure GET cannot force a
refresh.

Replace wildcard CORS with the exact configured WEPPcloud origins and required
methods/headers. Test missing, hostile, alternate-port, and allowed Origins.
Browser coverage must load a private project as its owner, observe a successful
dashboard query through Caddy, then prove anonymous and unrelated contexts fail
without redirect loops or token exposure. Exercise public runs separately.

Milestone acceptance: private browser queries work without JavaScript-readable
credentials; cross-origin requests and GET activation fail; valid public and
owner workflows remain familiar.

### Milestone 4: Review and local release gate

Run the focused query-engine and WEPPcloud auth/cookie suites, then the full
Python sanity gate. Run frontend lint/tests if query-console or dashboard
JavaScript changes. Validate the rendered Compose and Caddy configuration. Run
changed-file broad-exception and code-quality observability checks. Update user,
operator, developer, configuration-reference, and query-engine docs in the same
change set.

Obtain distinct correctness/UX, QA, code, and security reviews. The correctness
review owns valid-state noninterference; the security review owns hostile-state
containment and verifies noninterference. Close every medium/high finding. Bind
all evidence to the exact candidate revision and retain failed attempts rather
than overwriting them.

Milestone acceptance: all required gates pass or have explicit unrelated
blockers; no medium/high finding remains; the candidate is deployment-ready but
not yet called deployed.

### Milestone 5: Production-equivalent and wepp1 rollout

Use forest or an equivalent Compose environment with Caddy and production-like
identity, groups, mounts, umask, Redis, PostgreSQL, and secrets. Create or select
controlled public and private fixtures with no sensitive payloads. Verify the
full HTTP matrix and catalog/no-side-effect evidence. Inspect exact artifacts,
not only status codes.

After explicit wepp1 deployment authorization, follow
`scripts/deploy-production.sh` through the installed `wctl` preset. Record the
deployed revision, rendered topology, health, public/owner/private denials,
authorized query content, and log/catalog hashes. Do not probe unrelated runs or
use hostile payloads against live data. If rollback is required, retain Caddy
containment until the prior vulnerable application is no longer publicly
reachable.

Milestone acceptance: the exact candidate is deployed and observed on wepp1,
the controlled matrix passes, rollback is containment-safe, and an owner monitors
health/danger signals for 14 days. Only then may the finding be called deployed;
incident resolution additionally requires the observation/recurrence disposition.

## Concrete Steps

Run commands from `/home/workdir/wepppy`. Before implementation, inspect remote
and local ancestry without integrating automatically:

    git rev-parse HEAD origin/master
    git log --oneline HEAD..origin/master

After the contract files are approved and reviewed, create the standalone
checkpoint using the repository's normal non-interactive Git workflow. Do not
begin source edits until its SHA is recorded here and in `tracker.md`.

During implementation, use these focused gates, updating exact test paths as
new files are added:

    wctl run-pytest tests/query_engine/test_server_routes.py --maxfail=1
    wctl run-pytest tests/microservices/test_browse_auth_routes.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_run_0_nocfg_auth_bridge.py --maxfail=1
    wctl run-pytest tests/query_engine --maxfail=1

If frontend code changes:

    wctl run-npm lint
    wctl run-npm test

Before handoff:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20261110_query_engine_access_boundary

Validate Caddy and Compose using the existing repository/wctl entry points named
by Docker guidance; do not invent ad hoc deployment commands. Record exact
commands and outputs in package artifacts as they are run.

Expected focused behavior includes:

    anonymous + public run       -> contracted 200 read
    owner + private run          -> contracted 200 read/query
    anonymous + private run      -> 401 before filesystem side effects
    unrelated user + private run -> 403 before filesystem side effects
    absolute/root-relative path  -> 400 or 404, never a filesystem lookup result
    GET explicit activation      -> 405
    hostile Origin activation    -> 403

Do not freeze exact status codes until the M0 contract is ratified; once ratified,
replace the alternatives above with the canonical values and exact assertions.

## Validation and Acceptance

Acceptance requires behavior, not implementation shape. Through the real HTTP
stack, compare query records/schema/row counts for the same authorized public and
private fixtures before and after the patch. Confirm the private fixture cannot
be discovered, queried, activated, or logged to by anonymous/unrelated clients.
Confirm hostile route text cannot select `/etc`, `/tmp`, another run, a symlink
escape, or a poisoned Redis WD-cache target.

Parse and hash `_query_engine` outputs for authorized catalog creation. For every
denial, prove those artifacts and `exceptions.log` are absent or byte-identical.
Exercise documented ordinary, legacy, batch, culvert, Omni, and profile forms
under their real authorization/configuration or leave them explicitly unresolved.
Run the MCP suite to prove its independent scoped-token behavior remains intact.

The completion language is strict: source edits are "implemented"; focused local
evidence is "locally validated"; forest/equivalent evidence is "environment
validated"; the exact wepp1 receipt is "deployed"; the observation/recurrence
gate is "incident resolved". Never collapse these states.

## Idempotence and Recovery

Tests use temporary roots and disposable identities and must be repeatable. Token
minting may create Redis session markers with bounded TTL; test fixtures must use
isolated keys and clean them. Do not mutate existing production runs for
validation. Catalog comparisons use controlled fixtures and retain before/after
hashes.

An application rollback must not reopen the public vulnerability. Keep any
temporary Caddy containment until a safe application revision is active and the
matrix passes. If the query-scoped cookie causes compatibility failures, disable
only its mint/consumption path while containment remains; do not restore
unauthorized private reads. Record the failure and reassess the whole boundary
before layering another workaround.

## Artifacts and Notes

Retain the contract decision/reviews, failure-class matrix, failed and passing
test transcripts, controlled HTTP response matrix, catalog/log hash manifests,
rendered Compose/Caddy configuration, exact revisions, deployment receipt,
rollback evidence, and independent reviews under this package. Redact tokens,
cookies, private run identifiers, query records, and secrets.

## Interfaces and Dependencies

Prefer these existing interfaces:

- `wepppy.weppcloud.utils.helpers.get_wd(runid, prefer_active=False)` for
  identifier resolution after strict route parsing.
- `wepppy.microservices.browse.auth.authorize_run_request` and
  `wepppy.microservices.rq_engine.auth.authorize_run_access` for run decisions,
  generalized only with an explicit audience/operation contract.
- `wepppy.weppcloud.utils.auth_tokens.issue_token` and `decode_token` for the
  existing JWT protocol.
- `wepppy.weppcloud.utils.browse_cookie` for semicolon-safe cookie naming,
  extended with a query-engine path helper rather than duplicating hashing.
- `wepppy.query_engine.context.resolve_run_context` only after authorization.

No new runtime dependency is allowed. If evidence shows these interfaces cannot
represent an approved valid state, stop, update the complexity decision and
operator review, and record the smallest justified expansion plus its rollback
cost.

Revision note, 2026-11-11: created after the operator requested a GitHub fetch and
work-package scaffold for F1. Source diagnosis is complete; contract approval,
implementation, deployment, and incident resolution remain pending.

Revision note, 2026-11-11 01:25 UTC: M0 execution exposed resolver side effects,
Omni cookie transport, direct-entry minting and PCV/ownerless compatibility gaps.
The revised contract resolves these explicitly; runtime work awaits its exact
ratification and reviewed checkpoint ancestor. No implementation or deployment
evidence is claimed.

M0 validation, 2026-11-11 01:29 UTC: package doc lint (8 Markdown files)
and all eight affected canonical/reference documents passed with zero errors
or warnings; `git diff --check` passed. Spelling preview found only existing
CSRF-contract differences, left untouched. Evidence: `artifacts/20261110_m0_doc_validation.txt`
(package-relative). No runtime tests were run because source/tests are unchanged.

Operator ratification, 2026-11-11 UTC: "I approve the revised contract. please
commit and proceed". Exact contract approved; checkpoint commit follows before
implementation. Production deployment is not authorized.

M0 complete: accepted standalone checkpoint ancestor `2f9401f93` committed
2026-11-11 UTC before implementation/test edits. M1 execution begins.
