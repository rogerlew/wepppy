# Native SBS upload security review

## Findings and current disposition

| ID | Severity | Finding and evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| SNU-I01 | Medium, contract/state integrity | At initial review, `Baer.showSbs()` called the shared renderer in map-error branches, replacing Summary; map startup could also clear concurrent summary failure Details. | Fixed: all map failures use the bounded SBS renderer; opt-in map error propagation retains the original error; source-keyed map/summary failures survive the sibling request's success and clear on their own recovery. Reviewed the 28-test completion-order/recovery run and repeated direct browser containment/retention checks. | Closed. |
| SNU-I02 | Medium, request admission availability | Repeated proxy uploads exposed a copied HTTP context retaining a released lifecycle lease; a new request checkpointed that lease and returned 409. The owner retained the failure stack in `admission_failure_stack.log`. | Fixed: HTTP middleware explicitly requests a fresh lifecycle lease; nested operations retain inherited ownership checks. Independent real Redis/file-lock checks and repeated proxy uploads verify recovery and continued exclusion of competing or lost owners. | Closed. |

No XSS, resource-loading, navigation, custom-element execution or native failure
suppression defect was found in the implemented renderer/native wrapper changes.
Contract findings SNU-C01 and SNU-C02 are closed by the implementation.

No unresolved medium/high findings. **Gate status: pass.** The retained
authenticated proxy workflow, direct browser containment checks and focused
regressions close the review conditions. No risk acceptance is recorded.

## Scope and ancestry

Independent reviewer: Codex `contract_security`, 2026-09-10.
Contract checkpoint `328db92dd` is an ancestor of current HEAD.
Reviewed `sbs_error.js`, modified Disturbed/BAER upload and summary handlers,
shared HTTP/error adapter behavior, the SBS map helper's opt-in error propagation,
batch native-failure translation, `sbs_map.py`, added tests, and
[native refresh provenance](native_refresh.json).
Final review also covers the always-present filename display: the template
escapes the stored name, and JavaScript creates a code element with textContent
instead of interpolating the name into HTML. The filename-injection regression
passes; successful removal restores the empty-map message.
Security impact remains **high** because gateway HTML enters an authenticated
page as formatted content. Native-required execution adds no new external
dependency, auth scope, input path, queue edge or network destination.

## Direct security evidence

The reviewer executed [security_browser_probe.cjs](security_browser_probe.cjs)
against the actual `sbs_error.js` and `control_base.js` in Chromium on an isolated
`about:blank` page. No credentials, live runs or project data were used.
[Passing output](security_browser_probe.log) proves:

- Script and custom-element execution counts are zero, including a customized
  built-in `<p is=...>` payload.
- No network requests or navigation occur during parsing or after insertion;
  resource/script/CSS/iframe/base/meta/SVG payloads are discarded.
- Inserted formatting elements have no source attributes. Forms, SVG/MathML and
  custom-element subtrees are absent; entity-encoded markup stays text.
- The actual shared renderer preserves literal JSON markup without Summary
  targets. HTML Details reveals correctly; accepted Summary and hints survive.
- A 10,000-level input completes without recursive traversal failure.
- Re-rendering a retained hostile map error after summary recovery remains inert;
  recovery of that map clears Details. The updated probe passed against the
  final source-keyed helper. The probe records hashes of the exact executed
  sources and the Chromium version.

The source uses a detached template, fresh native HTML elements/text nodes, a
finite allowlist and a namespace check. It copies no attributes or source nodes.
Only raw string failure bodies labeled `text/html` receive HTML treatment.
The five native wrappers require callable owned APIs and propagate execution
exceptions. The summary cache does not cache raised failures. Missing color-table
metadata remains distinct from a missing native API. Duplicate Python raster
engines have been removed; scalar/custom-palette helpers remain.

## Validation and limits

The reviewer read passing [focused controller results](controller_tests.log),
[78 Python tests](python_tests.log) including native failures, source-mask
regressions and batch upload failure, [four Rust tests](rust_tests.log), and
final [Wallow pixel/geometry/NoData parity](native_parity.log). Native export took
0.57 seconds in the final recorded run. The final [JavaScript suite](npm_tests.log)
passes 110 suites and 852 tests, including filename text safety; the
[two template checks](template_tests.log) also pass.

The [proxy browser script](proxy_browser.cjs) and [passing log](proxy_browser.log)
record a real authenticated Wallow upload on a newly API-created Builder project:
HTTP 200 in 5.597 seconds, accepted filename, rendered classification table and
successful map response. Injected HTML 504 displays formatted Details, preserves
Summary and does not enter the upload hint. Retry succeeds and clears Details;
filename and table persist after reload. Three additional consecutive uploads
also return HTTP 200 after the admission fix. The failure is deliberately injected
in the browser; the successful uploads and map/summary requests use the real
development proxy and serving processes. Screenshots are retained with this
evidence. The test does not overwrite fair-division's input map.

The prior installed binary was stale. The final development binary is
`69119d84349a1e60d4290aa583c79419a0f22ecac416f3c26b60ada34a8eec45`.
`native_refresh.json` records the source commit plus the finite/integral NoData
metadata correction, before/after binary hashes, build command, Python ABI and
GDAL versions. [Development reload](development_reload.log) confirms the serving rq-engine service
restarted; the implementation owner confirms this followed the final native
installation. The reviewed Rust correction prevents fractional/nonfinite
metadata from being cast into an unrelated valid class; it adds no execution
or filesystem surface. The subsequent real proxy workflow is passing.

The full suite is excluded by explicit operator instruction. The recorded native
refresh affects the development shared release mount; it is not evidence of
installation or parity on other hosts. No production deployment was reviewed.

## HTTP request admission conformance review

The bounded extension reviews `rq_engine/__init__.py`,
`rq/submission_recovery.py` and its stub against the canonical
`rq-engine-agent-api-contract.md` HTTP request admission isolation section.
The retained stack establishes that the new HTTP request inherited a released
lease, rather than encountering a currently active competing owner.

`rq_submission_lock` retains `inherit_lifecycle=True` by default. HTTP admission
alone passes `False`, requiring fresh Redis lifecycle/resource locks and the
existing file lock. Nested operations continue to share the current request's
lease and reject lost ownership. Authentication, request-body checkpoints,
lock namespaces, lease timeouts, fork-state checks and error contracts remain
unchanged. The diagnostic logs the run identifier and exception stack, without
request bodies, authorization headers or tokens. The stub also now declares
the already implemented `on_job_id` parameter.

The reviewer independently executed [security_admission_probe.py](security_admission_probe.py)
with actual Redis and file locks, isolated random keys and a temporary lock
directory; it did not modify project data. The [passing log](security_admission_probe.log)
records the source hash and verifies stale-context reproduction, two fresh
request acquisitions, rejection of an active competing owner, rejection of a
lost parent lease, file-lock exclusion after Redis ownership loss, cleanup and
subsequent recovery. The retained [10 admission tests](admission_tests.log),
[helper stubtest](admission_stubtest.log) and final repeated proxy workflow pass.

**Admission extension disposition: pass.** No unresolved medium/high security
findings remain, and no risk acceptance is needed. The existing full-suite and
deployment limits above still apply.

Reviewer changes are limited to review artifacts and the independent browser
and admission probes and logs. No runtime code was edited by the reviewer.
