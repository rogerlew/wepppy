# Project developer mode (DM-01)

Status: implemented and locally artifact-validated, 2026-10-29 UTC; production deployment remains separate. See [validation evidence](../work-packages/20261028_project_developer_mode/artifacts/validation.md) for regression results and scope limits.

## Purpose and decision provenance

The requesting operator approved this design in the user/Codex workspace conversation on 2026-10-28 Pacific: Ron owns project developer mode with enable-only editing; only the `Dev` role may activate it through the PowerUser panel; project mode alone controls anisotropy maximum enforcement; clones retain mode. Codex records the decision, not scientific validation. Anurag is the intended development user, not an inferred participant or approver.

This bounded capability enables experiments without changing normal-project limits. It is not a general authorization bypass or a promise that extreme model parameters are stable.

## State and lifecycle

`Ron.developer_mode` is a persisted boolean in `ron.nodb`, backed by `_developer_mode`. New projects default to false. A missing attribute in legacy projects reads false without requiring a migration or writing on read. Explicit false and true are valid; null, strings, numbers and other malformed persisted values must fail explicitly when resolving this policy, never become true through truthiness.

Activation is the sole dedicated mode mutation: false to true. Repeated authorized activation is an idempotent success. There is no disable/reset API, form or configuration override. The one-way rule applies to ordinary mode editing, with the lifecycle replacement exceptions below. Use the existing NoDb locked refresh/mutation/persistence contract; concurrent unrelated Ron updates must not erase activation. An activation failure must not be presented as success. After a lost response, reload authoritative state before offering a retry.

Clones/forks preserve the source mode and anisotropy settings, including copies made by a caller without `Dev` when existing clone authorization permits that operation. This inherits project policy, not a user role. Normal/legacy projects clone as normal.

Operator clarification, 2026-10-29 UTC: archive restore and existing failed-fork recovery retain their established replacement semantics. Restored archived Ron state, or recopied source Ron state during fork recovery, is authoritative, even when it replaces true with false or a missing legacy attribute. Do not preserve the destination's previous true value or reject these operations because of developer-mode differences. Existing lifecycle authorization, validation and failure/retry behavior remain unchanged; no extra Dev-role check applies. There is no second datastore, activation history or sticky preservation mechanism. This explicit exception favors simple implementation and usable recovery: blocking archive/fork operations could prevent users from recovering projects. Re-enabling mode after replacement uses the usual Dev-only activation action.

Clone publication must preserve mode/value consistency during concurrent source activation: a clone must not publish copied elevated overrides with an earlier normal-mode Ron snapshot. Serialize with existing lifecycle mechanisms or reconcile the source mode after copying values and before publication within the same lifecycle incarnation. Mode is monotonic only within an incarnation; a restore/replacement must invalidate earlier observations under existing lifecycle fencing. Exercise that interleaving with real copy/rehydration. Existing failed-fork destination recovery follows the replacement exception above.

Archive creation has the same mode/value consistency obligation: do not publish an archive containing elevated saved overrides paired with a stale normal-mode Ron snapshot. Exercise activation interleaved with real archive member capture and subsequent restore. Reuse existing lifecycle serialization or mode reconciliation within the same lifecycle incarnation before archive publication; do not introduce a parallel persistence system.

## Activation authorization and presentation

The activation action requires an authenticated caller with the exact existing `Dev` role plus existing project mutation authorization, readonly enforcement and browser-session CSRF protection. `PowerUser`, `Admin` or `Root` without `Dev` does not independently authorize activation. This does not redefine those roles elsewhere.

Expose **Enable developer mode** in the PowerUser panel only to `Dev` users. Explain concisely: no off toggle; clones inherit mode; archive restore and failed-fork recovery use the incoming project state and may return it to normal mode. Anisotropy upper limits are removed while mode is enabled. Avoid an unqualified permanent label. A Dev-only user must be able to reach this action without gaining unrelated PowerUser actions. Preserve existing individual action gates and panel contents for existing audiences. For readonly projects, show the action disabled with the existing readonly explanation. After activation show status, not an off toggle. All authorized project viewers see a Developer mode indicator, including viewers without access to the panel.

On successful activation update the current page's mode indicator, activation action and anisotropy maximum attributes immediately without discarding unsaved form values. Failure leaves displayed policy unchanged; an indeterminate response requires authoritative reload/readback before claiming success. Other already-open pages may require reload to see activation; server validation always uses authoritative state.

Use `POST /runs/<runid>/<config>/tasks/enable_developer_mode` with JSON `{}` and the existing session CSRF header. Reject non-object or nonempty payloads with HTTP 400; there is no client-selectable policy or target boolean. On initial or repeated authorized success return HTTP 200 with `{"Content":{"developer_mode":true}}`, using the existing project-route success factory. Missing authentication, missing Dev role, project-access or readonly denial returns HTTP 403 through the existing error factory; CSRF failures retain the canonical CSRF status/envelope. Do not enable activation via general WEPP input parsing, query parameters, project config, a clone override, or an untrusted `developer_mode` form field. Failed authorization, CSRF, readonly checks or malformed requests leave state unchanged. Malformed stored mode fails explicitly as an internal data error rather than being treated as a caller validation error; persistence/lock failures retain existing NoDb boundary behavior.

## Anisotropy policy

The [soil anisotropy contract](soil-anisotropy-contract.md) retains all behavior except its maximum checks on explicit overrides:

| Project mode | Upper-horizon override | Lower-horizon override |
| --- | --- | --- |
| Normal | finite number in [1,100] | finite number in [1,10] |
| Developer | finite number >=1; no maximum | finite number >=1; no maximum |

Apply this policy consistently in rendered controls, request validation and preparation-time revalidation of saved values. No additional caller-role check applies to anisotropy submission or execution; ordinary operation authorization remains unchanged. Server and workers derive mode from Ron, never the submitted payload or a user identity. Resolve mode once for each preparation operation and pass it explicitly through Python to the native function; do not add environment-dependent native behavior. If activation happens after a normal-mode snapshot, that operation may reject an elevated value; retry observes the new mode. A stale browser maximum is resolved by reload, not by trusting the browser.

Keep default native calls normal-mode and preserve existing positional callers with an additive optional policy argument. A missing upgraded native API fails explicitly; no numerical fallback or silent normal-mode substitution. Updating Python, the rendered controls and wepppyo3 must be coordinated.

Blank/omitted semantics, validation-before-mutation, minimum 1, NaN/infinity and boolean rejection, MOFE/hourly eligibility, original source ratios, horizon boundaries, file formats and single-read/single-write preparation remain unchanged. No clamping is permitted. Retain the numerical-instability warning for both controls when developer mode allows either value above 10. Activation alone neither rewrites soils nor reruns WEPP nor relabels historical results as freshly generated.

## Extended landsoil panel presentation (DM-02)

Accepted design, 2026-10-29 UTC; implementation conformance pending in the
[implementation package](../work-packages/20261029_extended_landsoil_developer_panel/package.md).
The operator requested a simpler Disturbed Panel for normal base-table projects,
continued operation of existing extended-table projects, and no new backend
restriction on extended lookup use.

When the Disturbed module is enabled, render the current full Disturbed Panel
if `Ron.developer_mode` is true **or** the existing
`Disturbed.active_lookup_variant` getter resolves to `extended`. Otherwise,
render a simple panel with exactly two lookup actions: **Reset Base Landsoil
Lookup Table** and **Modify Base Table**. Retain normal dialog close controls,
status/error feedback and documentation links; omit the Base/Extended selector,
extended load/delete/edit/sync controls, and empty advanced sections. Preserve
existing project access, readonly handling, module eligibility and action
semantics. A user's Dev role alone does not select the full layout.

Apply the predicate to every modal consumer, including the run page and report
shell. Missing template context is not proof that the project has no Disturbed
state: report routes may omit a `disturbed` variable. Resolve existing state for
the active page/run root through the normal NoDb read path without constructing
missing state, rather than defaulting those report pages to Base.

Use the existing resolved variant, not the raw persisted field or file existence
alone. The getter honors explicit Base even when an extended file exists, and
recognizes legacy extended files when no valid selector is stored. Explicit
Extended with a missing file still gets the full panel so existing load/repair
controls remain reachable; existing file-availability and validation behavior
continues. Missing optional Disturbed state must not be created or mutated just
to decide presentation. Malformed Ron mode retains DM-01's explicit failure;
legacy Disturbed selector interpretation remains unchanged.

Layout is a page-render snapshot. Enabling developer mode requires a page reload
to reveal extended lookup controls; existing immediate anisotropy/status updates
remain intact. Selecting Base or deleting the extended table on a normal project
retains the currently rendered panel until reload, then shows the simple panel.
There is no automatic page reload that could discard unsaved inputs. On
2026-10-29 the operator explicitly accepted loss of full-panel access after this
transition and will give the affected users the Dev role to enable project mode.
Role assignment is outside this package. Do not add a sticky legacy grant or
remember whether the project previously used Extended.

This is UI discovery policy, **not backend authorization**. Do not add a
Dev-role or developer-mode requirement to existing extended lookup routes,
editors, direct URLs, generation, selection, deletion, synchronization, saved
state validation, or workers. Ordinary authorization, CSRF, locking and input
validation remain applicable. Direct authorized operations can still configure
Extended on a normal project; its next page render then uses the full panel.
No table is deleted, reset, converted or rewritten by rendering or activation.
Clone/archive recovery uses incoming Ron and Disturbed state under existing
lifecycle rules; there is no additional migration or recovery restriction.

Rationale: conditional presentation keeps normal-project controls simple and
preserves active extended workflows without changing model behavior. Render-time
selection minimizes controller and persistence risk; backend enforcement and
permanent grandfather flags add complexity the operator expressly does not want.
No numeric defaults, formulas, table schemas or native policy change.

## Compatibility and regression obligations

The additive boolean requires no bulk data migration and removes no existing keys. Normal and legacy runs retain current behavior. Validate durable reload, real locked concurrent updates, repeated activation, role combinations, readonly/CSRF failures and direct spoofed payloads. Validate Dev-only panel access without widening unrelated actions and non-Dev submission to activated projects under existing access rules.

Cover absent optional state, blank anisotropy, populated normal/developer state, legacy state, malformed mode/values, inactive eligibility, working/failed/completed execution and archive/restore separately from role/input combinations. Clone normal and developer projects through the actual copy/rehydration boundary, including a non-Dev authorized caller, and retain source hashes.

Exercise real restore and failed-fork recovery from an activated destination using incoming true, false and legacy-missing mode. Read back the incoming mode and associated saved values; prove authorized recovery is not rejected or silently made sticky. After true-to-normal replacement, normal anisotropy maxima apply again. Existing unrelated lifecycle safety checks still apply.

Read real generated `wepp/runs/p*.sol` after native preparation with upper=101 and lower=11; prove those values reach their respective depth classes and unrelated fields/source soils remain unchanged. Prove the same overrides fail atomically in normal mode. Exercise fresh model execution and normal browse/download/report paths on a representative project under production-equivalent runtime identities. Retain numerical failure evidence if an experimental simulation fails; accepting an override is not a guarantee of model stability. Archive/restore evidence must include Ron mode and generated inputs. Deployment remains a separate claim.

## Governing boundaries

Existing [NoDb persistence](nodb-persistence-concurrency-contract.md), [CSRF](weppcloud-csrf-contract.md), [RQ responses](rq-response-contract.md), [feature access](feature-access-governance-contract.md), and [controller behavior](../ui-docs/controller-contract.md) remain in force. Developer mode is a project parameter and presentation policy, not a registry feature entitlement, account group, project-config field or broad role hierarchy change. Future developer-mode effects require their own explicit contract amendment.

Rationale: an enable-only control avoids destructive clamping/reset semantics; inherited mode keeps experimental clones runnable; checking roles only at activation keeps queued execution independent of the initiating user's later roles. Instance-wide maxima, user-specific parameter validation and an ordinary off toggle were rejected. The operator explicitly rejected preserving destination mode or blocking existing restore/fork recovery: incoming project state wins for simplicity and recovery flexibility.
