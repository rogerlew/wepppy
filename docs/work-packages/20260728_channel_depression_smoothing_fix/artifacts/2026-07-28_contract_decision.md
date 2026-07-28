# REM-05 Channel Depression Smoothing Contract Decision

**Date**: 2026-07-28 UTC
**Starting implementation revision**:
`e07bb10668f5ac59b8bba4b8bb111e89f5d735a2` (local `master` before REM-05)
**Owner borrowed**: DOM-05
**Classification**: Bounded production-defect remediation
**Security impact**: High, inherited from DOM-05

## Operator Decision

The operator reported the production defect on wepp1, supplied the request
payload showing `"wbt_fill_or_breach": null`, directed Codex to fix the contract
and error, commit and push all local commits, pull on wepp1, and deploy
WEPPcloud. This is explicit approval of the finite behavior and deployment
described here.

## Normative Contract

For the Weppcloud-WBT Channel Delineation control:

1. The depression-smoothing selector has rendered DOM id
   `input_wbt_fill_or_breach`, submitted form name
   `wbt_fill_or_breach`, and data hook `data-channel-role="wbt-fill"`.
2. Its allowed user-visible/token pairs are Fill/`fill`,
   Breach/`breach`, and Breach (Least Cost)/`breach_least_cost`.
3. The selected value is hydrated from
   `Watershed.wbt_fill_or_breach`.
4. Channel controller serialization emits the canonical JSON key
   `wbt_fill_or_breach` with the selected non-null token.
5. The rq-engine/RQ boundary receives that token. Before channel construction,
   `build_channels_rq` assigns it through
   `Watershed.wbt_fill_or_breach`, whose NoDb setter persists the value.
6. A later page render hydrates the selector from the persisted value. A
   successful build and reload therefore preserve the user's selection.
7. Omission/null retains the existing worker compatibility behavior and does
   not overwrite the stored value. The browser control must not create
   omission/null for a rendered valid selection.

This checkpoint is the pre-registry-cutover canonical authority for this finite
REM-05 behavior. DOM-05 must inherit and reconcile it when the complete Channel
Delineation domain contract is ratified.

## Applicable Contracts and Conflict Disposition

| Canonical contract | Applicability and REM-05 disposition |
| --- | --- |
| `docs/ui-docs/controller-contract.md` | Applies to the shared controller/template boundary. REM-05 restores predictable form serialization and does not change singleton, bootstrap, status, event, or endpoint behavior. |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Applies because the existing Watershed setter persists the selected token. REM-05 does not change locking, atomic dump, cache invalidation, schema, or concurrency behavior. |
| `docs/schemas/rq-response-contract.md` | Applies to the unchanged queue response/error boundary. REM-05 changes neither responses nor queue wiring; the existing nullable worker argument remains compatible. |
| `docs/schemas/weppcloud-csrf-contract.md` | Applies to the existing authenticated browser mutation. REM-05 changes only one serialized enum value and does not change transport, authentication, origin, session, or CSRF enforcement. |
| REM-05 checkpoint and GOV-00A-M1E registration | Own the exact pre-registry-cutover depression-smoothing id/name/token/persist/reload behavior recorded above. |

No contract conflicts were found. The shared and cross-cutting contracts remain
unchanged; this finite checkpoint supplies the missing DOM-05 field-level
authority without redefining their behavior.

## Confirmed Discrepancy

Production run `lower-class-transfer` using configuration
`disturbed9002_wbt` submitted `wbt_fill_or_breach: null` twice. RQ jobs
`5006a2d0-6aa2-41e1-b4a9-8cd71eb8c385` and
`88e3068d-c77c-42ee-ba3c-f1738ac8c273` received `None`; the run log records
`fill_or_breach=breach_least_cost`, and `watershed.nodb` remained
`breach_least_cost`.

The Pure macro defaults the submitted name to its field id. The template passes
`input_wbt_fill_or_breach` as that id without the supported
`field_name="wbt_fill_or_breach"` override. Existing JavaScript tests model the
intended name and therefore did not expose the rendered-template mismatch.

## Implementation and Regression Plan

Add the canonical `field_name` argument to the existing select macro call. Add
actual-template regression assertions that check the id/name/data-hook triple,
reject the incorrect submitted name, and prove representative persisted values
render selected after reload.

Add focused worker tests that prove a non-null `fill` token is assigned before
`build_channels`, a null token retains existing stored state, and a build
failure after the setter does not introduce a second or partial persistence
path. These characterize the existing worker/NoDb contract; they must not
change queue wiring, locking, setter, or failure semantics.

Run:

- `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py`
- `wctl run-pytest tests/rq/test_project_rq_mutation_guards.py`
- `wctl run-npm lint`
- `wctl run-npm test`
- scoped documentation lint and `git diff --check`

After deployment, use non-mutating source/markup inspection to verify the
corrected rendered name. Do not submit the form or rebuild/mutate the user's
run. End-to-end mutation evidence must use automated tests or a separately
authorized disposable/cloned run.

## Compatibility and Security

This is backward-compatible for every valid enum token and old run. It changes
only the browser's previously missing value into the selected canonical value.
No route, parser, queue edge, default, formula, project schema, authentication,
authorization, CSRF, or file-upload behavior changes.

The high inherited security review must verify that the patch does not add a
new input, bypass validation, change endpoint/authentication behavior, or widen
the RQ boundary.
