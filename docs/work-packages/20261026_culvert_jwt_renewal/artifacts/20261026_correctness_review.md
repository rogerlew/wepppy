# Correctness review: Culvert JWT renewal

## Metadata

- Reviewer: independent `renewal_contract_correctness` reviewer agent.
- Date: 2026-10-26 UTC; final live-state inspection approximately 16:46 UTC.
- Contract ancestor: `4cd8e9cb1`; ancestry to current HEAD independently verified.
- Scope: `scripts/culvert_token_rotation.py`, user systemd service/timer,
  integration client helper, focused tests, live Culvert task import/call,
  integration runbook and live validation artifact.
- Canonical authority: `docs/schemas/culvert-jwt-renewal-contract.md`, all
  sections; `docs/schemas/feature-access-governance-contract.md`, “Culvert client
  registration and compatibility”; ADR-0106.
- Related evidence: [live validation](20261026_live_validation.md).

## User outcome and failure behavior

The operator requested automated renewal through systemd and proof that the
updated JWT is consumed on wepp2. Issuance preserves the registered submit-only
principal. A credential file is read per task invocation without caching, and
routine rotations do not restart the app or worker. A real timer-triggered
renewal and an independently inspected installed receipt substantiate this
outcome.

Invalid configured files fail explicitly; they never silently select the stale
environment token. Issuance, transport and candidate-authentication failures
produce sanitized operator errors. Pre-install failures leave the current token
unchanged. Failure after replacement/readback is reported as failure and requires
fingerprint inspection, because remote acknowledgment is not atomic with file
replacement. The existing browser's general upload-error presentation remains
outside this package.

## State and input coverage

| State | Required behavior | Evidence |
| --- | --- | --- |
| Receiver token absent | Provision a verified candidate | Direct filesystem test; real systemd provisioning at 16:42:49 UTC |
| Client file setting absent | Preserve legacy environment credential behavior | `test_client_legacy_and_configured_file_failure` |
| Configured file absent, empty or unreadable | Explicit credential error; no environment fallback | Focused missing/empty cases; reviewed OSError boundary |
| Populated valid credential above renewal threshold | No replacement | Focused no-op test; real normal service invocation retained fingerprint |
| Exactly 30 days remaining | Attempt issuance | `test_exact_renewal_boundary` |
| Structurally valid expired installed credential | Inspect and renew; do not install an expired candidate | Expired-state focused tests |
| Malformed compact JWT or invalid UTF-8 | Sanitized explicit error | COR-01 regression tests and independent direct file reproduction |
| Wrong principal/scope/audience or run claims | Reject before network installation | Parameterized identity tests |
| Symlink or nonregular destination | Reject without affecting unrelated file | Direct filesystem tests |
| Verification or replace failure | Preserve active credential; retain bounded backup when created | Verification rejection and replace-failure tests |

Inputs are considered separately from stored states: ordinary renewal, explicit
force, receiver status/install, unauthorized receiver command, HTTP rejection
and redirect. Focused tests and live probes cover these cases. Coverage is
bounded; this review does not claim every filesystem, process-kill, hardware or
network-fault interleaving was tested.

## Generated credential evidence chain

| Stage | Required semantics | Evidence and result |
| --- | --- | --- |
| Operator intent | Scheduled renewal under existing identity | Contract checkpoint and units: pass |
| Persisted configuration | Daily persistent user timer; no retained force override | Independent live `systemctl --user show`, `is-enabled`, `list-timers`: pass |
| Issuance | New jti, 90-day lifetime, unchanged principal/scope | Live receipt: iat `1793033141`, exp `1800809141`, jti `f596899cc3c647ceb440e074ee99e5c8`: pass |
| Delivery and file | Verified atomic installation on wepp2 | Live restricted SSH/receiver execution; independently checked modes 0700/0600: pass |
| Actual consumer | Same running process reads changed file through deployed helper | Worker probes PID 49 and PID 89 across separate rotations in live evidence: pass |
| API execution | Loaded credential reaches authenticated missing-file validation | Fresh worker-loaded POST returned HTTP 400 `missing_file`: pass |
| Operational result | Service succeeds and later ordinary execution skips replacement | Live forced service/timer and normal no-op evidence: pass |

The independently inspected final receipt fingerprint is
`8aeb895e2b0fcbaa713857f1be391c1a58d9b776e803adb7c7f8fc1b01907190`.
Both host operator scripts match local SHA256
`66ab5675572448c6cd7c69f8193fa70bb9463b6ffcc5c04936f86e6d36c99a53`.
The deployed client helper matches local SHA256
`84109cd6979fe42df8426bb07149856d86cce1d87cd7788d2c4072bb82bdb506`.

The initial SSH failure is useful noninterference evidence: a LAN connection
was rejected by the Tailscale-only key restriction. Explicit Tailscale DNS
selection repaired routing without relaxing authentication. The same restricted
receiver then accepted valid installation and rejected unauthorized commands
and malformed candidates.

## Findings

| ID | Severity | Description | Disposition |
| --- | --- | --- | --- |
| COR-01 | Medium | Initial client helper accepted malformed three-segment values such as `a.@@@.b`, contradicting explicit malformed-file failure behavior. | Resolved: strict base64url segments and decoded JSON-object header/payload checks; invalid UTF-8 converted to sanitized credential error. Direct reproduction and regression tests confirm rejection. |

No unresolved high, medium or low correctness findings remain in the reviewed
scope. The exact 30-day threshold test requested during review was also added.

## Verdict and limits

**Gate: pass.** Recommendation: ship the bounded renewal mechanism. Full
repository regression execution is pending at this review timestamp and remains
a separate package validation obligation; this review does not certify its
result. Focused tests, code review and real production boundary evidence support
the credential-lifecycle acceptance claim.

Highest supported claim: implemented, deployed and environment-validated
credential renewal and client consumption through actual systemd timer/service,
SSH, HTTPS and the existing container mount. No full model analysis was
submitted, no prior project repair is certified, and browser 401 presentation
is unchanged. First ordinary daily trigger is a follow-up observation.

Off-host notification is not configured; the runbook explicitly distinguishes
local journal/receipt/systemd status from notification. Monitoring receipt age
is necessary because a killed or timed-out service may leave an earlier receipt.

## Artifact observability

Credentials are secrets, not project/model artifacts, under the existing
artifact-observability exception. They must not enter public browse or project
archives. Redacted fingerprints, claims, failure/success receipts and deployment
evidence are retained in operator state and this package. Model archive tests
are not applicable because this workflow creates no model/project records.

Reviewer sign-off: `renewal_contract_correctness`, 2026-10-26 UTC.
