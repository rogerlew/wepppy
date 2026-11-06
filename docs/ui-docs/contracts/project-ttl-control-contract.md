# Project TTL Control Contract

## Access and rationale

All authenticated users who pass the existing run authorization checks may
disable or re-enable TTL deletion. No PowerUser, Dev, Admin, or Root role is
required. Both the run header and report header show the control to signed-in
users. Anonymous users cannot mutate this setting.

Operator clarification on 2026-11-03: TTL retention is available to all users.
The privileged-role restriction introduced in `b71bedfe8` was incorrect;
replacing its all-role requirement with an any-privileged-role requirement
would still exclude ordinary users and would not repair the intended workflow.

## Mutation and compatibility

`POST /runs/<runid>/<config>/tasks/set_ttl_disabled` retains the existing boolean
payload, response envelope, CSRF protection, run authorization, lifecycle lock,
and user-ID audit. Signed-in access to a public run follows the existing run
authorization rules; this repair adds no owner-only restriction. Private runs
remain inaccessible to callers rejected by those rules.

The stored TTL schema, rolling expiration calculation, readonly/batch policy,
and deletion lifecycle are unchanged. Missing, empty, malformed, and legacy TTL
metadata retain the existing setter's initialization/normalization behavior.

## Runs catalog bulk protection (2026-11-05; implementation pending)

The Runs page offers **Disable Automated Deletion for Selected** beside its
delete action, as specified by the [catalog contract](runs-catalog-ttl-deletion-contract.md).
Each selected run receives the existing JSON `ttl_disabled: true` POST, with
the existing authentication, run authorization, CSRF protection and user audit.
Catalog visibility, including an admin alias view, never grants mutation access.
Missing/legacy metadata follows the existing setter behavior. Partial failures
are reported individually and do not roll back successful protection. The
client must verify the success envelope and returned disabled state before
claiming protection. No bulk endpoint, re-enable action, policy formula or
deletion lifecycle change is introduced. This reuses the established control
to let users protect several projects without opening each one.


Protection confirmation requires a non-null returned TTL object with
`delete_state: "active"` and either `policy: "disabled"` with
`user_disabled: true`, or `policy: "excluded"` with `disabled_reason: "batch"`,
as well as the successful response's `ttl_disabled: true`. Existing batch
exclusion is a successful protected outcome, not an invalid state. A missing run may return
null TTL; queued/trash/purged states cannot be reported as protected because
this action cannot stop or undo deletion already started. Report these as
unconfirmed failures with a specific explanation, retaining the existing server
behavior. Cover each response state in browser-handler tests. The batch/read-only
exclusions and existing setter normalization remain unchanged.

## Regression and operator verification

Exercise the registered route with an ordinary signed-in account, read the
written TTL file, and check disable/re-enable plus its user-ID audit. Cover
anonymous rejection, run-authorization rejection without writes, and invalid
payload rejection. Render both headers for ordinary and privileged users and
anonymous visitors; verify the checkbox state after reload.

After deployment, use an ordinary account on an accessible project to toggle
the setting and reload both the project and a report. A privileged account
alone cannot validate this repair. Local tests do not establish deployment or
resolution of Marta's reported instance, whose URL/error was not supplied.

## Local repair evidence (2026-11-04)

The route, both header variants, and both user guides were confirmed consumers
of the incorrect privileged-role assumption and are repaired together. The
unchanged controller transport and TTL writer remain covered by existing tests.
Repository search also found multi-role `roles_required` decorators in
`routes/admin.py`; their intended audience is unresolved and outside this TTL
repair, so this change makes no claim about those admin operations.

The pre-fix ordinary-user route regression failed with Forbidden. After repair,
322 focused route/render/TTL tests passed; a subsequent 13-test TTL run also
passed with added real authorization/CSRF and invalid-payload coverage. Frontend
lint and 1,033 frontend tests passed. Independent correctness (`ttl_review`) and
security (`ttl_security`) reviewers reported no remaining findings after the
real authorization test was added. The full Python run was stopped at the
operator's request; it is not a completed validation gate. No production rollout
or original-incident resolution is claimed.

## Plain-language presentation (2026-11-04)

Implemented and locally validated after checkpoint `c62567f1c`; deployment separate. Both headers label the checkbox **Disable
automatic deletion**, explain that it prevents deletion due to inactivity, and
link **How to keep your project** to the existing guide ID. A persistent status
uses **Automatic deletion is disabled** for confirmed disabled/excluded policy
or **Automatic deletion is enabled for [readable date]** for a valid active
expiration. Unknown state is explicitly unavailable, never assumed disabled.
Dates are readable UTC dates with timezone indicated. Success updates status
from the returned policy. Errors restore the last confirmed checkbox value; an
uncertain network failure asks the user to reload to check whether it saved.
This avoids claiming a timed-out mutation did not reach the server.

The operator chose these exact labels to replace technical TTL wording. Internal
selectors, request keys and events stay compatible. No access or retention change.

Disabled describes the inactivity policy, not a promise that an already-started
deletion can be canceled. Help must say this control cannot undo deletion that
has already started or restore deleted projects. Existing queued/trash handling
is unchanged; this work does not redesign deletion or project recovery.
