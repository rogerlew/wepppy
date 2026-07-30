# SURF-01 Pure UI Public Creation/CAP Contract

**Status**: Closed 2026-07-29 UTC
**Package ID**: SURF-01
**Security impact**: `high`

## Purpose

Verify public and authenticated run-creation surfaces from registry-informed
rendering through CAPTCHA gating, exact form submission, CAP verification, and
creation handoff.

## Concise Intent Contract

The public interfaces page renders only launch configurations permitted by the
feature registry and shows one maturity label per interface card. Anonymous
launch forms are POST forms with an exact configuration, optional overrides,
one section-owned CAP token, and a disabled launch action until that section's
widget provides a nonempty token. One solved section enables only its forms;
missing tokens open that section's prompt and do not submit.

Authenticated users retain the same permitted launch identity without an
anonymous CAP requirement. The authenticated create index renders the
server-provided configuration catalog and exact override variants. Portland,
Seattle, and SPU regional forms retain their fixed configuration/override
payloads and anonymous CAP gating. The JOH page is presentation-only and does
not invent a launch mutation.

The CAP client is safe on absent DOM and repeated execution, uses native form
submission so browser form/CSRF behavior remains authoritative, and never
reflects token contents. CAP library, missing-widget, verification, registry,
and creation failures remain visible and fail closed. Server verification
accepts only a successful CAP response and records the verified session
without logging token contents.

## Scope

- `wepppy/weppcloud/templates/interfaces.htm`;
- `wepppy/weppcloud/templates/run_0/create_index.htm`;
- `wepppy/weppcloud/templates/cap_gate.htm`;
- `wepppy/weppcloud/templates/locations/{joh,portland,seattle,spu}/index.htm`;
- `wepppy/weppcloud/controllers_js/interfaces_captcha.js` and generated parity;
- interfaces, create-index, location, and CAP verification route producers;
- exact render, executable client, route, registry, CAP, and creation-handoff
  evidence.

## Exclusions

SURF-04 owns the fork console. SURF-13 owns login/registration CAP forms.
Feature-registry metadata and role policy remain governed by the canonical
feature-registry specification. This package does not add a configuration,
location, CAPTCHA provider, authentication method, creation field, route,
queue edge, fallback, or parameter default.

SURF-14A does not alter the rq-engine create handoff. Anonymous/CAP and
authenticated launches continue to use explicit form input and project
configuration without account-preference lookup. Account units are resolved
later as request-local presentation, and WBT behavior is resolved when an
account-bearing user submits delineation. All public, regional, and
authenticated forms still converge on the same `POST /create/` endpoint. See
`../20260729_user_preferences_wbt_boundary/`.

## Acceptance

Actual renders prove exact action/method/config/override/CAP/widget/asset/
maturity identity for anonymous, authenticated, regional, and hostile inputs.
Executable client tests prove section isolation, blocked/allowed submission,
absent DOM, repeated execution, empty solve, and missing prompt/widget behavior.
Route tests prove role-filtered registry output, CAP configuration, successful
and rejected verification, safe logging, authenticated create-index variants,
regional contexts, and exact creation handoff. A dedicated security review
must pass with no unresolved high or medium finding.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; the operator directed SURF-01
  execution and the package preserves existing creation values and defaults.

## Related Packages

- **Depends on**: SHR-01/02 consumer evidence and verified SHR-04A/04B.
- **Related**: `docs/work-packages/20260728_pure_ui_security_auth_forms_contract/`
- **Unlocks**: SURF-04 Pure UI fork console contract.

## Security Review Gate

Anonymous creation crosses registry authorization, CAPTCHA, session, browser
form, external verification, and rq-engine creation boundaries. A dedicated
security review is required at `artifacts/2026-07-29_security_review.md`.

## Outcome

SURF-01 closed with exact public, authenticated, regional, hostile-value, and
presentation-only render evidence; seven executable CAP-client tests; retained
route, session, logging, and rq-engine creation evidence; and a passing
high-impact security review. No production repair, parameter change, queue
change, generated-bundle rebuild, or compatibility behavior was required.
