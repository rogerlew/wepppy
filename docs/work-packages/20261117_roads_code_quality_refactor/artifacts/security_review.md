# Roads refactor security review

## Findings and verdict

**Source review: pass; no high, medium, or low security findings identified.**
The new diagnostic regression passed. Final package security acceptance remains
pending independent QA disposition and exact-candidate native/project evidence. This is
not deployment approval or a claim that those outstanding gates passed.

The review found no new route, authentication bypass, filesystem authority,
subprocess transport, network egress, or persistence ownership. The intentional
logging addition uses the existing sanitizer and bounded text while retaining
legacy diagnostic-list continuation.

## Metadata

Reviewer: `/root/roads_security`, independent security reviewer, 2026-11-17 UTC.
Package: `docs/work-packages/20261117_roads_code_quality_refactor/`.
Base: `96555f2f95326350d2d7007c19327378ea831ab0`.
Initial source review preceded execution commit
`01dca0d28d223e7957842225c16e88601cca60ba`. The current delta review is against
that HEAD with literal `__all__` declarations added to six internal modules.
No executable bodies changed in this delta. The exact reviewed production and
new test bytes are bound in [security_source_manifest.json](security_source_manifest.json).
Subsequent source edits need delta review; a matching HEAD alone is insufficient.

Related evidence: [correctness review](correctness_review.md),
[baseline validation](baseline_validation.md), and
[characterization matrix](characterization.md). Independent QA and final native
candidate evidence are not yet available to this review.

## Security triage and threat model

Dedicated security review is required; retain the package's **high** triage
because code motion crosses upload-derived inputs, generated paths, native
execution, and result publication. High triage does not mean a vulnerability was
found. The intended scope is faithful extraction, with no added dependency,
privilege, service, process identity, auth policy, or deployment topology.

Uploaded attributes and restored project state remain untrusted inputs at the
existing validation and lifecycle boundaries. Native inputs are generated from
validated project intent; native executables and callable dependencies remain
selected by the server/facade. The new helpers are internal Python functions,
not user-callable endpoints or a configurable plugin interface.

## Surface checks

| Surface | Assessment and evidence |
| --- | --- |
| Authentication/session/CSRF | No route, feature access, session, CSRF or queue admission code changed. Existing facade lifecycle decorators are identical to baseline. |
| Input validation | Input helper bodies preserve baseline validation, enum/default resolution, required unrutted fields and explicit error contracts. No relaxed validation or new fallback was added. |
| Filesystem/workspaces | `_pass_routing` preserves link/copy, baseline diagnostic exclusion, isolated workspace clearing, PASS header verification and native combiner calls. Path operations were moved with identical body ASTs. No additional paths are accepted. |
| Retained parameterization | `_parameterization_support` preserves saved-state distinction, bounded allowlisted materialization through the unchanged parameterization module, path containment/readback, input hash checks, and completed-record requirements. |
| Native subprocess boundary | `_native_runner` receives `make_hillslope_run` and `run_hillslope` directly from the facade, not from request data. Selected binary and pass-family arguments are unchanged; no shell, eval, dynamic import string, or command interpolation was added. Watershed runner calls remain in the facade. |
| Persistence/concurrency | NoDb class/import identity, method signatures/decorators, upload rollback and lifecycle retention are preserved. Execution result/terrain/trace records remain local and are never attached to serialized controller state. Existing status locks, publication order and final transient cleanup remain in the facade. |
| Queries/output safety | Existing query/parameterization body ASTs remain identical. Historical readback/path admission and sanitized diagnostic behavior are unchanged. No template/HTML rendering or download surface changed. |
| Logging/secrets | New diagnostic-list warning sanitizes candidate and exception strings with `safe_text(current_profile(WORKER))` before truncation to 160/240 characters, emits no traceback, and retains fixed format text. Existing contributor errors continue through sanitized diagnostic records. No secrets or credential transport added. |
| Queue/worker/retry | No enqueue/dependency edges or worker routing changed; RQ graph regeneration is not applicable. Contributor failure aggregation and failed-attempt publication prevention were inspected against baseline. |
| Agent/runtime tooling | Recorded validation uses isolated `wctl run --rm --no-deps --pull never` containers, explicit task bind and canonical checkout nonce verification. Shared services are not remounted/recreated. This reviewer started no test container or production operation. |
| Network/supply chain/CI | No new outbound call, package dependency, registry publication, CI permission, secret mount, or deployment change. |

## Valid-state noninterference

The correctness review enumerates absent, empty, populated, supported legacy and
malformed states. This review separately checked security boundaries:

- Absent parameterization remains an unbound preview; inspection does not bind
  defaults or write project state. Present null/malformed state remains explicit.
- Empty eligible contributors still follow the existing baseline-equivalent
  path and current policy-marker requirements; no new blanket rejection exists.
- Populated inputs retain all four design branches, candidate ordering, native
  paths, baseline/roads isolation, and model-output publication sequence.
- Legacy/historical results retain existing admission and inspectability rules.
- Malformed retained assets, symlink aliases, missing/changed provenance and
  incomplete publication still pass through the original rejecting helpers.
- Upload cancellation and pre/post-commit rollback semantics are unchanged.

Security inspection does not replace the correctness or native parity gates.

## Evidence inspected

An independent AST comparison found no added/missing `Roads` methods and no
signature, return-annotation, or decorator differences. All **87** named moved
method bodies match their original method body ASTs. Initialization, hydration,
enable/save/upload, preparation currentness, error recording, summary and saved
input-query bodies remain unchanged where not delegated. Preparation/execution
coordinators received manual lifecycle, data lifetime, and publication review.

Existing direct regression anchors include `test_materialization_refuses_symlink_parent_and_input`
in `tests/nodb/mods/test_roads_parameterization.py`, historical symlink/changed
publication tests and upload commit-failure tests in `test_roads_controller.py`,
and required-resource/provenance admission tests in `test_roads_lifecycle.py`.
The integrator's `/tmp/roads-refactor-validation/m3-execution.log` reports
390 passed, one skipped for the integrated execution selection. Earlier staged
passes and baseline native results do not independently qualify later source.

The reviewer added only `tests/nodb/mods/test_roads_execution_diagnostics.py`,
with two meaningful boundary checks requested by the integrator: valid duplicate
membership updates without warnings, and injected diagnostic-list failure with
real sanitizer/profile and log readback proving continuation, bounded output,
and synthetic-secret redaction. No production source was edited by this reviewer.
The coordinated checkout-verified run passed **4 tests**, including both new
security tests and two mixed execution-boundary tests, in 10.08 seconds.
Receipt: `/tmp/roads-refactor-validation/execution-boundaries.log`; its SHA-256
is retained in the security source manifest. This is direct sanitizer/log evidence,
not merely a mocked sanitizer assertion. The later export-only delta leaves all
tested method bodies unchanged.

## Artifact observability and completion limits

Existing generated directories, manifest envelope, summary/provenance paths,
failed-attempt evidence and current/historical result admission are retained.
No new hidden-only artifact or archive exclusion is introduced. The original
upload and prior results remain governed by unchanged lifecycle retention.
Baseline native matrix/project receipts are baseline evidence only. Final
candidate acceptance must still show generated/consumed input and output parity,
source/binary identity, successful project behavior, explicit road/fill fit
rejection, source isolation, and fresh report admission. New browser/archive execution is not
claimed by this source-only review; unchanged underlying mechanisms and retained
coverage must not be misrepresented as a fresh deployment exercise.

## Sign-off and remaining gates

Security reviewer: source assessment accepted, `/root/roads_security`,
2026-11-17 UTC. Unresolved code findings: high 0, medium 0, low 0.
Package-owner final acknowledgment and closeout remain pending final native/project
validation, independent QA, final source-hash comparison, and any resulting
finding disposition. No risk-acceptance exception has been requested or granted.

## Export-only delta review

Reviewed 2026-11-17 UTC: `_constants.py`, `_execution.py`, `_point_source.py`,
`_unrutted_execution.py`, `_unrutted_native.py`, and `_unrutted_planning.py` now
explicitly list their internal module exports. Independent AST comparison
against `01dca0d28` is identical after removing those literal assignments. No
dynamic export mechanism, externally selected callable, new import execution,
or changed runtime body is introduced. This delta is accepted with no findings.
The source manifest preserves the earlier review snapshot and binds current bytes.
