# Security review - GridMET Redis admission

## Findings

| ID | Severity | Surface | Description and exploit path | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Redis Lua integrity | Pruning changed state before complete type and ownership validation. Overlapping liveness/active members could remove a live holder's owner token; raw fractional sequence text failed after partial writes; infinite expiry leaked capacity indefinitely. | `wepppy/climates/gridmet/admission.py:_SCRIPT`; independent real-Redis before/after `DUMP` comparison | Pre-write types, membership, canonical sequence, and finite expiry validation added. Wrong-type, overlap, fractional sequence, and infinite expiry now reject with all six keys unchanged. | Resolved |
| SEC-02 / COR-01 | Medium | Lease failure containment | A renewal failure recorded while context exit joined the renewal thread could be ignored, permitting a successful result. Explicit failed renewal was not sticky. | `GridMetPermit.renew`, `release`, and `__exit__`; `test_manual_renew_failure_is_terminal` and `test_inflight_renew_is_joined_before_terminal_failure_check` | Terminal failures remain recorded; exit joins renewal and rechecks its outcome. Independent focused tests passed both successful and failing real-thread races. | Resolved |
| SEC-03 / COR-02 | Medium | FIFO integrity | Missing sequence state could restart FIFO ordinals; cardinality-only validation missed mismatched queue members and duplicate ranks. | `wepppy/climates/gridmet/admission.py:_SCRIPT`; independent real-Redis corruption corpus | Sequence continuity, member correspondence, and strictly increasing queue ranks now reject malformed state before mutation; all corresponding independent cases passed. | Resolved |
| SEC-04 | Low | Configuration error taxonomy | A supplied timing integer too large for float conversion raised `OverflowError` before the intended configuration error. | `GridMetAdmissionConfig.__post_init__`; `test_unrepresentable_timings_rejected_before_io` | Check the platform range before `math.isfinite`; regression inputs include `10**400` and `1e100` for every timing field. | Resolved |

Risk acceptance requires explicit package-owner acknowledgment. No finding is
accepted as an exception to the contract.

## Metadata

- Package: `docs/work-packages/20260907_gridmet_redis_admission/`.
- Reviewer: independent Codex `/root/contract_security`.
- Review started: 2026-09-07 16:31 UTC; final review: 2026-09-07 16:41 UTC.
- Checkpoint: `1b4835ca73bc67c9c84ecbb26f596aab4078e234`, following starting
  revision `583e6870c639999515035423f133e5925dae2da5`.
- Runtime scope: `wepppy/climates/gridmet/admission.py`, GridMET acquisition and
  public clients, Daymet/PRISM and NoDb propagation, development Compose,
  `tools/gridmet_admission_probe.py`, tests, configuration reference, and Forest
  runbook. No runtime files were edited by this reviewer.
- The final contract makes runtime representation bounds explicit and explains
  that an external observer reports zero for unknown local elapsed wait. Neither
  clarification adds an operational parameter or changes Forest values. Queue
  position and Redis server time remain independently observable.
- Related reviews: [correctness](2026-09-07_correctness_review.md),
  [QA/code](2026-09-07_code_qa_review.md), and
  [contract checkpoint](2026-09-07_contract_decision.md).

## Security triage decision

Security impact is **high** and a dedicated review is required. The patch adds
Redis state mutations, cross-process admission, lease renewal, subprocess probes,
and outbound-request gating. It adds no route, privilege grant, external
dependency, RQ topology, or model-output schema.

The threat model treats application processes and Redis credentials as trusted
operator resources. Ownership tokens prevent accidental or hostile cross-owner
operations through the admission interface; they do not isolate an attacker
already able to issue arbitrary commands with the shared Redis credential.
Malformed Redis state, outages, ambiguous commands, stale ownership, and delayed
process scheduling must fail closed. Acceptance probes must protect both the
default and effective operational namespace.

Valid states remain distinct from malformed inputs: absent/false enable and
literal public `None` preserve acquisition with zero Redis activity; valid
enabled empty/populated namespaces admit normally; stale tickets and expired
leases are reclaimed; timed-out or interrupted callers clean only owned state.
The canonical contract explicitly permits bounded wait exhaustion and separate
configuration, Redis, and ownership failures.

## Verdict

- Runtime security gate: **PASS**; unresolved high 0, medium 0, low 0.
- Final review follows correctness PASS at 16:37 UTC and QA PASS at 16:40 UTC.
  All findings were rechecked against the final implementation.
- Release recommendation: proceed through remaining full validation, exact
  candidate commit/push, and Forest operational acceptance. This artifact does
  not establish deployment parity or a successful real public download.

## Surface checks

### 0) Valid-state noninterference and user experience

- Default-off behavior, immutable configuration propagation, existing response
  validation, and release-before-backoff are represented in focused tests.
- Direct real-Redis checks admitted a valid holder before each malformed-state
  injection and proved rejection preserved all six keys; mocks were not used
  to close SEC-01 or SEC-03.

### 1) Auth, session, and authorization

No auth/session/JWT/CSRF or route changes. The invoked plan limits deployment to
Forest development Compose and isolated probes. Batches, registry publication,
other hosts, and Kubernetes remain excluded.

### 2) Secrets and credential handling

Connections use `redis_connection_kwargs(RedisDB.LOCK)` with the existing secret
contract. Redis exceptions expose only their class; full connection parameters,
ownership tokens, and raw query URLs are excluded from new logs. Development
Compose adds seven nonsecret parameters without changing secret mounts.

### 3) Input validation and output safety

Configuration rejects unknown/empty booleans, nonfinite timings, invalid limits,
and namespace characters outside the bounded ASCII grammar. Probe process count,
timings, polling frequency, and identifiers are bounded. Operational namespace
overrides receive the same mutating-probe refusal as the default key.

### 4) Filesystem and run-tree boundaries

Existing validated filename components, temporary NetCDF staging, payload byte
ceilings, and atomic publication remain. Probe file inputs are local evidence;
the probe does not delete Redis keys or write run outputs.

### 5) Queue, worker, and subprocess surfaces

No RQ enqueue/dependency edits. Configuration passed to child processes contains
only immutable primitive values. Probe subprocesses use argument lists, bounded
parent waits, targeted terminate/kill, and ownership-safe context cleanup.

### 6) Agentic tooling and MCP surfaces

No MCP or agent credential changes. Reviewer actions are local read-only review,
bounded verification, and this artifact. Live host operations remain with the
authorized executor and the Forest operational gate.

### 7) Network and external integrations

Existing public GridMET destinations, redirect refusal, connect/read timeouts,
retry count, and byte ceilings remain. Each retry reenters admission with the
shared monotonic scheduling deadline. Redis uses bounded connection/socket
timeouts with automatic retries disabled; there is no fail-open path.

### 8) CI/CD and supply chain

No dependency, workflow, runner-token, or image-publication changes. Only the
development Compose environment is amended. Candidate commit and push must
precede Forest recreation.

### 9) Data integrity, locking, and concurrency

Same-slot Lua scripts and Redis server time are the shared authority. Random
tokens, expiring state, conservative local validity, and policy fingerprints
form the boundary. Corruption and renewal races in the findings table are
closed by independent verification. NoDb persistence/locking stays unchanged.

### 10) Logging, monitoring, and incident readiness

The probe emits sanitized JSON and suppresses raw child stderr. HTTP retry
errors suppress Requests exception chains that can expose query coordinates.
The Forest runbook scopes environment backup, inspection, activation, rollback,
and diagnostic evidence without full environment or Compose dumps.

## Validation evidence

- Read the checkpoint, contract, ADR-0050, ADR-0028, full runtime diff, new
  admission/probe implementations, and focused test definitions.
- Independent `wctl run-pytest tests/climates/gridmet/test_admission.py
  tests/climates/gridmet/test_admission_clients.py
  tests/tools/test_gridmet_admission_probe.py --maxfail=1`: **95 passed**, two
  existing dependency deprecation warnings. This includes foreground expiry,
  delayed replies, terminal manual renewal, successful/failing in-flight renewal
  threads, HTTP close/release ordering, and probe namespace/logging safeguards.
- Independent `wctl docker compose exec -T weppcloud env -u REDIS_URL -u
  RQ_REDIS_URL -u SESSION_REDIS_URL -u REDIS_PASSWORD -u REDIS_PASSWORD_FILE
  REDIS_HOST=gridmet-admission-test-20260907 REDIS_PORT=6379 python -` ran seven
  real-Redis corruption cases: wrong owner type, active/liveness overlap, raw
  sequence `1.0`, infinite active expiry, duplicate queue rank, equal-count
  member mismatch, and missing sequence. Each first admitted a valid holder,
  injected the isolated defect, captured all six keys with Redis `DUMP`,
  attempted admission, and asserted explicit rejection plus identical dumps.
  **7/7 passed** at 2026-09-07 16:35 UTC. Cleanup deleted only the exact UUID
  test keys from the disposable service; no operational keys or DB flush.
- The implementation owner reports **9 real-Redis scenarios passed** in
  153.11 seconds: ownership/conflict, FIFO, independent processes, timeout,
  outage, clock disagreement, killed owners, corruption, and heartbeat. The
  reviewer read those scenarios and independently exercised the corruption
  boundary above; the nine-scenario suite was not redundantly rerun here.
- The implementation owner reports the final admission unit suite **45 passed**
  in 9.38 seconds after the huge-integer validation fix. Final source readback
  confirmed range checks precede float conversion. Correctness and QA artifacts
  independently cover the last wait-snapshot and context-entry cleanup fixes.
- Correctness and QA final artifacts were read after their PASS signoffs. Broad
  suite and Forest integration evidence remain executor-owned; no successful
  deployment or download is inferred from unit and Redis test counts.

## Residual risk

Redis limits live permits; it cannot fence an already-running remote GridMET
request after process suspension or partition. Socket inactivity timeouts do
not impose a total wall-time bound on DNS or trickling responses. The canonical
contract and ADR explicitly state this limitation. Disabled or independently
configured callers bypass the shared pool by design, so deployment configuration
parity is required. Forest evidence cannot establish Kubernetes acceptance.

## Sign-off

- Security reviewer: Codex `/root/contract_security`, **PASS**, 2026-09-07
  16:41 UTC, after correctness and QA review completion.
- Package owner: root executor acknowledgment and remaining release/deployment
  evidence are recorded in the tracker and integration artifact. No finding
  requires risk acceptance.
