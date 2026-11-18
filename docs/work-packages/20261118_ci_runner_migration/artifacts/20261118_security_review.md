# Security Review - CI runner migration

## Metadata

- Package: `docs/work-packages/20261118_ci_runner_migration/`
- Reviewer: independent `/root/ci_migration_review` agent
- Date: 2026-11-18 UTC
- Source: `b53395d363705bef477d97522045fcded6608cfd`, plus browser Compose's temporary query-coordination mount; reviewed file SHA-256 `4c0c3e4b1e10db92866f378d19997d7108a51ffe979153c29294defba53b2fa9`.
- Scope: migrated workflow sources/generated YAML, browser fixture, isolated Compose runtimes, authenticated Status2 client, coverage commands, schedule retirement and shared-header conformance repair.
- Related evidence: [tracker](../tracker.md), [header repair](header-conformance-repair.md), [validation manifest](validation-artifacts.json), [retirement readback](retirement-readback.json).
- Correctness: interim independent findings were sent to the integrator; final browser/runner acceptance remains pending and is not supplied by this review.

## Security Triage Decision

Security impact is **high**; dedicated review is required because CI execution,
credential provisioning and container boundaries change. The threat model retains
the repository's existing trusted `remote-ci` runner. Public PR execution on that
persistent Docker-capable runner is not a sandbox against malicious repository
code. This migration does not claim otherwise or assign workloads to the trusted
image builder.

Valid states include a fresh disposable database/run tree, absent optional control
panels, populated authenticated test pages and supported legacy session cookies.
A production deployment profile or preexisting account schema must fail before
fixture mutation. Missing browser output or skipped required pages must not be
accepted as successful validation.

## Findings

The initial source review and the later runtime-preparation/RQ revisions have no
unresolved findings after the corrections recorded below. Current counts: high 0,
medium 0, low 0. Earlier correctness findings concerning prefix routing, cookie settings,
run configuration, schedule gating and skipped-page coverage were repaired in
source. Their runtime acceptance remains part of the separate correctness gate.

The header repair changes only the developer indicator's existing view-model
lookup from `ron` to `current_ron`. It restores the canonical contract in
`docs/schemas/project-developer-mode-contract.md`, State and lifecycle/UI sections.
It does not activate developer mode, alter roles, mutate persisted state, or widen
backend authorization. Missing/false/true display states have regression coverage.

## Verdict

- Initial security **source review: PASS** for the identified revision and mount addition.
- Latest uncommitted runtime additions: security **source review PASS**, including
  the resolved SEC-01 and RQ cleanup/origin corrections documented below.
- Overall migration/release acceptance: **pending**, not complete.
- Recommendation: retain the source changes; require remaining real browser,
  supported-runner and failure-cleanup evidence before package closure.
- No risk acceptance or policy bypass is requested by this review.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

The browser fixture retains canonical owned-cookie migration configuration,
`disturbed9002_wbt`, test-support scope and actual authenticated account creation.
It mounts the application under `/weppcloud` instead of changing production route
prefixes. Fresh report validation rejects all-skipped execution and requires the
seven intended axe page identities. Theme Lab succeeded against the actual app;
remaining controller/accessibility valid-state checks are still required.

### 1) Auth, Session, and Authorization

Production auth/session/JWT/CSRF implementations are unchanged. Disposable browser
roles permit the existing authenticated smoke coverage; signing secrets and the
scoped one-hour support token stay within the fixture's process/container.
Status2 uses the actual service and existing signed-client protocol, exact allowed
Origin, and Redis authentication. No anonymous fallback service was introduced.

### 2) Secrets and Credential Handling

Browser passwords and signing material are generated per invocation. Status2
signing material is generated in an owned temporary directory under umask 077,
passed through file paths, and removed by cleanup. `local-ci-only` is an explicit
disposable Redis fixture credential, not a deployment credential or fallback.
No Forest credential files are mounted or copied. Support requests retain their
existing token-safe HTTP path outside Playwright tracing. The reviewed logs do
not expose generated passwords, keys or bearer tokens.

### 3) Input Validation and Output Safety

Suite selection is an argparse enum. Subprocess calls use argument lists; workflow
commands interpolate trusted workspace/job identifiers with quoting. New fixture
URLs are loopback-only. Existing support URL/scope restrictions and production
render escaping remain intact. Missing reports and incompatible fixture runtime
produce explicit failures rather than hidden recovery.

### 4) File System and Run-Tree Boundaries

Independent Compose rendering showed no privileged containers, published ports,
Docker socket mounts or live-secret mounts. Browser execution binds only the task
checkout and uses temporary `/wc1/runs`, `/wc1/logs` and query-coordination storage.
The Status2 smoke container has no host mounts, a read-only root, dropped
capabilities and temporary scratch. Account initialization refuses a nonempty
schema. Successful/failing job cleanup is scoped to its unique Compose project;
removed Forest cleanup no longer deletes shared Redis data.

### 5) Queue, Worker, and Subprocess Surfaces

No production RQ wiring changes; `check-rq-graph` is not applicable. Existing test
commands remain explicit. Status2 readiness and client execution are bounded;
cleanup terminates/reaps its owned service. Workflow cancellation retains the
normal Actions cleanup path. Hard runner loss still requires ordinary runner
recovery and is not claimed to be solved by shell traps.

### 6) Agentic Tooling and MCP Surfaces

The operator authorized the migration and explicitly approved retiring both the
21 profile schedules and CI Samurai. Retained readback covers exactly those 22
workflows, disabled with zero queued runs. No unrelated runner relabeling,
production restart or deployment authority is inferred from this task.

### 7) Network and External Integrations

Both application and smoke runtime networks render as internal, without host
ports. The browser reaches its fixture through loopback. Dependency acquisition
occurs in the declared build/Node/Go contexts using existing package locks and
pinned image references; outbound download capability is not represented as a
runtime isolation guarantee. Live Forest URLs and SSH restart orchestration are
removed from the migrated/retired jobs.

### 8) CI/CD and Supply Chain

Migrated checks target `remote-ci`; Cloc uses a disposable hosted runner. The
`ghcr-builder` label remains exclusive to trusted publication. Checkouts disable
persisted credentials; new test jobs use read-only repository token permissions.
Node/Go checks reuse existing pinned Docker images. Existing intentionally scoped
reporting permissions remain unchanged. No new third-party setup action is needed.

### 9) Data Integrity, Locking, and Concurrency

Unique job/run/attempt Compose project names separate databases, Redis and cleanup.
Production NoDb locking and session persistence code are unchanged. Temporary query
coordination storage makes the real browser fixture writable without borrowing
host state. That mount requires final valid controller execution evidence.

### 10) Logging, Monitoring, and Incident Readiness

Status2's retained log proves all five authenticated messages were delivered;
report artifacts and source/revision evidence remain reviewable. Browser report
checks reject missing authenticated coverage. Rollback is normal reviewed Git
history, not shared-master reset or a runner-label bypass. Pending CI failures
must remain visible rather than being canceled or relabeled as passes.

## Validation Evidence

Independently inspected the rendered browser and Status2 Compose configurations;
there were no published ports, privileged containers or live-secret/socket mounts.
A direct browser-fixture invocation with deployment profile `production` exited
before importing the app or touching the database. The local negative transcript
is `/tmp/ci-review-invalid-runtime.log`; this review records its observed result.

Read retained `status-smoke.log.gz`: actual signed smoke client received 5/5 frames
and exited zero. Read `status-tests.log.gz` and `preflight-tests.log.gz`: unit and
integration packages passed, including existing auth validation. Read current
header regression output: seven tests passed with clean receipt
`5615d7b4d10e44a096d865d89287b4b4`. Read actual repaired Theme Lab output: HTTP 200,
14 themes and 1,568 measurements; one browser test passed. The log also reports
59 non-enforced contrast findings, which must not be presented as universal AA
conformance. Browser/CI acceptance beyond these observations remains pending.

Read `retirement-readback.json`: 22 entries, every state `disabled_manually`, total
queued count zero. These are immutable observations, not guarantees about future
administrative changes.

## Residual Risk

The trusted self-hosted runner model and ordinary dependency-download trust remain
existing assumptions. Real controller/accessibility completion, supported-runner
execution and unsuccessful-job cleanup evidence are outstanding acceptance work.
Do not describe this source pass as a completed migration, deployment, exhaustive
security proof, or accessibility certification.

## Sign-off

Security source reviewer: `/root/ci_migration_review`, 2026-11-18 UTC.
Package integrator: `/root`; final acceptance is pending the named evidence.

## Artifact Observability Gate

This package creates CI reports and disposable fixture data, not new project
outputs. Retained build/test/report evidence and remote queue observations are the
reviewable artifacts. Production project archive/download retention is unchanged.
The browser requires fresh semantic report content instead of treating successful
process exit or directory existence as sufficient proof.

## Incremental review: CAP login and prepared CI assets

Reviewed the later uncommitted CAP service, normal-login/storage-state fixture,
`tests/prepare_ci_runtime.py`, parser additions to `docker/Dockerfile.test`, and
new preparation steps in affected workflow sources/generated YAML. This review
extends the initial source pass for these additional surfaces; it does not
claim actual browser or CI acceptance.

| ID | Severity | Surface | Description and required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | `tests/prepare_ci_runtime.py`, existing runtime directories | The helper previously accepted existing real asset directories without checking their identity. It now rejects them, verifies candidate/image manifests and allows only absent paths or links to the image-owned directories. The direct browser fixture calls this preparation too; mismatch, foreign-directory and idempotent-link cases have regression coverage. | Resolved |

The added CAP service is the existing pinned owned service, on the internal job
network without host ports. Its fixed `local-ci-cap-only` credential is confined
to this disposable fixture. The login helper obtains a real bounded challenge,
redeems it through the existing canary, fetches a real CSRF token and submits the
normal password login. It does not forge an authenticated Flask session or disable
CAP/CSRF server checks. Changing `requests` cookie transport to send Secure cookies
over this internal loopback HTTP connection does not change server cookie policy;
Playwright receives Secure storage-state cookies. Real browser behavior remains
an acceptance requirement.

The login helper's storage-state and CAP-secret files are protected by a private
`TemporaryDirectory` and mode 0600, then removed in `finally`; they are outside
uploaded report paths. At review time its docstring said tmpfs, but browser `/tmp`
was ordinary container-layer temporary storage. The helper description now names
container temporary storage; the ownership and cleanup boundary is sound.

The test image now builds shape/geoparquet parsers from locked candidate sources
and generates adjacent provenance. Existing wctl preflight compares the complete
recorded Rust/Cargo inventory with candidate bytes and checks binary identity.
The CI/development revision label is not release attestation. Required actual
parser probes and hostile-input tests remain part of the runtime acceptance.
No production parser, credential policy or application auth implementation changes
were introduced by these additions.

### Incremental readback: isolated RQ API and SEC-01 closure

The browser fixture now serves the existing RQ API through an owned pre-bound
loopback socket and a fixed proxy target. It introduces no worker, host port,
production mount or replacement authorization path. Startup has a deadline;
context-manager cleanup requests server shutdown and checks its thread terminates.
The stale explicit `rq_context.__exit__` call was removed because the `with`
statement owns cleanup. The RQ proxy preserves the incoming Host and port via
`host=None`, so actual same-origin validation remains active instead of accepting
a fabricated origin or disabling CSRF checks.

Read back clean focused receipt `49895803660d498f8af012d5b6d81aa0`: pytest and wrapper
exit zero, source/runtime changes empty. The reported suite outcome is 295 passed,
three deselected. This covers asset-preparation regressions; the final removal of
the dangling cleanup call and proxy Host correction occurred afterward and are
source-reviewed here. Their real controller execution was still running at review
time, so the earlier receipt is not presented as validation of those last edits.

The exact incremental source hashes reviewed are:

| Path | SHA-256 |
| --- | --- |
| `tests/ci_browser_runtime.py` | `0b860b106c6e3639b93e3e24c8537f12abc2dedb0f9ff1b3e1fa0dd24cf5d4e9` |
| `tests/prepare_ci_runtime.py` | `79abc4b1b3cb92c2459c392ec2700c7fb1eb9be550ae0967224bd4801ad4b516` |
| `docker/docker-compose.browser-test.yml` | `674b0dc81fb1cf3b5833e5d807715691c173bbba47b5287da4c23b996c4e2e04` |
| `docker/Dockerfile.test` | `e40252c15f9e9564e9b07bdeeb8a20cf64883db10c979a4629dbb2790070aea0` |
| `wepppy/weppcloud/static-src/playwright.config.mjs` | `58062da5c9103e9bb320375a42692e0ebbce2e117e4a5895005532d51e04e9d3` |

This closes SEC-01 at source/regression level and finds no additional source
security defect. It does not close the still-pending actual browser, generated
report, supported-runner, failed-job cleanup or overall migration acceptance gates.
