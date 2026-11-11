# Sanitize traceback secrets without removing diagnostic context

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, WEPPcloud continues to show and retain useful tracebacks, with
the same fields and path/frame context operators and frontend panels currently
use, but configured secret values and credential-shaped material are removed
before the diagnostic crosses any API, log, run-file, RQ Redis or status boundary.
There is one sanitized representation for existing consumers. Normal successful
execution does not read secret files or pay the sanitizer cost.

Kubernetes remains a mounted-file deployment of the same contract. Each
application or worker adapter selects metadata for only the secrets consumed by
that process. F5 does not decrypt SOPS or query Kubernetes. Container
stdout/stderr is an output sink, and synthetic production-equivalent mounts are
part of focused acceptance; live openwepp deployment remains separate.

Redis credential transport is completed first with scoped tests. F5 then passes
focused sink/canary checks and the exact full Python and frontend gates.

## Progress

- [x] (2026-11-11 18:27 UTC) Record filter-not-removal, one representation,
      absolute-path preservation and unchanged authorization.
- [x] (2026-11-11 18:27 UTC) Record exceptional-path temporary secret snapshots,
      no process registry/cache and unchanged secret lifecycle.
- [x] (2026-11-11 18:27 UTC) Scaffold package, contract/failure artifacts and
      correctness/security review gates.
- [x] (2026-11-11 18:27 UTC) Record Redis-first order and required full pytest,
      npm lint and npm tests for F5.
- [x] (2026-11-11 19:05 UTC) Review openwepp SOPS/projected-secret handling and
      record process-owned sources, compound decoders and container-log sinks.
- [ ] Prerequisite: Redis credential transport passes scoped acceptance/reviews.
- [ ] M0: ratify safe traceback/source/sink contract and checkpoint.
- [ ] M1: implement renderer/snapshot and focused unit/performance tests.
- [ ] M2: integrate API/error factory and logging formatter sinks.
- [ ] M3: integrate run-file, RQ persistence and publication sinks.
- [ ] M4: close focused validation and independent reviews.
- [ ] M5: pass full pytest, npm lint and full npm tests; close SEC-05.

## Surprises & Discoveries

- Observation: standard Python traceback formatting does not capture locals by
  default, but exception messages, notes and library errors can include complete
  connection URLs, headers or configuration values.
  Evidence: current response factories interpolate `str(exc)` and formatted
  exceptions into APIs and logs.

- Observation: the same raw trace can be emitted to several sinks: API details,
  logger `exc_info`, run-local files and RQ Redis metadata. Sanitizing only the
  response field leaves retained copies.
  Evidence: `wepppy/weppcloud/utils/helpers.py`, query-engine log writer and
  `WepppyRqWorker.handle_exception`.

- Observation: synthetic replacement with 24 secret values measured about
  18 microseconds for a 7.8 KB trace on this host; exceptional-path loading keeps
  this work out of normal request/log throughput. This is design evidence, not a
  final performance receipt.

- Observation: openwepp workloads receive SOPS-managed values as read-only
  mounted files, generally mode `0444`; application service accounts do not have
  Kubernetes Secret read permission.
  Evidence: `clusters/openwepp/apps/weppcloud` in the sibling
  `open-wepp-org` repository and
  `artifacts/20261111_kubernetes_secret_handling_review.md`.

- Observation: environment presence does not prove local source ownership. The
  web pod declares a WEPPcloudR token path that only the downstream RQ worker
  mounts, while shape converter declares a Redis password path without a secret
  mount or Redis egress.
  Evidence: `open-wepp-org` `web.yaml`, `rq-worker.yaml`,
  `request-plane.yaml` and the Kubernetes review artifact.

- Observation: `WEPP_AUTH_JWT_SECRETS_FILE` is a comma-delimited key ring.
  Redacting the complete file string would not remove an individual signing key.
  Evidence: `_parse_secrets` in `wepppy/weppcloud/utils/auth_tokens.py`.

## Decision Log

- Decision: preserve tracebacks and absolute paths, using one sanitized
  representation rather than audience-specific variants.
  Rationale: the app depends on traceback observability; account creation makes
  the proposed audience distinction complex with limited security benefit.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: do not introduce a process-wide secret registry. Load explicitly
  configured mounted/environment secret values only while rendering an
  exception, then release references without claiming zeroization.
  Rationale: preserve the current secret lifecycle and avoid aggregating or
  extending secret retention while keeping work off normal paths.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: execute Redis credential transport first with scoped validation;
  F5 then runs full pytest, npm lint and full npm tests.
  Rationale: remove avoidable Redis credential strings before validating the
  comprehensive traceback boundary, while applying broad regression cost once.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: source selection is process-owned metadata, not scanning of known or
  arbitrary environment variables. Adapters select immutable setting/decoder
  metadata; only one render call holds the resolved values.
  Rationale: Kubernetes manifests include downstream-only and stale file paths.
  Process profiles preserve fail-closed behavior for true local sources without
  destroying unrelated traceback observability or creating a value registry.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: treat SOPS and the Kubernetes Secret API as deployment boundaries,
  not sanitizer inputs. F5 reads only files already mounted into the process and
  does not add RBAC.
  Rationale: workloads already receive the required plaintext files, while
  expanding decryption/API authority would increase risk without improving
  filtering.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: include Kubernetes-captured stdout/stderr, uncaught process output
  and the Python WEPPcloudR control plane in the sink inventory. Prove local
  production-equivalent container behavior; leave live openwepp rollout to a
  separately authorized deployment package.
  Rationale: a logging formatter cannot protect an output path it never sees,
  and code-package acceptance must not silently authorize a cluster mutation.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

## Outcomes & Retrospective

No implementation outcome exists. Populate this section with sink coverage,
canary results, performance, full-suite receipts and residual risks.

## Context and Orientation

WEPPcloud Flask factories in `wepppy/weppcloud/utils/helpers.py` format stacks
and exceptions, log them, optionally write `exception_factory.log`, and return
diagnostic details. FastAPI rq-engine has a parallel helper in
`wepppy/microservices/rq_engine/responses.py`. Query-engine formats several
error classes into `stacktrace`, `stacktrace_lines` and `exc_info`, logs through
Python logging and appends `exceptions.log`.

RQ stores failure text in Redis. `wepppy/rq/rq_worker.py` passes raw `exc_string`
to superclass persistence and stores another copy in job meta; task decorators
and run loggers also format exceptions. The repair must sanitize before the first
write, not merely at later API readback.

The new module belongs under `wepppy/observability/` and must not be named
`traceback.py`, which could shadow Python's standard library. It must not import
Flask, FastAPI, RQ or application objects. Framework adapters call it.

An exceptional-path secret snapshot contains only values from an explicit
source profile selected by the current application, worker or logging adapter.
A source profile is immutable metadata: canonical setting name, file/env
precedence, required/optional state and bounded decoder. It never stores secret
values. The snapshot reads the configured `_FILE` value, or current legacy
environment fallback, only when rendering. It does not enumerate `/run/secrets`,
arbitrary `*_FILE` variables or request data, and is never
cached/serialized/exposed. Missing optional local settings are absent;
configured-but-unreadable local sources force fail-closed rendering. A path
owned by a downstream process is not part of the caller's profile and is never
opened.

The openwepp deployment mounts the ordinary runtime/auth/database values plus
WEPPcloudR tokens and a TLS private key. Its control plane also has a projected
Kubernetes service-account token. The authorization JWT key-ring file must be
decoded into its comma-delimited constituent keys. The Kubernetes CA, public TLS
certificate and namespace file are not secrets. The detailed source map is in
`artifacts/20261111_kubernetes_secret_handling_review.md`.

## Plan of Work

### Prerequisite: Redis package

Read the Redis package tracker and validation/review artifacts. Do not begin F5
implementation until its scoped checkpoint proves Redis clients, RQ and server
work without secret-bearing URLs/argv. Record the exact prerequisite revision.

### Milestone 0: Contract and inventories

Create `docs/schemas/safe-traceback-contract.md`. Define the existing diagnostic
fields preserved, the single representation, absolute-path behavior, configured
process source profiles, file/env precedence, compound decoders,
raw/percent/JSON variants, structural patterns, exception chains/groups/notes,
locals prohibition, output bounds, failure behavior and error-ID correlation.
Decide whether bounds require a parameterization ADR.

Inventory every `traceback.format_*`, `logger.exception`, `exc_info`, run-file
write, RQ `exc_string` and traceback response/publication consumer. Disposition
each row in the failure matrix, including WEPPcloudR reconciliation,
interpreter/framework uncaught output and Kubernetes-captured stdout/stderr.
Ratify the process-to-source matrix from the Kubernetes review and identify
downstream-only/stale settings that adapters must not open. Obtain independent
contract/security reviews and commit a standalone ancestor checkpoint.

### Milestone 1: Pure renderer and snapshot

Implement a pure module such as `wepppy/observability/safe_traceback.py` with
immutable `SecretSourceSpec`/`SecretSourceProfile` metadata, an immutable
per-call secret snapshot, `sanitize_text`, structured sanitization and
exception/stack render functions. A profile contains setting names and decoders,
never values. Build `TracebackException` with
`capture_locals=False`, retain ordinary frames/absolute paths and sanitize every
exception value/note/chain/group. Exact values and bounded encodings are replaced
longest-first; structural redaction covers credential forms not known in advance.

Provide a bounded comma-list decoder matching the authorization JWT consumer and
explicit raw/PEM handling for the WEPPcloudR token, TLS private key and owning
control plane's service-account token. Do not parse public certificates or trust
material as secrets. A configured source read fails closed only when the source
belongs to the selected profile.

Never return raw input on error. If a configured source cannot be read or the
sanitizer fails, return a fixed generic diagnostic with the caller's `error_id`.
Add tests that inspect module state to prove no registry/cache remains after the
call and that no file is read on successful/non-exception paths.

### Milestone 2: API factories and logging

Route Flask, rq-engine, query-engine, browse/download and the WEPPcloudR control
plane exception construction through the renderer with the correct source
profile. Preserve current response keys and existing authorization; do not add
or remove traceback fields as an incidental change. Sanitize both the human
message and trace-derived details when either can contain exception text.

Install a safe formatter on every relevant production handler so `exc_info`
from application or dependency loggers is rendered centrally. Avoid a filter-only
design because formatters render exception text. Ensure correlation/error IDs are
unchanged. Direct handlers/tests must prove the final emitted string, not just a
helper return.

Inventory top-level entry points and framework startup behavior that can write a
raw traceback directly to stderr. Install the earliest safe hook the existing
entry point supports, or retain evidence that a bounded startup failure cannot
contain a loaded secret. Never add a raw fallback merely to preserve startup
detail.

### Milestone 3: Persistence and publications

Sanitize before writing `exception_factory.log`, `exceptions.log`, RQ failure
`exc_string`/meta and any status/error publication. RQ superclass failure
handling must receive the sanitized string so Redis never stores the raw value.
Preserve controlled-error schemas, job status, retry/dependency behavior and
frontend status parsing.

### Milestone 4: Focused validation and reviews

Use unique synthetic canaries supplied through temporary mounted-file and legacy
environment fixtures. Include a comma-delimited key ring with separately
detectable members, a Kubernetes service-account-shaped JWT, WEPPcloudR bearer
token and PEM private key. Raise exceptions containing raw, URL-encoded and
JSON-escaped values, URI credentials, Authorization/cookie data, JWT, PEM,
notes, causes, contexts and ExceptionGroups. Read every
API/log/file/RQ/status/stdout/stderr sink and assert no canary/variant remains
while frames, absolute paths, type, line/function and safe context do.

Run a production-equivalent container contract with synthetic files at the
openwepp paths, read-only `0444` modes and current non-root identity. Prove that
web/downstream and shape-converter stale paths are not opened by the wrong
profile, a missing required local source fails closed, and a file replacement is
observed by the next exception without caching. Do not decrypt SOPS or contact a
live cluster.

Benchmark the exceptional path and prove ordinary requests/logs do not open
secret files. Close correctness, QA and security findings before broad tests.

### Milestone 5: Full regression gates and closeout

Run exactly:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

All commands must exit zero on the reviewed revision. A segmented run does not
replace the requested full command. Update canonical docs, package/tracker,
reviews and the gitignored audit board from evidence. Production deployment
remains separately authorized.

## Concrete Steps

Work from `/home/workdir/wepppy` and preserve unrelated dirty files. After the
Redis prerequisite, refresh the inventory:

    rg -n "traceback\.format|logger\.exception|exc_info|exc_string|stacktrace" \
      wepppy services tests

Review the retained Kubernetes source evidence without reading encrypted values:

    cd /home/workdir/open-wepp-org
    scripts/check-secrets.sh
    rg -n "_FILE|secretName:|serviceAccountToken|automountServiceAccountToken" \
      clusters/openwepp/apps/weppcloud templates/declarative-dem-pod.json

Return to `/home/workdir/wepppy`. Do not make F5 depend on a sibling checkout at
runtime or in unit tests; copy only the non-secret path/source contract into test
fixtures. Create focused tests under `tests/observability/` and the existing
Docker/runtime-contract test area. Add a local container validation entry point
only if existing `wctl run-pytest` fixtures cannot reproduce the image identity,
mount paths and file modes.

Focused test paths must be created/refined around the pure module, Flask helper,
rq-engine responses, query-engine handlers, browse/download errors, RQ worker
failure persistence and logging configuration. Use `wctl run-pytest` for each
target and retain direct sink output. Run stub/check-stub gates if the new module
has a public stub surface. Finish with the exact full commands in Milestone 5.

## Validation and Acceptance

For every sink, the same exception must produce a sanitized diagnostic with
useful frames/absolute paths and no configured canary in raw or encoded form.
Locals/environment mappings are absent. Every member of a compound key ring is
absent. A configured local source or sanitizer failure emits only the fixed
generic diagnostic/error ID, while downstream-only and stale paths are not
opened. RQ Redis and captured container stdout/stderr never contain the raw
trace. The next exception after a synthetic file replacement redacts the new
value, proving no cache. Normal execution performs no snapshot read. Existing
frontend stacktrace tests pass. Focused and all three full commands exit zero.

Helper unit tests alone cannot establish sink safety. Each API formatter, log
handler, run file, RQ persistence boundary and container output path needs direct
readback. Live openwepp deployment is not a package-completion requirement and
remains separately authorized.

## Idempotence and Recovery

The renderer is stateless per call. Tests use temporary files/environment and
remove them without touching real secrets. Integration should be incremental:
keep focused tests green after each sink, but never retain a raw fallback flag in
deployed configuration. If a sink fails, revert only its adapter and keep the
package open; do not publish real secret-bearing traces as diagnostics.

## Artifacts and Notes

- `artifacts/20261111_contract_decision.md`: ratified design decisions.
- `artifacts/20261111_failure_class_matrix.md`: source/sink inventory.
- `artifacts/20261111_kubernetes_secret_handling_review.md`: openwepp mounted
  source profiles, log sinks and validation boundary.
- `artifacts/20261111_correctness_review.md`: observability compatibility gate.
- `artifacts/20261111_security_review.md`: secret-disclosure gate.
- Add QA, focused validation and full-suite receipts during execution.

## Interfaces and Dependencies

The module should expose immutable metadata equivalent to
`SecretSourceSpec(setting, file_setting, required, decoder)` and
`SecretSourceProfile(name, sources)`, plus a narrow rendering interface
equivalent to `render_exception(exc, *, source_profile, error_id=None) -> str`,
`render_current_exception(*, source_profile, error_id=None) -> str`,
`render_stack(*, source_profile) -> str` and
`sanitize_text(text, snapshot) -> str`. The safe logging Formatter receives a
profile during process logging setup. Exact names may be ratified in M0. Use only
the Python standard library and existing observability/correlation helpers. Do
not expose secret snapshots or return their values.

## Revision Note

2026-11-11: Initial plan captures the operator's filtered-traceback design,
single representation, preserved absolute paths, exceptional-path-only secret
snapshot, unchanged secret lifecycle, Redis-first order and mandatory full
Python/frontend gates. No implementation or deployment occurred.

2026-11-11: Openwepp review adds process-owned source metadata, compound
key-ring/WEPPcloudR/Kubernetes token coverage, container stdout/stderr and a
synthetic production-equivalent mount gate. F5 does not decrypt SOPS, query
Kubernetes or authorize a live rollout. No implementation or deployment
occurred.
