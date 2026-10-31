# MRS-01 final security review

Reviewer: independent `/root/flask_contract_review` (`security_reviewer`).
Date: 2026-10-30. Security impact: **high**; dedicated review required because
public mutation, upload and token/spawn boundaries change input handling.

## Findings and verdict

**Security gate: pass for the reviewed implementation.** No unresolved high or
medium security findings remain in this scope. This supersedes the implementation
hold in [the initial security review](20261030_security_review.md). Full-suite and
consumer-matrix completion remain package gates; this is not deployment approval.

| Finding | Severity | Exploit path and final disposition | Evidence |
| --- | --- | --- | --- |
| SEC-01 | High | Malformed bodies became defaults, or invalid flags enabled mutation. Closed: typed transport/scalar rejection reaches bounded JSON 400 responses before the reviewed business actions; intentional omissions and declared sentinels remain distinct. | `wepppy/request_payload.py`, `routes/_common.py`; `test_request_payload_conformance.py`, Flask route matrices, agent and batch tests |
| SEC-02 | High | Earlier config fields or optional-controller initialization could persist before a later request error. Closed for reviewed Flask boundaries: PATH validates proposed config before creation; Geneva validates schema and supplied/merged config before setters; WATAR validates configured concentrations and both reservoir fields before `parse_cc_inputs`; batch validates all applicable directives before update. RQ upload/application findings are independently closed in the correctness review. | `test_optional_payload_persistence.py`, `test_batch_runner_endpoints.py`, `test_project_bp.py`, terrain file tests; [correctness review](correctness-final-review.md) |
| SEC-03 | Medium | Local broad catches could translate the new error into 500, HTML or a success/default path. Closed: narrow translation/rethrow precedes broad boundaries; real registered route tests exercise canonical error mapping. | `utils/helpers.py`, `routes/_common.py`, changed route catches; framework conformance and route matrices |
| SEC-04 | High | URL-form encoding validation buffered an oversize request before the existing memory limit. Closed: declared oversize rejects before any read; unknown length reads at most the limit plus one byte. | `wepppy/weppcloud/request.py`; `test_flask_url_form_limit_precedes_encoding_buffer` checks both read counts |
| SEC-05 | Medium | CSRF's early form read could erase malformed multipart evidence and let JSON-only routes execute defaults. Closed: `PayloadRequest` retains the typed error; both route parser adapters honor it after the auth/CSRF boundary. | `test_flask_csrf_early_form_read_retains_parse_failure`, including JSON-only and form adapters with real Flask-WTF |
| SEC-06 | Medium | Partial multipart parsing could leave temporary streams open on size/disconnect failures. Closed: cleanup covers malformed input and preserves propagation of size, cancellation and operational errors. | `StrictFormDataParser`; actual stream tests in `test_request_payload_conformance.py`; RQ cleanup review |

Contract null/blank, recorder-envelope and Geneva native-boolean findings from the
initial review remain closed. No risk acceptance is used to close these findings.

## Scope and contract authority

Reviewed shared validation, the Flask request adapter and route wrappers, and
changed Flask consumers including project, PATH, Geneva, terrain, batch, WATAR,
bootstrap, recorder, agent sessions and operator-token body detection. The final
[correctness](correctness-final-review.md) and [QA](qa-final-review.md) artifacts
were read before this verdict; they supply the independently assessed RQ,
upload-promotion, WAM-01 and resource evidence outside this review's primary Flask
scope. Unrelated Roads, research, Usersum and binary changes are excluded.

Observed HEAD is `ca28085acb8171be6e77aa03d24754521c9e04d1`, following initial
contract checkpoint `3ab204e9c`. The committed request-contract blob is exactly
`b2be0cbb021c31f38b89651b4e5c83f0349b04e9`, independently approved in the
[follow-on decision](followup-contract-decision.md). Operator authority and the
implementation owner's restoration-after-checkpoint record are documented there;
this review grants neither commit nor deployment authority.

## Surface checks and valid-state preservation

- **Auth/session/CSRF:** existing route guards and role checks remain. Parser
  errors do not bypass them; actual Flask-WTF tests preserve rejection precedence.
  Agent TTL validation occurs before token mint/spawn or publish. Existing zero,
  null and empty-string defaults follow the approved bounded contract.
- **Input/output/logging:** errors contain a fixed message/code and, where used,
  a declared field name. Rejected bodies, credentials, paths and tracebacks are
  not echoed. JSON-only routes retain their media boundary; recorder nested
  events and legitimate terrain collections retain their shapes.
- **Files/data/cache:** real PATH/Geneva tests cover absent state, valid creation,
  unchanged files after rejection and a valid follow-up. WATAR uses real Ash
  persistence; project and batch tests compare saved/cache state and subsequent
  accepted changes. Terrain tests compare actual config files. These supplement
  route tests that control auth, queue or external boundaries.
- **Resource/queue/locking:** parser buffers retain existing limits; failed
  temporary uploads close. No new queue topology, execution identity or lock
  policy is introduced. Existing WAM-01 admission/replay and no-prep behavior is
  assessed by the correctness review and its retained regression suites.
- **Secrets/egress/supply chain/tooling:** no new credentials, dependencies,
  external destinations, deployment wiring or agent permissions are introduced
  by the reviewed repair. Existing agent token/spawn capabilities remain behind
  their original authorization boundary.
- **Artifacts:** the repair creates no new user artifact layout or hidden output
  store. Existing accepted source/output retention is checked by byte comparisons
  and real upload/generated-raster readback in the correctness evidence. No live
  browser, deployment or production-run observation is claimed.

## Evidence and remaining package gates

Inspected `/tmp/mrs-followup-tests.log`: **175 passed**, including framework
conformance, agent TTL, real optional-controller/WATAR persistence, project
mutations and batch directives. Earlier `/tmp/mrs-final-boundaries.log` records
**220 passed** for the broader parser/upload/route boundary selection, also
assessed by correctness and QA. Counts are separate invocations, not a unique
test total. The QA reviewer independently reran the two URL-form read-limit tests.
Earlier reviewer probes directly reproduced and then confirmed closure of the
CSRF-consumed-body and partial-upload cleanup defects using disposable requests.

At sign-off `/tmp/mrs-full-final.log` is still running. The owner must retain its
final result and reconcile the [consumer matrix](consumer-matrix.md), including
unexecuted/disposition limits, before package closeout. The old
`/tmp/mrs-flask-matrix.log` contains an earlier failed invocation and is not used
as passing evidence here. Representative persistence tests do not prove every
discovery-index route independently; route matrices likewise do not establish
every controller's persistence behavior or production identity parity.

Residual risk is limited to those stated evidence boundaries and future framework
upgrades affecting private form/stream integration. No arbitrary rollback after
later storage, queue or model failures is promised. No unresolved security defect
is being accepted through these limits. Security sign-off: `/root/flask_contract_review`.

## Addendum: rq-engine session body detection

The final inventory identified the same header-only absence assumption in
`session_routes._parse_optional_json_payload`. Independent review approves its
narrow replacement with `await request.body()`: actual empty bytes retain the
default, while nonempty streamed requests undergo the existing specialized JSON
validation. Starlette caches those bytes for the subsequent `request.json()` call.
This restores the committed request contract's prohibition on inferring absence
from Content-Length; it adds no field or transport policy.

Auth, same-origin cookie checks and workflow authorization still precede parsing.
Parsing precedes idempotency reservation, token issuance and marker storage.
Existing `application/json`-only, null-as-empty, object-shape and
`validation_error` behavior is retained. No new security findings result.

Inspected `/tmp/mrs-session-final.log`: **59 passed**. The new registered-route
test removes Content-Length from malformed JSON, observes HTTP 400 and no marker
storage, then successfully issues a token for a genuinely empty request. Token
issuance ordering is additionally established by source inspection; the test's
effect spy targets marker storage. Security verdict remains **pass** within the
scope and package-gate limits above.
