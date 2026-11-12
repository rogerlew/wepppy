# Close F7 and assemble F1-F7 pre-deployment readiness

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current. At every
stopping point, update this plan and
`docs/work-packages/20261111_test_support_production_guardrails/tracker.md`.

## Purpose / Big Picture

After this work, WEPPcloud test-support routes cannot appear in a production
runtime because a missing deployment profile means production, production
refuses enabled test support, and the production route inventory contains no
`/tests/api/*` entries. In explicitly configured development or test runtimes,
authorized agents can still provision and clean up disposable runs through
`wctl run-playwright` without logging in, copying a token, managing cookies, or
maintaining smoke markers.

This work is also the final pre-deployment coordination point for audit findings
F1 through F7. A human can inspect one readiness matrix and determine the exact
candidate revision, the evidence grade of each finding, any unresolved item,
and the checks that a separately authorized deployment must execute. This plan
does not deploy to forest, forest1, wepp1, wepp2, wepp3, or openwepp.org.

## Progress

- [x] (2026-11-12 01:01 UTC) Confirm the F7 source, configuration, Compose,
      wctl, Playwright, and F1-F6 evidence boundaries.
- [x] (2026-11-12 01:01 UTC) Record the operator's production-default profile,
      low-friction agent auth, no-marker, and F1-F7 wrap-up decisions.
- [x] (2026-11-12 01:01 UTC) Scaffold package, tracker, contract decision,
      failure-class matrix, readiness matrix, deployment plan, and reviews.
- [x] (2026-11-12 01:15 UTC) Pass scoped markdown lint for all package files,
      `AGENTS.md`, and `PROJECT_TRACKER.md`; pass `git diff --check` and the
      root AGENTS size gate.
- [x] (2026-11-12 UTC) M0: promote and ratify the canonical profile, test-support JWT, response,
      and CSRF contract; obtain two independent reviews; commit the standalone
      checkpoint ancestor.
- [x] (2026-11-12 UTC) M1: implement fail-closed configuration and route registration.
- [x] (2026-11-12 UTC) M2: implement scoped existing-JWT authentication with no-side-effect
      negative coverage and no smoke-marker state.
- [x] (2026-11-12 UTC) M3: make wctl/Playwright token handling automatic, narrow, and
      non-retaining; update all consumers and docs.
- [ ] M4: focused configuration/route/CLI/Compose gates pass; actual production
      URL map passes. Unmocked create/load succeeds, but NFS delete leaves a
      directory despite 200. Automatic browser lifecycle/retention remains open.
- [x] (2026-11-12 UTC) Broad local Python sanity: 13,721 passed, 437 skipped,
      exit 0 in 1:04:40. Shared-worktree receipt predates final refinements;
      does not satisfy the frozen-candidate M6 gate.
- [ ] M5: independent correctness/QA/security source reviews approved after
      fixes; release hold remains for M4 cleanup and workflow evidence.
- [ ] M6: after F6 M4, reconcile exact F1-F7 evidence and pass one combined full
      Python/frontend regression gate on the exact candidate.
- [ ] M7: finalize the non-executed deployment-validation plan, update the audit
      board and project tracker to evidence-supported readiness, and close.

## Surprises & Discoveries

- Actual forest `/wc1` is NFS4: deletion can return 200 while open-file cleanup
  yields EBUSY and the run directory remains. Existing local-filesystem tests
  did not establish mount parity. Direct readback prevented false acceptance.
- Ambient proxies affect both urllib and modern Node HTTP global agents; both
  were explicitly isolated. Node TLS verification is explicitly required even
  when its ambient insecure override is set. Real endpoint tests cover both.
- The running container predates profile configuration. Validation used an
  explicit process-local profile through wctl exec, without a service restart.

- Observation: the current route registration is already conditional on
  `TEST_SUPPORT_ENABLED`, so the defect is not a default-on route. The missing
  controls are a production-profile invariant and authentication after the flag
  is enabled.
  Evidence: `wepppy/weppcloud/_blueprints_context.py` and
  `wepppy/weppcloud/routes/test_bp.py`.

- Observation: production Compose does not explicitly pass
  `TEST_SUPPORT_ENABLED`, but all WEPPcloud services consume a generated env
  file. The Python default is safe, yet a host override remains capable of
  changing behavior unless production pins a literal and startup checks the
  profile.
  Evidence: `docker/docker-compose.prod.yml` service `env_file` and
  `wepppy/weppcloud/configuration.py`.

- Observation: the existing WEPP_AUTH implementation and
  `wctl issue-auth-token` command already provide file-backed signing,
  audience/scope claims, expiration, and container-local minting. A new static
  test token would duplicate an owned mechanism and add secret provisioning.
  Evidence: `wepppy/weppcloud/utils/auth_tokens.py`,
  `wepppy/weppcloud/_scripts/issue_auth_token.py`, and
  `tools/wctl2/commands/auth.py`.

- Observation: the normal run-delete endpoint requires an authenticated owner
  and enqueues asynchronous cleanup, while test support performs immediate
  deterministic cleanup. Reusing normal deletion would add login/CSRF/ownership
  setup and change smoke semantics. The operator instead accepts an
  environment-wide non-production test capability.
  Evidence: `wepppy/weppcloud/routes/nodb_api/project_bp.py` and the recorded
  no-marker decision.

- Observation: F1-F5 have implementation evidence at different grades and F6
  is still active. A single word such as "complete" would erase material
  distinctions between locally validated, forest validated, rollout pending,
  and deployed.
  Evidence: `artifacts/20261111_f1_f7_readiness_matrix.md`.

## Decision Log

- Decision (2026-11-12, Codex): retain NFS cleanup as an M4 blocker, with no
  general deletion lifecycle redesign. Rationale: M2 explicitly excludes that
  expansion; cached-instance cleanup precedent does not cover all directly
  constructed initialization objects. Any follow-up must prove handle lifecycle.
- Decision (2026-11-12, Codex): no parameterization ADR is required: the fixed
  3600-second lifetime reuses WEPP_AUTH's existing default, adds no configurable
  threshold and changes no scientific/model parameterization.

- Decision: `WEPPCLOUD_DEPLOYMENT_PROFILE` recognizes `production`,
  `development`, and `test`; absence means `production`; unknown values fail
  startup.
  Rationale: a fail-closed default satisfies the operator decision while named
  non-production values preserve intentional dev and smoke workflows.
  Date/Author: 2026-11-12, Roger decision recorded and completed by Codex.

- Decision: production Compose passes literal `production` and literal
  `TEST_SUPPORT_ENABLED=false`. Development Compose passes literal/default
  `development`; a controlled test deployment must pass `test` explicitly.
  Rationale: the runtime default protects raw starts while rendered Compose
  remains observable and resists ordinary env-file drift.
  Date/Author: 2026-11-12, Codex.

- Decision: use a short-lived WEPP_AUTH token with audience
  `weppcloud-test-support` and scope `test:support` rather than a new static
  secret or browser session.
  Rationale: existing issuer/validator behavior is already owned and agents can
  mint through wctl without password, cookie, or CSRF ceremony.
  Date/Author: 2026-11-12, Codex implementing Roger's low-friction requirement.

- Decision: bearer-only test-support views are CSRF-exempt, but a cookie/session
  without the bearer grants no authority.
  Rationale: CSRF protects ambient browser credentials; the exact Authorization
  header is non-ambient and must be checked before every side effect.
  Date/Author: 2026-11-12, Codex; pending M0 contract ratification.

- Decision: do not create smoke markers or a cleanup registry. A valid support
  token authorizes create/delete across its development or test environment.
  Rationale: the operator rejected marker management; the issuer is available
  only to authorized host/container agents, and production registration is
  independently prohibited.
  Date/Author: 2026-11-12, Roger; recorded by Codex.

- Decision: package closure means pre-deployment readiness, not production
  deployment or incident resolution. F6 is required through M4, not its
  separately authorized M5 rollout.
  Rationale: all seven remediations must be compatible and reviewed before a
  combined deployment can be planned, while production authority remains a
  separate operator decision.
  Date/Author: 2026-11-12, Roger direction interpreted and recorded by Codex.

- Decision: F8 remains separate.
  Rationale: port publication has different source, validation, rollback, and
  acceptance boundaries. Sharing a future deploy window does not justify
  coupling implementation packages.
  Date/Author: 2026-11-12, Codex.

## Outcomes & Retrospective

M0-M3 are implemented after the reviewed contract ancestor. Production Compose
and the actual production app (484 total rules) expose no support routes.
Focused auth/CSRF/side-effect and CLI tests pass; frontend gates pass. Independent
source reviews closed all changed-code medium/high findings.

Broad local Python sanity passed (13,721 passed, 437 skipped). It used the shared
working tree and began before final refinements, so a fresh combined gate after
F6 M4 and candidate freeze remains required. F6's tracker still reports M1 in
progress with evaluator/deploy-hook and CI prerequisites incomplete.

M4 remains open: actual create/load passed, denied delete preserved the run, but
valid delete returned 200 with a remaining NFS directory. Scoped recovery after
process exit removed identified fixtures and verified absence. The plan excludes
general deletion-worker redesign; no passing runtime cleanup claim is made.
Automatic wrapper/browser artifact scanning remains open; the forest service was
not restarted. F6 M4 is still absent, blocking M6/M7 and package closure.
See `artifacts/20261112_validation.md` for commands, outcomes and limitations.

## Context and Orientation

The WEPPcloud Flask application loads environment configuration in
`wepppy/weppcloud/configuration.py`, then registers blueprints through
`wepppy/weppcloud/_blueprints_context.py`. A blueprint is a Flask route group.
The optional `test_bp` group lives in
`wepppy/weppcloud/routes/test_bp.py` under `/tests/api`. It currently exposes a
ping, a run-creation mutation, and immediate run deletion. `_require_enabled()`
checks only the boolean feature flag. It does not authenticate the request.

`create_run_endpoint()` constructs a normal run directory, initializes `Ron`
state, and returns a run URL. `delete_run_endpoint()` validates the run ID
through `get_wd()` and recursively removes the resolved directory. `get_wd()`
blocks separators, NUL, dot traversal, and malformed grouped identifiers, but
path validation is not authorization. Run IDs are identifiers, not secrets.

`wepppy/weppcloud/utils/auth_tokens.py` signs and validates WEPP_AUTH HMAC JWTs
using file-backed configuration already mounted into WEPPcloud. A JWT is a
signed short-lived claim set. This package uses one audience, identifying the
test-support service, and one scope, identifying the allowed capability.
`wctl issue-auth-token` already executes the token issuer inside the WEPPcloud
container. `tools/wctl2/commands/playwright.py` implements the canonical smoke
wrapper and currently pings the support endpoint anonymously before launching
Playwright.

Six smoke specifications directly create and delete runs. They live under
`wepppy/weppcloud/static-src/tests/smoke/`. A shared helper must add the bearer
only to requests for `/tests/api/*`; a Playwright-wide extra header would leak
the token to unrelated application requests and is prohibited.

Production WEPPcloud uses `docker/docker-compose.prod.yml` plus a host override
selected by installed wctl. Development uses `docker/docker-compose.dev.yml`.
For `wepp.cloud`, `scripts/deploy-production.sh` is the only canonical deployment
entry point. This package may inspect and plan around that script but may not
execute it.

The F1-F7 release-readiness owners are:

- F1: `docs/work-packages/20261110_query_engine_access_boundary/`.
- F2: `docs/work-packages/20261110_pickle_artifact_restriction/`.
- F3: `docs/work-packages/20261110_browse_listing_output_safety/`.
- F4: `docs/work-packages/20261111_status_preflight_websocket_authorization/`.
- F5: `docs/work-packages/20261111_safe_traceback_sanitization/`.
- F6: `docs/work-packages/20261110_wepp1_dependency_security_gate/`.
- F7: this package.

Closed packages are historical evidence, not mutable authority. Durable F7
rules must live in a new canonical
`docs/schemas/weppcloud-test-support-contract.md` plus the affected runtime and
CSRF contracts. The roll-up links evidence; it does not edit older packages to
make their status appear stronger.

Starting implementation revision:
`cfa1fc6e79ad1db643bd70c95bc8d44dc7083367`. The working tree already contains
unrelated controller-contract work and an ignored generated docs index. Preserve
all unrelated changes and never include the generated index in this package.

## Plan of Work

### Milestone 0: Ratify the durable contract before code

Create `docs/schemas/weppcloud-test-support-contract.md`. State the recognized
profile values, default-production rule, unknown-value failure, production
startup rejection, route registration matrix, token audience/scope/lifetime,
response statuses, CSRF exemption rationale, environment-wide non-production
delete authority, token non-retention, and exact no-marker decision. Amend
`docs/infrastructure/weppcloud-web-runtime-contract.md` with startup invariants
and `docs/schemas/weppcloud-csrf-contract.md` with the bounded bearer-only
exemption. Update `artifacts/20261111_contract_decision.md` with exact proposed
text and compatibility effects.

Obtain two independent read-only reviews covering authority, compatibility,
security, low-friction agent use, and regression evidence. Disposition every
finding. Commit the package checkpoint, canonical contract changes, and review
record as a standalone ancestor. Do not edit implementation files before this
commit exists. Record its full revision in this plan and the tracker.

Milestone acceptance is a clean, review-approved contract ancestor whose diff
contains no implementation changes and whose canonical text is sufficient to
derive every row in the valid-state matrix.

### Milestone 1: Make runtime configuration fail closed

In `wepppy/weppcloud/configuration.py`, parse
`WEPPCLOUD_DEPLOYMENT_PROFILE` as a trimmed, case-normalized enum. Missing or
empty input resolves to `production`; an unknown non-empty value raises an
actionable configuration exception. Preserve the existing false default for
`TEST_SUPPORT_ENABLED`. If test support is true under production, raise before
secret-dependent service startup and before blueprint registration.

In `wepppy/weppcloud/_blueprints_context.py`, retain defense in depth: register
`test_bp` only for `development` or `test` with the flag enabled. Do not rely
solely on the earlier configuration exception. Production must have no rules to
dispatch, rather than registered rules that return a denial.

In development Compose, set the development profile explicitly. In production
Compose, set literal production and literal false test support at the
WEPPcloud-service environment boundary so env-file contents cannot change the
effective values. Verify host overrides do not replace these literals. The
legacy HPC Compose target must be inventoried and explicitly dispositioned; do
not silently extend unsupported behavior.

Add configuration and registration tests for every valid-state matrix row.
Use an actual Flask URL map for route absence. A mocked registration predicate
alone is not acceptance evidence.

### Milestone 2: Require the existing scoped bearer

In `wepppy/weppcloud/routes/test_bp.py`, add a small helper that extracts the
standard Authorization bearer, calls `auth_tokens.decode_token()` with audience
`weppcloud-test-support`, and requires scope `test:support`. Reuse existing
scope parsing or promote a shared helper only if current code already exposes
one appropriate to Flask routes. Do not add a second JWT implementation or
log raw tokens/claims.

Return 401 for missing, malformed, invalid, expired, or wrong-audience tokens.
Return 403 for a valid token lacking `test:support`. Keep production absence as
404 because no route is registered. Apply the authentication helper before
payload parsing, run resolution, directory creation, or deletion. Add narrow
audit logs that record outcome and route without bearer material or private
payloads.

Make the three bearer-only views explicitly CSRF-exempt through the existing
Flask CSRF integration. Prove a session cookie without the bearer provides no
authority. Do not add login, Root-role, marker, registry, or ordinary ownership
checks. Preserve the current create/delete results for a valid credential, but
replace silent cleanup success evidence with direct path-absence validation in
tests. Do not widen this package into a general redesign of `shutil.rmtree` or
the run deletion worker.

### Milestone 3: Remove authentication ceremony from agent smoke workflows

Refactor the existing wctl auth execution boundary only as much as needed to let
`tools/wctl2/commands/playwright.py` mint a one-hour token inside the running
WEPPcloud container without echoing its value. The command itself may appear in
debug logs because it contains no token; captured stdout must not. Mint subject
`wctl-playwright`, audience `weppcloud-test-support`, scope `test:support`, and
an exact bounded lifetime. If minting fails, exit before ping or npm with an
actionable message. Never fall back to anonymous requests.

Pass the token to the Playwright child only through a dedicated environment
value. Do not put it in argv, a URL, a report, a profile YAML file, or a tracked
artifact. Change `_ping_test_support()` to attach the bearer and keep its
errors token-free.

Under `wepppy/weppcloud/static-src/tests/smoke/`, add one shared support-request
helper that reads the transient environment value and supplies Authorization
only for ping/create/delete. Update every direct consumer found by the failure
matrix. Do not configure a context-wide header. Ensure cleanup failures remain
visible but redact credentials.

Update `tools/wctl2/docs/playwright.SPEC.md`, `wctl/README.md`,
`tests/README.smoke_tests.md`, the static-src README, the smoke `AGENTS.md`,
`docs/configuration-reference.md`, `wepppy/weppcloud/README.md`, and
`docker/README.md`. Remove instructions that tell an agent merely to set the
boolean flag without naming the profile and bearer workflow.

### Milestone 4: Focused and unmocked F7 acceptance

Run configuration, route, CSRF, wctl, Compose, and Playwright unit gates. Render
both dev and production Compose using the repository-supported wrapper. Inspect
the production WEPPcloud environment and actual URL map; retain only nonsecret
configuration names/values. Attempting an env-file override must not make the
route appear.

Start or reuse an explicitly authorized non-production local stack with
development/test profile and test support enabled. Use `wctl run-playwright` to
mint/inject the credential, create a disposable run, load the returned page,
and delete it. Read back that the run directory is absent. Exercise missing and
bad credentials and prove no directory was created or deleted. Scan command
output, logs, Playwright reports, URLs, and retained artifacts for the exact
minted token while it is still available in memory; persist only the boolean
result and sanitized metadata.

Do not deploy to forest or any production host under this milestone. If a local
stack cannot provide the required service/mount identity, record the gap and
leave environment validation for the separately authorized deployment plan.

### Milestone 5: Independent closeout reviews

Complete `artifacts/20261111_correctness_review.md`,
`artifacts/20261111_qa_review.md`, and
`artifacts/20261111_security_review.md`. Review profile absence, disabled,
enabled, unknown, valid/invalid token, mint failure, existing smoke, and hostile
states separately. Confirm that production route absence and non-production
agent usability both hold. An auth denial without a side-effect assertion is
not enough.

The security reviewer must explicitly disposition the residual authority that a
valid test-support bearer can delete any resolvable run in its non-production
environment. Accepted risk requires the reviewer recommendation and package
owner acknowledgment. No medium/high review finding may remain open.

### Milestone 6: Assemble the exact F1-F7 candidate

Wait for F6 to reach M4. Do not treat an in-progress scan, partial test run, or
M0 policy checkpoint as F6 acceptance. Update
`artifacts/20261111_f1_f7_readiness_matrix.md` with the full candidate revision,
ancestor checks, exact owning-package receipts, evidence grades, unresolved
rollout work, and review verdicts. Reopen readiness if any owner reports a newer
medium/high finding.

Run each finding's focused owner gate against the combined candidate or record
an exact superseding receipt from that same candidate. Then run one unsegmented
full Python suite, npm lint, and full npm tests. Run the status2/preflight2 Go
gates and F6 exact-image/advisory gate required by their current packages.
Partial or sharded runs may diagnose failures but do not replace the requested
combined broad receipts.

This milestone may repair only confirmed integration regressions within the
already authorized F1-F7 boundaries. A repair owned by another package must be
recorded there and reviewed at the correct boundary. Do not hide a blocker by
editing an old package's status text.

### Milestone 7: Finalize deployment validation without deploying

Complete `artifacts/20261111_deployment_validation_plan.md` for the exact
candidate. Re-read `scripts/deploy-production.sh`, the installed wctl preset
contract, production Compose/host overrides, and current F1-F7 artifacts. Name
which services and images on wepp1 and wepp2 consume each change. Plan a forest
or production-equivalent rehearsal, pre-deploy route/config/image gates,
service-safe activation, post-deploy F1-F7 checks, rollback triggers, evidence
retention, and cleanup.

Production checks must distinguish read-only observations from controlled
mutations. A future operator must separately authorize any disposable run,
Bootstrap push, hostile filename, synthetic traceback canary, service restart,
or image activation. The plan may not rely on testing dangerous payloads against
live user data. It must use `scripts/deploy-production.sh` and the correct
installed wctl preset; it must not invent a registry or Kubernetes flow for
wepp.cloud.

Obtain independent operations and security review of the plan. Update the
gitignored audit board and `PROJECT_TRACKER.md` to state the exact readiness
grade. Close this package only when F1-F7 are implementation/review ready and
the deploy plan is review-ready. Move this ExecPlan to `prompts/completed/` with
an outcome summary. Do not execute the plan without new operator authority.

## Concrete Steps

All commands run from `/home/workdir/wepppy` unless a command says otherwise.
Before each milestone, inspect status and preserve unrelated work:

    git status --short --branch
    git diff -- docs/work-packages/20261111_test_support_production_guardrails

For M0, inspect the source and canonical documents before editing:

    rg -n "TEST_SUPPORT_ENABLED|test_bp|WTF_CSRF" wepppy/weppcloud docker docs tests tools/wctl2
    sed -n '1,240p' docs/infrastructure/weppcloud-web-runtime-contract.md
    sed -n '1,240p' docs/schemas/weppcloud-csrf-contract.md

After M0 review, commit only the checkpoint files. Record the resulting full
hash. Do not use a broad `git add .` in the dirty worktree.

During M1-M3, iterate with:

    wctl run-pytest tests/weppcloud/test_configuration.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_test_bp.py tests/weppcloud/routes/test_blueprint_registration.py --maxfail=1
    PYTHONPATH=/workdir/wepppy pytest tools/wctl2/tests/test_playwright_command.py
    wctl run-npm lint

Render effective configuration through the active wrapper rather than raw
guessed Compose commands:

    wctl docker compose config --format json

Record only the test-support/profile fields and route names. Never retain JWTs
or unrelated environment values.

Run the final combined gates after F6 M4 and exact-candidate freeze:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

Run the current status2/preflight2 and F6 gates named by their owning trackers;
do not copy stale commands into this plan. Record exact command, revision, exit
status, pass/skip counts, and elapsed time in a validation artifact.

Validate documentation after prose changes:

    wctl doc-lint --path docs/work-packages/20261111_test_support_production_guardrails
    wctl doc-lint --path docs/schemas/weppcloud-test-support-contract.md

Preview spelling normalization for each changed prose file and apply only safe
prose-only changes:

    diff -u FILE <(uk2us FILE)

## Validation and Acceptance

F7 is locally accepted when an actual configured Flask app shows no test routes
under the default/production profile; production plus an enabled flag refuses
startup; an explicit development/test profile registers the routes only when
enabled; every request requires an exact unexpired audience/scope token; and the
canonical wctl smoke wrapper completes create/load/delete without manual auth or
token retention.

Negative tests must observe side effects, not only status codes. Before each
denied create, record the bounded run-root contents and assert no new directory.
Before each denied delete, create a disposable fixture and assert it remains.
For valid delete, assert the intended path is absent. Never aim a deletion test
at an existing retained run.

Production configuration acceptance requires both rendered values and Flask
route inventory. Expected production behavior is no matching route, not a
registered route returning 401/403. Expected non-production behavior is 401 for
missing/invalid credentials, 403 for a valid token missing scope, and the
existing success status/payload for a valid credential.

Combined F1-F7 acceptance requires every row in the readiness matrix to name an
exact revision and accepted owner evidence; no unresolved medium/high review
finding; F6 M4 acceptance; focused gates; one exact full Python pass; npm lint;
full npm tests; and a reviewed deployment plan. Do not call findings deployed,
repaired in production, or incident-resolved.

## Idempotence and Recovery

Configuration and route changes are repeatable. A failed development smoke run
may leave a disposable run; record its ID without sensitive content and clean it
through the authenticated support endpoint or existing authorized operator
workflow. Never broaden deletion to recover an unknown path.

If production configuration rejects startup during a future deployment, the
deployment preflight should detect that before service replacement. Recovery is
to correct the nonsecret profile/flag configuration and rerender, not to weaken
the guard. The future deploy plan must name the known-good image and service
mapping before activation.

If token minting fails, stop before ping and Playwright. Preserve the actionable
error but no token stdout. Do not use a static development token or anonymous
fallback.

If a combined gate fails in an unrelated dirty file, reproduce against the exact
candidate and baseline, retain the evidence, and assign ownership. Do not reset,
overwrite, or commit unrelated user work.

## Artifacts and Notes

- `artifacts/20261111_contract_decision.md`: M0 normative delta and reviews.
- `artifacts/20261111_failure_class_matrix.md`: consumers and deployment
  variants.
- `artifacts/20261111_correctness_review.md`: valid states and user errors.
- `artifacts/20261111_qa_review.md`: maintainability and test-quality gate.
- `artifacts/20261111_security_review.md`: auth/secrets/CSRF/deletion review.
- `artifacts/20261111_f1_f7_readiness_matrix.md`: exact combined evidence.
- `artifacts/20261111_deployment_validation_plan.md`: reviewed plan, never an
  execution receipt.

Retained validation output must exclude raw JWTs, Authorization headers,
credentials, private run payloads, production run identifiers, and unredacted
environment dumps. Store concise hashes, counts, route names, image IDs, and
sanitized assertions.

## Interfaces and Dependencies

At M0, the canonical contract must define these stable configuration values:

    WEPPCLOUD_DEPLOYMENT_PROFILE = production | development | test
    TEST_SUPPORT_ENABLED = boolean, default false
    TEST_SUPPORT_AUDIENCE = weppcloud-test-support (fixed contract constant)
    TEST_SUPPORT_SCOPE = test:support (fixed contract constant)

Do not add `TEST_SUPPORT_TOKEN` or `TEST_SUPPORT_TOKEN_FILE`. Signing and
validation use the existing `WEPP_AUTH_JWT_*` secret-file configuration.

`configuration.config_app(app)` must write one normalized profile into
`app.config` and raise a narrow configuration error for unknown values or
production plus enabled support. The exact exception type and message become
part of the M0 startup contract and focused tests.

`test_bp` must expose the same route paths and successful payload shapes. A
private helper must return validated claims or raise/return the contracted
401/403 response before any side effect. Scope parsing must match the existing
WEPP_AUTH separator behavior.

`wctl run-playwright` must acquire a token internally when it will call support
routes, pass it only to `_ping_test_support` and the Playwright child, and remove
it from any retained diagnostic representation. If `--no-create-run` still
performs ping under the current contract, M0 must decide whether authenticated
ping remains necessary; do not infer a behavior change from implementation.

The implementation may use only Flask, Flask-WTF, existing WEPP_AUTH utilities,
existing wctl helpers, and existing Playwright infrastructure. No external
dependency evaluation is necessary unless implementation proves one is
unavoidable, in which case stop and apply the repository dependency gate before
adding it.

## Revision Note

Initial scaffold created 2026-11-12 01:01 UTC to capture the operator's
production-default profile, low-friction agent authentication, no-marker, and
F1-F7 pre-deployment wrap-up decisions. No implementation or deployment has
occurred.

M0 standalone contract ancestor: `21a75b7944573f6b41f6c091349458b5b9ab1e4b` (2026-11-12 UTC).

Execution update 2026-11-12 UTC: M0-M3 implemented, M4 runtime blocker retained,
independent source reviews completed; no deployment, restart or closure.

Implementation revision: `c2507338fbdcd5e7156e708f84a43691942ef19f`; M4/M6/M7 remain open.
