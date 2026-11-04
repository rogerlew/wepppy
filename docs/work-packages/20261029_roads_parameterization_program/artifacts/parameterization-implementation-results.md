# Roads parameterization implementation results

Status: **PASS — package closed2026-11-03**. Accepted contract ancestor: `73b5da4ac`.
Actual workflow, independent reviews and final reconciled regression coverage pass.
This is local delivery evidence, not production deployment or new-default adoption.

Final validation:13,034 unique passes,422 runtime skips and one collection skip;
all13,456 collected tests accounted for across the retained broad prefix and142-test
passing suffix. Affected view checks287 passed, focused Roads273 passed, frontend
122 suites/1,033 tests passed, and lint/test-stub/broad-exception checks passed.
See [final receipt](parameterization-implementation-validation.json) and
[ledger v40](candidate-ledger-v40.json).

## Delivered behavior

Roads owns retained repository baseline texts and twelve role-driver overrides in
`roads.nodb`. The dedicated view supports Save/Cancel/Reset, explicit invalid-state
repair, source arithmetic, repository drift disclosure, actual emitted values and
compatible retained-run comparisons. Native inputs and successful publication
receipts bind the saved configuration. Accepted changes revoke current output
eligibility while preserving historical artifacts. Existing geometry/management
settings and baseline WEPP outputs remain independent.

## Actual workflow evidence

Raw receipts are under
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1/`.
The disposable project is `roads-param-ui-20261103-v1`; validation uses the canonical
local HTTPS/browser/Flask/RQ/native/report path and uid1000/gid993 service identities.

| Boundary | Retained evidence and result |
| --- | --- |
| Default execution | `prepare-restarted.json`, `run-restarted.json`, `native-default-restarted-readback.json`: 35 profiles, 105 role records, exact native values and current receipt identity |
| Custom Save | `ui-custom-restarted.json`, `custom-save-invalidation-v2.json`: twelve multipliers of 2, unchanged retained baseline, invalidated current result and retained historical default |
| Custom execution | `prepare-custom-restarted.json`, `run-custom-restarted.json`, `native-custom-restarted-readback.json`: 420 exact driver values; 70 unchanged slope/management files; bound publication receipt |
| Comparison/report | `independent-correctness-readback-v1.json`, `independent-correctness-compatibility-v1.json`, `reports-custom-semantic-v2.json`: raw native metrics independently recomputed, actual compatibility inputs compared and fresh report identity verified |
| Readonly | `readonly-on-sequential.json`, `readonly-off-sequential.json`: Edit disabled, actual Save denied403, normal editable state restored |
| Archive/Reset/Restore | `archive.json`, `ui-reset.json`, `restore.json`, `lifecycle-archive-v1.json`, `lifecycle-reset-v1.json`, `lifecycle-restored-v1.json`: 8,131 archive members verified; retained baseline survives Reset; custom authority, inputs, history and current eligibility restored exactly |
| Full fork/private access | `fork-ready.json`, `lifecycle-fork-v1.json`, `fork-private-auth-csrf-valid.json`: retained authority, all native/artifact bytes and current eligibility match; authorized query200; anonymous GET and valid-CSRF Save both404 |
| Artifact access | `artifacts-restored.json`: authenticated browse200 and native soil/manifest/comparison downloads match actual bytes |
| Desktop/mobile | `parameterization-implementation-ux-final-stale-v3/` beside the workflow directory: 1440/1440 and390/390 widths, zero JS errors, all420 native values and12 comparison cells match query |

Independent recomputation used 204,540 PASS rows per execution. Default modeled
profile exports were 2,311.08895 m3/year runoff and 9,025.41668 kg/year sediment;
combined custom overrides produced 1,993.68161 m3/year and 7,334.82236 kg/year.
These are modeled-profile PASS exports, not watershed outlet yield, field calibration
or isolated parameter sensitivity. Geometry, management, climate, runtime controls
and all nonoverride soil content are unchanged between this pair.

## Retained failures and recovery

Pre-restart default receipts lacked parameterization identity because long-lived
workers loaded the older lifecycle reader. The owning-codec repair plus authorized
service reload and new native run resolved that boundary; failed receipts remain.
The prior claim that the project was unbound or unchanged Save was broken was
incorrect. `_parameterization` is durable and its hash is computed.

A readonly submission during archive locking was rejected before mutation; the
sequential retry passed. A fork submission in the five-day-old rq-engine failed
on import before enqueue. Restarting that service restored the route; an immediate
startup request also failed before readiness and is retained separately. A web
reload interrupted the first broad test run with exit137; final-source broad
validation was restarted. None of these attempts is counted as a passing gate.

The first private-auth helper incorrectly excluded the existing concealment404
response and sent a CSRF-less POST. Its corrected retry uses an anonymous valid
CSRF token and the complete valid override object; GET and POST both return404,
while the owner sees the bound fork. No production authorization change was needed.

The final broad attempt completed485 tests and all96 native Disturbed matrix cases
before its published-report source guard detected the changed shared management
parser. Independent correctness and security reviews confirmed all768 native outputs and
960 other inputs byte-identical to the published evidence; all96 soil differences
are exactly one generated Build Date comment. A separate source-review record
pins the exact parser delta and unchanged original report/provenance. The strict
gate rejects later unreviewed drift. Ten focused contract tests pass; the subsequent broad attempt and final suffix complete the required collection. Historical report data is not relabeled as newly
executed.

Final source corrections disclose repository baseline drift, constrain the populated
mobile selector and explain native conductivity conversion. They change query/UI
behavior only; native execution remains bound to its recorded writer identities.
Mounted source hashes do not establish the loaded code of an older worker.

## Limits and maintenance

The actual service workflow covers one continuous rutted project with all three
roles. Broader branches, invalid states, hostile retained content and single-storm
comparison unavailability have focused parser/writer/controller coverage; this
workflow does not claim live coverage of every branch. Historical scientific
failures and withheld materials remain unchanged. No repository default, binary,
new dependency, service, queue or deployment topology was adopted.

Quality telemetry is observe-only: the Roads facade grew to integrate the approved
state, provenance and query behavior; separate owned helpers isolate validation
and comparisons. A new unrelated refactor is not part of this delivery.

Management stubtest reports143 diagnostics in both the candidate and an isolated
HEAD module, with identical diagnostics and zero new errors. The public
`**kwargs: Any` signature is unchanged; Roads has no maintained `.pyi` target.
This inherited stub debt is recorded in `management-stubtest-comparison.json`
under the final validation directory, not represented as a passing stubtest.
The test-stub hygiene check passes.

The broad retry reached12,892 passes and423 skips before the new dedicated
template failed the shared stale-bundle wiring contract. It omitted the standard
`controllers_gl_stale_check.js` immediately after `controllers-gl.js`. The bounded
fix adds that same-origin deferred script through `static_url`; no native writer,
saved state or report arithmetic changes. Final validation completes the failed
case and unexecuted collection tail and rechecks affected view/render tests, with
explicit collection reconciliation. Earlier passing native tests are retained,
not represented as an uninterrupted green full run. Final rendered UX binds
the new template and actual loaded stale-check script; build IDs match and no
false stale warning appears. All287 affected checks and142 suffix tests pass.
