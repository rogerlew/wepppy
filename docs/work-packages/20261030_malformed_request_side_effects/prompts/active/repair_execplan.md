# Reject malformed requests before side effects

This is the active MRS-01 ExecPlan. Maintain it according to
`docs/prompt_templates/codex_exec_plans.md`, including every living section below.

## Purpose / Big Picture


A malformed request must produce a bounded client error without changing a
project, deleting output, promoting a source, reserving a callback or starting
work. Valid empty/default requests and existing JSON/form callers must still work.
The task covers both WEPPcloud Flask and rq-engine FastAPI and all confirmed
consumers of invalid-to-default parsing, not just RHEM or shared helper functions.

## Progress


- [x] (2026-10-30) Reverified baseline HEAD and recorded unrelated dirty files.
- [x] (2026-10-30) Read applicable root/framework guidance, contract-first/work-package standards and documentation/testing skills.
- [x] (2026-10-30) Reproduced fallback with real HTTP decoding in both production parsers without project mutation.
- [x] (2026-10-30) Independent read-only Flask and RQ source audits identified direct/indirect consumers and compatibility exceptions.
- [x] (2026-10-30) Prepared canonical contract, source inventory, consumer/state matrix and checkpoint decision.
- [x] (2026-10-30 23:37 UTC) Both independent contract reviewers approved after all medium/high findings closed.
- [ ] Obtain explicit checkpoint commit authority; commit only the accepted checkpoint and record ancestor revision.
- [ ] Implement shared classification/validation, adapters, enclosing catches and all confirmed early-write fixes.
- [ ] Run actual route/persistence/multipart/WAM-01 regressions and required broad/static/doc gates.
- [ ] Complete independent correctness, QA and security review; update all evidence and handoff.

## Surprises & Discoveries


Both production parsers returned `{}` with HTTP 200 for truncated JSON, array,
null and whitespace in the isolated HTTP probe. Invalid clean text survived;
clean=2 became true. `artifacts/parser-baseline.jsonl` retains exact responses.
The RHEM worker defaults missing/null stages to enabled, linking parser fallback
to destructive cleanup without needing to run production work.

The required independent audits found webhook-only body guards on default
operations, direct Flask parsers, undeclared WEPP `delete_after_interchange`,
Omni filesystem recovery before parsing, upload promotion before later field
validation, and invalid numeric values silently omitted. Strict shared parsing
alone cannot close the task. Legitimate Omni arrays, field-null clearing and
route-specific null/blank boolean semantics require explicit preservation.

## Decision Log


2026-10-30, Codex: execute a separate MRS-01 package; WAM-01 is immutable history.
Its current canonical leases/replay/no-prep contracts remain authoritative.
The user explicitly authorizes bounded remediation and tests, but their prompt
withholds commit authority. Prepare and independently review the concrete checkpoint
before requesting that authority; do not edit implementation beforehand.

2026-10-30, Codex: select transport by media type, preserve zero-byte/default
operations and legacy forms, reject malformed bytes and invalid supplied scalar
flags before business effects. Preserve per-domain null/blank semantics and
strict native-boolean exceptions. Keep existing decoder duplicate-key behavior
rather than adding a custom parser. Resolve distinct alias/form conflicts explicitly.
Rationale and precise matrix live in `docs/schemas/request-payload-contract.md`.

## Outcomes & Retrospective


The reviewed checkpoint is ready; implementation awaits explicit checkpoint commit
authority and its ancestor commit. Documentation lint passes. No production code is
changed, no repair is claimed, and no deployment or production jobs were run.
A major risk is breadth hidden behind webhook/decorator/direct-parser helpers;
retain per-consumer evidence rather than relying on a parser-only green suite.

## Context and Orientation


Work in `/home/workdir/wepppy`, baseline
`e35d7a3e69497ddfd9709736af50107f56963584`. `payloads.py` under
`wepppy/microservices/rq_engine/` handles async JSON/form input; Flask uses
`wepppy/weppcloud/routes/_common.py`. Both currently mask invalid JSON into an
empty dictionary and recursively coerce boolean values. Empty dictionaries trigger
legitimate default execution at several consumers. `webhooks.py` reads bodies
separately, and `single_input_uploads.py` owns bounded upload streams and cleanup.
The latter must remain the sole multipart reader on landuse/soil build paths.

A business side effect is a controller/file change, source promotion, cleanup,
completion timestamp clear, replacement receipt/hint, callback reservation,
enqueue or external action. Existing request locks/logging/rate accounting and
cleaned temporary transport buffering are operational effects, not a promise of
byte-identical Redis state. A route may load optional state eagerly; that load
must be inspected for creation/recovery before treating it as read-only.

## Plan of Work


Milestone 1 prepares the contract checkpoint. Retain starting status, source
searches and safe reproduction. Update `docs/schemas/request-payload-contract.md`
and affected current contracts, not historical packages. Complete
`artifacts/consumer-matrix.md` and `20261030_contract_decision.md`. Obtain two
independent read-only reviews, disposition findings, lint docs, then ask for
checkpoint commit authority if still absent. Commit only package files and the
listed canonical amendments, selectively including this package's tracker entry
without unrelated dirty Roads changes. Record the resulting SHA in tracker and
verify it is an ancestor before implementation. The prompt does not authorize
committing implementation either; request only necessary scope explicitly.

Milestone 2 introduces shared framework-neutral transport/flag validation and a
narrow typed exception, reusing current dependencies. Keep adapters for Flask and
FastAPI. Do not globally read request bodies in middleware before auth or buffer
large uploads. Classify actual body/media, reject malformed JSON/nonobject input
on object routes, preserve domain list adapters, and validate raw scalar flag
shapes before recursive normalization. Preserve known null/blank policies and
nonflag normalization. Handle field repeats/aliases without arbitrary selection.
Make webhook readers reuse validated payload/form state and preserve receipt digests.

Milestone 3 follows every matrix consumer to its first effect. Translate the typed
exception explicitly through local catches and Flask auth/decorator boundaries.
Move parsing and independent structural/flag validation ahead of eager creation,
NoDir recovery and writes. Stage supplied multi-field values before any assignment;
validate mode/mapping/file requirements and numeric conversions before promotion.
Keep state-dependent WEPP validation within existing admission leases. Validate
all confirmed direct-parser and webhook-only default routes as well as shared
parser consumers. Preserve special JSON/list/raw/form endpoints and existing
required-field/status contracts. Resolve all remaining candidate dispositions
with evidence; do not mark untested paths unaffected.

Milestone 4 proves rejection and compatibility using real HTTP frameworks and
business routes. Use disposable run fixtures and real NoDb persistence/reload,
then send a valid request in the same process to expose stale caches. Inspect
RHEM output sentinels at controlled worker boundaries, multipart spools and
promoted sources, timestamps and callback receipts. Preserve WAM-01 contention,
replay, configuration-only batch/base and no-prep prepared-file evidence. Run
focused tests before the full suite and independent final reviews. Update user,
operator and developer guidance with exact valid/error behavior in the same change.

## Concrete Steps


From the repository root, the baseline probe command is:

    wctl exec weppcloud python /workdir/wepppy/docs/work-packages/20261030_malformed_request_side_effects/artifacts/reproduce_parsers.py

It currently prints both framework statuses 200 and empty payloads for malformed
JSON. This is baseline evidence, not a success expectation after repair. The dev
container is already running; do not start containers or install dependencies.
Use the docs-maintainer skill's `wctl doc-lint --path <file>` and spelling preview.
Before implementation tests, read `tests/AGENTS.md` and any nearest controller
or helper instructions for newly touched files. Use `wctl run-pytest` throughout.

Start focused validation with both framework parser/route suites and the existing
`tests/microservices/test_wepp_admission_persistence.py`, RHEM, WEPP, bootstrap,
landuse/soil and webhook route suites. Add the missing real HTTP/persistence cases
in the owning test directories. Record exact test paths/commands/results as they
are created; do not claim a suite exists before writing it. Required broad gate:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

If public/stub interfaces change, run relevant stubtest and check-test-stubs.
Frontend and queue-wiring edits are not planned; if required, apply their gates
and document scope. Keep all executed evidence in package artifacts.

## Validation and Acceptance


Exercise malformed/truncated/wrong-top-level/non-finite/invalid-encoding JSON,
empty body/object/form, whitespace, Content-Type casing/parameters/+json/missing/
unsupported, and missing Content-Length. Exercise native and legacy flags,
false/zero, null/blank/missing policy, JSON containers, repeated form values and
aliases. Preserve legitimate nested/list/raw CSV fields and intentional default
operations. Inject disconnect/cancel/operational faults distinctly from client
syntax failures. Multipart tests must verify actual completion detection, bounded
limits, duplicate file rejection and closed temporary resources without promotion.

Every confirmed route must return its canonical JSON client error with no business
effect. Include real NoDb reload/cache follow-up and file readback at representative
boundaries, not mocks of the safety boundary. WAM-01 tests must still prove admitted
prepared inputs survive rejected competing changes and no-prep files are reused.
No full model run is necessary to prove parsing/preparation boundaries; no claims
about new scientific outputs follow from these tests. Required independent final
correctness/QA/security findings must be closed before claiming local completion.

## Idempotence and Recovery


Use temporary projects, bounded requests and controlled enqueue/external-action
boundaries. Re-running tests may only alter disposable fixtures. Never issue
malformed requests to a production run. Keep unrelated dirty files intact; never
reset the workspace or switch branches. If a gate fails, retain the command,
error and affected coverage and continue independent work. Lack of checkpoint
commit authority prevents implementation; uncommitted documentation is insufficient.

## Artifacts and Notes


The operator prompt is retained as `prompts/active/repair_request.md`. Baseline
status, HTTP probe, source inventory, consumer/state matrix, contract decisions,
reviews and validation logs are under this package's `artifacts/`. Paths resolve
relative to `docs/work-packages/20261030_malformed_request_side_effects/`.
Every milestone updates this plan and `tracker.md`; update PROJECT_TRACKER without
including unrelated edits in a task commit.

## Interfaces and Dependencies


Use existing Flask/Werkzeug, FastAPI/Starlette, python-multipart and canonical
response helpers. A shared narrowly typed request-validation failure must carry
only a bounded public code/message/optional field reason; adapters map it to HTTP
400 JSON. Preserve `parse_request_payload` caller compatibility except the ratified
invalid-input rejection. Keep request body/form reuse explicit and single-input
upload limit ownership intact. No new persistence schema or external dependency.

Revision note, 2026-10-30: created after safe reproduction and independent source
audits; checkpoint review and authority precede implementation.

Revision note, 2026-10-30 23:38 UTC: both independent reviews approved; reconciled
clipping contract authority and completed doc gates. Only checkpoint commit
authority now blocks source implementation.
