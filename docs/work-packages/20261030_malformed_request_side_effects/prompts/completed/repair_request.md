# Comprehensively reject malformed requests before side effects

Work in `/home/workdir/wepppy`. Execute a complete, evidence-based repair of this failure class:

> Reject malformed requests before side effects, preserving intentional empty/default requests.

This is an implementation task, not another architecture review. Investigate the shared mechanisms and all confirmed consumers, establish the contract, implement the bounded repair, run meaningful regressions and required gates, and retain evidence. Do not stop after fixing one endpoint or making the parser raise if consumers still swallow the error or mutate first.

## Baseline and prior work

At prompt authoring, HEAD was `e35d7a3e69497ddfd9709736af50107f56963584` (`Fix WEPP admission before proposed input mutation`), following contract checkpoint `525e78c9f`. Reverify current revision and working-tree state before work.

The landed WAM-01 repair covers three ordinary WEPP endpoints and two bootstrap/no-prep endpoints. Preserve it and its regression evidence:

- `docs/schemas/wepp-run-input-contract.md`, section `Admission before proposed input mutation (WAM-01)`
- `docs/work-packages/20261030_wepp_admission_before_mutation/`
- `tests/microservices/test_wepp_admission_persistence.py`
- WEPP and bootstrap route tests.

Treat prior work-package records as historical evidence; durable authority is in current canonical contracts. Create a separate package for this repair. Do not reopen the prior package or silently weaken its admission/lease/replay guarantees.

The checkout has unrelated Roads edits and research artifacts. Record initial status, preserve them, and ignore dirty `wepppy/weppcloud/routes/usersum/generated/docs_index.json`. Do not switch/create branches, deploy, submit production jobs, install dependencies, or change unrelated application behavior.

## Confirmed starting mechanisms — reverify, then reproduce

1. `wepppy/microservices/rq_engine/payloads.py::parse_request_payload` catches all JSON parsing exceptions, tries form parsing, catches those exceptions, and can return `{}`. Non-object JSON can likewise become an empty dictionary. `_normalize_scalar` leaves unrecognized boolean strings unchanged and converts arbitrary numbers by truthiness; recursive normalization can leave containers where consumers expect scalar flags.
2. `wepppy/weppcloud/routes/_common.py::parse_request_payload` uses Flask `get_json(silent=True)`, ignores non-object JSON, and falls back to form/default behavior. Its boolean normalizer has analogous permissive behavior. This is a separate implementation: repairing FastAPI alone is not comprehensive.
3. RHEM's route consumes the shared parser; `wepppy/rq/project_rq.py::run_rhem_rq` defaults omitted/null stage flags to enabled. `wepppy/nodb/mods/rhem/rhem.py::clean` removes existing run/output directories. Malformed JSON can therefore become a default execution, and an invalid nonempty string can become an enabled cleanup flag. This is static evidence; reproduce safely without running destructive production work.
4. WEPP, bootstrap, climate, landuse/soils, watershed, exports, project mutations, fork/archive, and other route families use shared or indirect payload parsing. Invalid body handling is not confined to RHEM.
5. `wepppy/microservices/rq_engine/webhooks.py::{request_options,reject_unsupported,submission_boundary}` separately reads bodies and participates in reservation/replay/cleanup. `single_input_uploads.py` imports private normalization helpers and owns bounded multipart parsing and file cleanup. These paths require explicit compatibility analysis.

Do not treat every occurrence of `silent=True`, a default, or a broad catch as automatically defective. Establish a reachable mutation/default-execution path and its intended input contract. Distinguish malformed transport, invalid supplied field values, valid omissions, and infrastructure/transport failure.

## Governance and execution

Read root and nearest `AGENTS.md` files for every touched subsystem. Use applicable `docs-maintainer` and `wepppy-tester` skills. This comprehensive multi-consumer repair requires a dedicated work package and active ExecPlan; read `docs/prompt_templates/codex_exec_plans.md` and the work-package process before authoring. Keep progress, decisions, discoveries, outcomes, and tracker current.

Read and apply:

- `docs/standards/contract-first-change-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`, especially failure-class assessment and working-behavior authority
- `docs/schemas/rq-response-contract.md`
- `docs/schemas/rq-webhook-contract.md`
- `docs/schemas/wepp-run-input-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- Current domain contracts identified by nearest guidance.

The operator authorizes the bounded intended outcome in the task statement, including equivalent confirmed consumers of this failure class. Follow required contract checkpoint sequencing and independent reviews before implementation. Do not invent additional approval requirements or repeatedly ask approval for this outcome. This prompt does not independently grant commit authority: if required checkpoint commits lack authorization, prepare the concrete checkpoint and explain the precise remaining requirement before asking. Do not bypass the ancestor-commit requirement.

Assess actual security impact, including valid-state noninterference; produce the security review artifact required by the work-package process when applicable. Delegate independent reviews when the applicable process requires them. Do not expand into auth, permissions, identity, deployment, or general security redesign.

## Required discovery artifact: consumer and contract matrix

Inventory repository-owned mutation/submission consumers across Flask and rq-engine. Start with both parser definitions, follow aliases/imports/wrappers, private normalizer consumers, webhook pre-parsers, multipart adapters, and direct JSON/form parsers that exhibit the same failure mode. Inspect callers and decorators, not just same-name matches. Scope searches to source/test trees; avoid scanning bulky run fixtures unnecessarily.

For each route or demonstrably equivalent group, record:

- Method/path, framework, parser/wrapper chain, and existing canonical contract.
- Supported media types and real UI/API callers, including legacy callers.
- Whether a genuinely absent body, empty JSON object, empty form, whitespace body, JSON null, and missing/empty Content-Type are valid and why.
- Scalar boolean fields, allowed tokens/numbers/nulls, aliases, repeated fields, list/object fields, and defaults.
- First side effect: NoDb mutation (including eager initialization), task timestamp clearing, receipt/hint replacement, webhook reservation, upload promotion, file deletion, queue enqueue, external action, or worker execution.
- Where parsing/validation errors are translated or caught, and auth/CSRF ordering.
- Tests/evidence and disposition: confirmed defect, verified unaffected, or unresolved.

Retain search boundaries and exclusions. Repair all confirmed instances of this class within scope; do not label an untested consumer unaffected. Explicitly resolve broad route catches that would turn a new validation exception into HTTP 500, HTML, success, or default execution.

## Contract decisions to settle before implementation

Write a concise acceptance matrix and rationale in current canonical documentation; use domain-specific exceptions only where real contracts require them.

1. **Transport:** Select parsing by the supported media type. Malformed declared JSON must not fall back to forms or `{}`. Non-object JSON must be rejected where the contract expects an object. Specify parameters/casing, supported `+json` types if any, missing headers, unsupported media types, invalid encodings, incomplete multipart, and empty bodies based on actual callers. Do not infer absence only from Content-Length; streamed requests may lack it.
2. **Intentional defaults:** Preserve documented `{}` and genuinely absent-body operations that intentionally run defaults, and valid empty forms where supported. Treat whitespace, JSON `null`, and missing fields separately rather than equating all falsy values. Establish route-specific null/blank semantics from the current contract and consumers before narrowing them.
3. **Boolean validation:** Preserve documented valid native booleans and legacy tokens (`true/false`, `1/0`, `yes/no`, `on/off` where accepted). Reject unrecognized supplied values rather than allowing Python truthiness. Decide arbitrary numeric, null, blank, list, and object handling explicitly. Do not accidentally apply scalar-boolean rules to legitimate collections/nested objects or change ordinary numeric/string fields through recursive coercion.
4. **Repeated keys and aliases:** Inspect existing hidden-input/checkbox patterns and multi-select forms before choosing a duplicate policy. Preserve legitimate repeated fields. Specify ambiguity handling for conflicting boolean duplicates and canonical/legacy aliases; avoid arbitrary first/last-value selection for a newly rejected ambiguous flag. Decide JSON duplicate-key behavior explicitly without adding a speculative custom parser.
5. **Errors:** Establish stable canonical client errors with appropriate existing status conventions (normally 400 for malformed/invalid input, 415 only where contracted). Include bounded field information without echoing uploaded bodies, secrets, filesystem details, or tracebacks. Keep infrastructure failures, disconnections, and cancellation distinct from malformed client input; do not catch them into defaults.
6. **Ordering:** After the existing auth/CSRF boundary, finish transport parsing and applicable structural/flag validation before business side effects. Domain validation that depends on admitted state must still respect WAM-01. Document error precedence rather than accidentally shifting auth or active-job semantics. Avoid a promise of rollback for arbitrary later computation failures.
7. **Webhook/multipart behavior:** Ensure validation precedes new callback reservation/publication when required and does not break valid idempotent replay. Preserve bounded upload parsing, source limits, duplicate-file checks, request-body reuse, and cleanup on parser errors/disconnects. Temporary upload buffering is distinct from promoting a source into project state; test cleanup and no promotion on rejection.

Do not mechanically reject all empty requests, require JSON globally, replace valid forms, enforce a universal unknown-field policy, introduce required fields unrelated to this defect, or silently change existing parameterization. If an adjacent numeric/enum error can produce the same invalid-to-default side effect, classify it and repair the confirmed instance with a bounded validator; do not turn the task into an unbounded scientific-range redesign.

## Implementation constraints

- Reuse shared parsing/normalization/error contracts, with framework adapters as needed. Do not copy a different fix into every route or add a new dependency/service/framework.
- Make invalid input an explicit, narrowly typed failure that reaches the correct client response. Audit every enclosing broad handler; a global handler is insufficient if local catches intercept it.
- Keep reads of a request body consistent across helpers; do not consume a stream twice, bypass multipart limits, or eagerly buffer large uploads to solve small JSON validation.
- Do not use blanket catch-and-continue wrappers, stringify arbitrary objects into booleans, or translate absent input and malformed input into the same sentinel.
- Keep classification/validation separate from mutation where needed. A late validation failure after an earlier field was saved does not meet the no-side-effects acceptance condition for that malformed request.
- Preserve the five landed WEPP admission consumers, callback replay identities, configuration-only batch/base updates, leases, recovery behavior, and no-prep file semantics.
- No changes to queue topology, scientific formulas/defaults, artifact layouts, runtime identity, or auth policy are authorized merely by this parser repair.

## Required validation

Tests are authorized. Use canonical `wctl` tooling, real framework request parsing, and meaningful state assertions. Maintain a traced coverage matrix linking every changed consumer/group to evidence.

### Shared parser conformance in both frameworks

Exercise actual HTTP requests, not only fake request objects:

- Truncated/malformed JSON, wrong top-level array/string/number/bool/null, invalid encoding, and appropriate nonstandard/non-finite JSON cases supported by the decoder.
- Valid object, valid `{}`, absent body, whitespace, empty form, media-type parameters, supported/missing/unsupported Content-Type, and requests without Content-Length.
- True/false in JSON and documented form/string/numeric representations; explicit false/zero must survive. Missing/null/blank behavior must match the ratified contract.
- Invalid boolean text, out-of-contract numbers, nested values, empty/single/multiple-item collections, duplicate fields, and conflicting aliases.
- Legitimate arrays, nested objects, multi-value forms, and trim-disabled strings unaffected by scalar flag rules.
- Multipart parse failures, missing/truncated boundaries, duplicate files, size errors, and clean temporary-resource teardown.
- Parser/transport failure classification: disconnects, cancellation, and operational errors are not successful default submissions.

### Route integration and no-side-effect evidence

For every confirmed mutation/submission consumer, test the rejection path through its real route and exception wrappers. Parameterized cases may cover equivalent families, but every exposed route must have a reasoned disposition.

For malformed/invalid requests assert the contracted error and no:

- Enqueue or expensive default execution.
- Changes to controller fields or persisted files, source promotion/deletion, or generated inputs/outputs.
- Completion timestamp clearing, receipt/hint replacement, or orphan callback reservation/publication.

Allow only explicitly documented operational effects such as request logging/rate accounting and cleaned-up temporary transport buffering; do not require unrelated Redis state to be byte-identical.

At minimum, exercise RHEM, ordinary WEPP, both bootstrap/no-prep consumers, one Flask mutation/default path, and actual multipart landuse/soil consumers. RHEM tests must prove invalid `clean` values cannot become cleanup and that deliberate defaults and explicit `clean=false` still work. Use disposable files/sentinels and controlled worker/queue boundaries; never test destructive requests on a production run.

Use real NoDb persistence/reload for representative rejection cases. Include a same-process follow-up valid request to show the invalid request left neither persisted nor cached proposed state. Test real framework exception translation to prevent a typed validation error from becoming 500/HTML. The contract-first standard requires direct unmocked evidence for changed safety/persistence/filesystem boundaries; parser-only mocks do not satisfy it.

For valid requests, prove successful save/enqueue, defaults, aliases, false/zero, batch/base configuration-only operation, callback replay, and upload behavior remain compatible. Re-run WAM-01 tests and preserve its prepared-input and no-prep invariants. Do not perform unnecessary expensive model runs when actual preparation/file readback establishes the changed boundary.

### Gates and evidence quality

Run focused tests first, then required substantive-code pre-handoff tests and applicable static checks. Run frontend lint/tests if frontend code changes, stub checks if public/stub surfaces change, queue graph/live-tree requirements if queue wiring changes, and documentation lint for changed docs. Do not introduce queue wiring changes merely to exercise those gates.

Read tests and fix production defects rather than weakening assertions to accept silent fallback. Review stubs for fidelity: dummy requests that cannot model malformed HTTP or mocks that bypass parser/exception wrappers are not proof. Record executed commands/results, skips, blockers, and the exact local environment. Do not claim production deployment or live behavior without evidence.

## Completion and handoff

Keep the ExecPlan, tracker, canonical contracts, and affected user/operator/developer documentation current. Obtain required independent contract and final reviews, disposition findings, and retain concise artifacts.

Final handoff must include:

- Shared root causes and the final transport/boolean/default contract, with exact file/section references and rationale.
- Consumer/state coverage matrix, including confirmed repairs, verified unaffected cases, and explicit unresolved boundaries.
- Preservation of landed WAM-01 behavior and valid empty/default/form/webhook/upload workflows.
- Test/gate results and no-side-effect evidence from real persistence and request handling.
- Any blocker or residual risk, with precise limits on completeness claims.

Do not close this task with only a strict parser while routes still mutate before validation, swallow the new exception, or allow malformed requests to reach default execution. Do not claim all repository validation is solved: close this defined failure class across its confirmed consumers.
