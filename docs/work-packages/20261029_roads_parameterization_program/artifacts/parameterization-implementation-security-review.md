# Roads parameterization implementation security review

Status: **PASS — final source and local runtime security review**.
Current disposition: [final independent review](#final-independent-review-2026-11-03).
Accepted ancestor: `73b5da4ac`; approved proposal: `9532a2968`.
Initial reviewer: independent `parameterization_impl_security` agent.
Final reviewer: independent `/root/security` (`security_reviewer`).

Scope: retained baseline model and raw/native validation, Roads mutation and
materialization, result admission, dedicated route/view/controller, and valid-state
noninterference. Review follows the approved repository/project contracts, NoDb
persistence and existing auth/CSRF/readonly boundaries. Earlier sections retain the initial findings and intermediate checkpoints;
the final independent review below supersedes their pending dispositions.

## IS-01 — medium: invalid first Save can mutate initialization state

Initial new route called `_ensure_roads_controller` and `set_enabled(True)` before
validating the request. An invalid nested override could create a controller or
enable a mismatched disabled controller. This violates rejection-before-mutation
and changes working enabled-state authority.

Requested remedy: validate the complete prospective first-use payload without
initializing state, then create only for an authorized enabled absent project.
Preserve existing enable mismatch as an explicit error, not an implicit repair.
Add invalid first-Save and existing-disabled preservation regressions.

Owner reports route now calls `Roads.validate_initial_params` before absent
creation and uses ordinary synchronization for an existing controller. Final source
and regression readback pending.

## IS-02 — medium: non-strict legacy parser accepts malformed retained management

Confirmed using the actual container and owned model: append an active
`999 999 999` record to `managements/3inslope.man`, recompute the asset hash and
baseline identity, then call `validate_state`. The initial implementation accepted
it (`ACCEPTED_TRAILING_NATIVE_RECORDS`). `Management._parse` only enforced complete
consumption and count/reference consistency in strict mode, while `read_management`
selected non-strict mode to support the valid legacy 97.3 baseline.

Requested remedy: bounded owned structural validation for 97.3, including trailing
records and references, without changing retained source or emitted numeric bytes.
Do not treat parser success or a self-consistent hash as trusted grammar. Owner is
coordinating a narrow owned-parser mode rather than adding a duplicate grammar.
Final source and malformed/default parity regressions pending.

## IS-03 — medium: finite Python numbers can overflow native representation

Initial raw soil validation checks horizon depth and CEC for Python finiteness,
but only the four editable drivers undergo native REAL conversion validation.
Thus raw finite values such as 1e308 can pass the restored-source validation and
become nonfinite native inputs. Management raw numeric validation has the same
Python-finite-only distinction.

Requested remedy: reject native-unrepresentable numeric fields before
materialization, using actual numeric representation rather than inventing
scientific ranges. Add a finite-double/native-infinite regression. Owner notified;
final resolution pending.

## Positive controls inspected

Exact 18 asset-name allowlist, per-asset/aggregate byte limits, UTF-8/NUL checks,
asset hashes and deterministic baseline identity are explicit. Soil raw role
markers and numeric values are validated before parser normalization. Override
shape is exact; booleans/nulls/strings and nonpositive/nonfinite values are rejected.
Repair is explicit, all-default-only and prohibited on valid/unbound states.
Materialization uses a fresh owned directory, fixed names and rejects symlinked
parents. New display values use text nodes and Jinja safe JSON embedding.

Durable result admission reads `roads.nodb` without controller creation, validates
the saved parameterization and requires matching preparation/receipt identities;
legacy receipts remain separate. Publication also binds completed profile hashes.
Existing lifecycle locking and historical-output retention remain in force.

## Final verification required

Re-read final hashes; run targeted malformed/valid persistence/materialization and
route tests; inspect full workflow evidence under actual identities/mounts. Verify
no source/state/default changes outside approved scope. Static source review alone
does not certify browser/auth/worker/archive boundaries or full native execution.

## First resolution readback

IS-01 is resolved in source: first-use validation runs through the same pure
ordinary-parameter parser plus the nested override validator before controller
creation. Existing disabled/controller mismatch uses normal synchronization and
is not enabled by the new route. Both route regressions pass.

IS-02 is resolved in source through an opt-in owned97.3 parser validation mode
using existing strict token/count/reference/full-consumption checks. The source
comment adapter operates only on a validation scratch copy. Original templates
and materialized bytes remain unchanged. Trailing records, negative references,
large counts and malformed restored hashes have retained regressions. A small
follow-up requests explicit rejection of simultaneous public StrictUpload and
StrictLegacyRoads modes to preserve the98.4-only upload boundary without ambiguity.

IS-03 is resolved: raw soil/horizon and management numeric fields now undergo
native REAL representation validation before materialization. Repeating the depth
1e308 probe returns an explicit `ValueError` for native representation; no native
execution occurs.

Independent focused command:

```sh
wctl run-pytest tests/nodb/mods/test_roads_parameterization.py tests/weppcloud/routes/test_roads_bp.py tests/wepp/interchange/test_roads_lifecycle.py -q --maxfail=1
```

Result: **119 passed, 4 warnings, 23.49 seconds**. This checks actual owned parser,
file materialization and durable receipt boundaries alongside route fixtures. It
does not replace the pending live authenticated browser/worker/archive workflow.

## Final parser and comparison source disposition

IS-01, IS-02 and IS-03 are resolved. Simultaneous StrictUpload/StrictLegacyRoads
modes are explicitly rejected; ordinary upload remains98.4-only and ordinary
management objects do not gain a serialized legacy-validation flag. The comparison
helper rejects traversal/external aliases, excludes symlinked history candidates,
checks publication receipts and source bytes, recomputes metrics, and does not
initialize NoDb. Malformed comparisons are explicit diagnostics, not current data.

Independent final focused command:

```sh
wctl run-pytest tests/nodb/mods/test_roads_parameterization.py tests/nodb/mods/test_roads_parameterization_comparisons.py tests/wepp/management -q --maxfail=1
```

Result: **226 passed, 2 warnings, 14.20 seconds**. The prior119-test command additionally
covered the route and durable result-admission boundaries. No unresolved source
security finding remains at this readback. Runtime/browser/archive verification
and final source-identity refresh remain pending; deployment is not certified.

## IS-04 — medium: later historical readback lacked containment and receipt checks

A subsequent implementation added `_last_parameterization_readback`, after the
source pass above. Independent correctness review identified, and security review
confirmed, that its direct history glob/receipt/manifest reads can follow a
symlinked history subtree outside the project. Required-resource checks reject
literal traversal but did not reject resolved aliases. The readback also accepted
receipt-shaped JSON without policy, single-storm type or mandatory-resource-set
validation. That can expose another project's historical fields or present an
incomplete record as completed evidence.

Requested remedy: contained historical path access, reject aliased candidate roots,
and require a complete matching publication receipt plus execution provenance.
Retain source-hash/readback checks, and add real symlink-escape and incomplete
receipt regression cases. Integration owner notified. Earlier source pass does
not cover this later addition; this finding is pending resolution.

## IS-04 resolution

Historical readback now uses contained roots and files, validates exact published
receipt policy/shape/mandatory resources, and binds the snapshot hash, manifest
hash and actual soil/slope/management input hashes. It does not use an unverified
current summary as historical evidence. Malformed source bindings are explicit
diagnostics. The reader requires manifest binding for single-storm as well as
continuous results; the writer must retain that binding even when comparison
metrics are unavailable.

Independent command:

```sh
wctl run-pytest tests/nodb/mods/test_roads_controller.py -k parameterization_historical -q --maxfail=1
```

Result: **10 passed, 69 deselected, 2 warnings, 10.62 seconds**. Tests include
actual symlink aliases, incomplete receipts and changed snapshot/manifest/input
bytes. IS-04 is resolved in the reader; final writer parity and live workflow
readback remain to be incorporated with the final source-identity refresh.


IS-04 final writer readback: the derived snapshot now binds manifest bytes before
branching on metric availability, including single-storm/unavailable summaries.
The producer also rejects a snapshot destination aliased to another project
artifact. Owner reports 13 comparison regressions passing. Source review confirms
both producer and historical reader enforce the same published binding; no
remaining source security finding is open.

## Final independent review (2026-11-03)

Reviewer: `/root/security` (`security_reviewer`), independent of implementation.
Scope: the eight source files hashed in the companion JSON, on ancestor
`73b5da4ac3337d066619bd625d48b6adc2f307d1` plus the retained working changes.
Security impact is **high** under the package policy because this adds a public
run-scoped view, mutation payload and retained-file handling. A dedicated review
is required. Historical findings and preliminary verification above remain an
audit trail; this section and the companion JSON govern the current disposition.

The threat model covers browser-controlled overrides, malformed restored baseline
text, inconsistent retained provenance, and path aliases beneath a project.
Existing project ownership/public access policy, trusted installed source/native
binaries and NoDb's owned serialization remain the enclosing trust boundaries.
Arbitrary hostile Python object payloads are not accepted through the new request
schema. This change does not make externally supplied jsonpickle safe in general.

IS-01 through IS-04 have no remaining source finding. The fresh independent
focused command ran the comparison module and historical controller cases through
`wctl`, including real temporary files, symlinks and publication hash mutations:
**23 passed, 70 deselected, 2 warnings, 11.57 seconds**. Its retained log is
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1/security-final-focused-v2.log`.
Tests establish the unavailable/single-storm snapshot writer's manifest binding,
output-alias rejection and contained historical reader. Live lifecycle evidence
remains a separate gate below.

### Surface checks

| Surface | Independent disposition and evidence |
| --- | --- |
| Valid states | Absent/legacy preview remains read-only, first binding is explicit, valid retained baseline/reset remains supported, and malformed/aliased inputs fail explicitly. Current correctness and UX artifacts own their distinct verdicts. |
| Auth/session/CSRF | New view and both mutation aliases retain `authorize_and_handle_with_exception_factory`; the alias delegates inside the existing authorized/fenced request. Global Flask CSRF applies, with no new exemption. Browser `WCHttp` supplies existing CSRF transport. Private and readonly live denial evidence is required below. |
| Secrets | No new credential dependency, secret defaults or secrets in reviewed production code. Task harness loads the ignored dev-agent credential file; retained summaries exclude credentials, cookies and bearer tokens. |
| Input/output | Exact override keys/modes and positive finite native values; exact 18 retained assets with per-asset/total limits and owned raw/strict parsing. Templates use Jinja `tojson`; displayed source/error values use `textContent`. No dynamic HTML injection or request-selected executable/path is introduced. |
| Filesystem | Fresh fixed-name baseline materialization, nonsymlink scratch ancestry, contained current/history receipts and source hashes; writer refuses output aliases. Actual symlink and traversal regressions pass. Local filesystem administrators remain outside the web attacker model. |
| Queue/subprocess | Existing Roads Prepare/Run and lifecycle workers remain the execution path; no enqueue/dependency edge, shell command, executable selection or queue permission changes. New parameters reach numeric native headers only after validation. |
| Agent tooling | Workflow tooling is restricted to the named disposable project and local services. No production deployment or shared project regeneration is part of this review. |
| Network | No production network integration or egress is added. Workflow automation uses the configured local HTTPS origin and existing authentication/RQ boundaries. |
| Supply chain | No new dependency, registry workflow, runner permission or native binary is introduced. |
| Integrity/concurrency | Prospective values validate before retention and persistence, using existing Roads lifecycle exclusion and NoDb locked refresh. Durable admission uses the owning codec without cache/post-load mutation and binds preparation/configuration/snapshot identity. Retained comparisons recompute source/input/metric compatibility. |
| Logging/recovery | Explicit validation/denial diagnostics remain inspectable; no new broad exception swallow. Save retains prior artifacts/authority and revokes current eligibility. Failed pre-restart evidence remains preserved, with live recovery required rather than synthetic publication. |

### Runtime and artifact observability gate

The final independent readback is
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1/security-final-runtime-v2.json`.
It hashes 20 inspected workflow/service receipts and directly verifies all 182
comparison source hashes and all 105 native input hashes in each of the restored
project and full fork. Both current receipts bind the custom configuration
`9908b75c468dfd4fc6d14460a8fee6c8842ae530237b37199908c3f71b940e15`
and snapshot `e351a5791f1bdbb13acc5b3bd4562f4d43f329725c9907a74b2f035517f8139a`.

The verified default is `native-default-restarted-readback.json`, not either
pre-restart attempt. Default and custom evidence each cover 35 profiles and all
three roles. Custom readback confirms all twelve multipliers reach native inputs
and all 70 geometry/management files remain unchanged. The real browser Save
changes configuration, revokes current results and keeps the prior execution
historical. The custom publication and actual report views use fresh bound results.

`readonly-on-sequential.json` confirms disabled Edit and an actual Save denied
HTTP 403; `readonly-off-sequential.json` confirms writable recovery. The initial
readonly attempt raced an archive guard and failed enqueue without mutation. It
is retained as a harness sequencing failure, not a permission pass or source fix.

The canonical archive job verifies 8,131 ZIP members, including retained NoDb
parameterization and generated/history/baseline bytes. Reset retains the same
baseline, clears all overrides and rejects current results. Canonical restore
and full fork each preserve all 7,223 Roads artifacts, 907 protected baseline
files, all 105 native input files, retained configuration and current eligibility.
See `lifecycle-{archive,reset,restored,fork}-v1.json`; these are artifact checks
after real RQ operations, not job-status-only claims. Browser browse/download
checks in `artifacts-restored.json` return 200 and match snapshot, manifest and
native input hashes through established project tools.

`fork-private-auth-csrf-valid.json` proves the owner can query the existing private
fork (200), while anonymous GET and Save with a same-session CSRF token and valid
complete overrides both return 404 access concealment. The earlier harness
incorrectly rejected GET 404 and its missing-CSRF POST received 400; that failed
receipt remains preserved. The final test separates authorization from CSRF.
Initial fork attempts failed at stale rq-engine imports and then startup readiness;
the retained successful `fork-ready.json` follows the rq-engine restart.

Service receipts record uid 1000, gid 993, umask 022 and actual local mounts.
Mounted source hashes are not proof that long-lived workers loaded those bytes.
The native run uses its restarted/resumed execution checkpoint; later changes
are query-only repository-drift disclosure and UI presentation. Final Flask and
rq-engine identities follow their documented reloads. No claim is made that the
older worker process reloaded query-only code merely because mounted bytes changed.
Native writer/parameter validation behavior did not change after custom execution.

IS-04 is now resolved in both writer/reader source and this live retained-artifact
workflow. A bounded scan of retained top-level JSON/HTML/log evidence found no
bearer/credential values or unredacted CSRF metadata; captured report metadata
uses an explicit redaction placeholder. This is not an exhaustive secret scanner.

### Verdict and residual scope

Security source and local runtime gate: **pass**. No unresolved high, medium or
low security findings remain; IS-01 through IS-04 are resolved. No risk acceptance
was used. Reviewer sign-off: independent `/root/security`, 2026-11-03 (local date).
The package's broad validation, correctness and UX gates remain separate; this
security verdict cannot waive them.

Live checks cover the local continuous-run workflow. They do not certify an
unobserved production host, live single-storm execution, scientific calibration,
new default adoption or deployment. Source and focused regression coverage for
single-storm/unavailable comparison binding is distinct from live native evidence.

### Supplemental Disturbed provenance review

Independent security review accepts the final validation-only change in
`tests/disturbed/PLAN.md`, `test_matrix_contracts.py` and
`analysis_source_reviews_current.json`. The sidecar pins the original provenance
and report bytes plus the exact old/current `managements.py` source hashes; its
delta map must equal every actual drift. Another source change or a changed report
fails until separately reviewed. Without a sidecar the strict equality gate still
applies. This repository-owned review record introduces no runtime input or path
access boundary and does not relabel the original execution with current sources.

Independent direct readback confirmed the original provenance/report are identical
to HEAD and rehashed all 96 retained cases: 768 native outputs and 960 other inputs
are byte-identical, including all 96 managements. Each of the 96 soil differences
is exactly one `#   Build Date: ` comment; all remaining bytes are unchanged.
The opt-in Roads strict parser is not selected by these Disturbed cases.
`disturbed-security-source-review-v1.json` in the workflow evidence directory
binds this review's three source hashes and independently checked counts.
No new security finding; the security verdict remains **pass**. The final broad
suite remains a separate completion gate.

### Final stale-client script inclusion

The final template adds the established same-origin deferred
`controllers_gl_stale_check.js` immediately after `controllers-gl.js`, using
`static_url` for both. Independent source review confirms the shared script is
unchanged: it compares build IDs, uses text nodes for its banner and reloads only
on user action. It introduces no new mutation/authentication boundary, external
fetch or native writer change. Security source review passes; the companion JSON
now binds the final template hash and unchanged shared script. Final rendered
loading/build-ID acceptance belongs to the UX browser check after web reload,
not this static hash refresh. The native artifact evidence remains applicable.
