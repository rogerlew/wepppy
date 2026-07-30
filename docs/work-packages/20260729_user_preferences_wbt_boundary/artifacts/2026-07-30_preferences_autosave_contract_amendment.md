# User Preferences Auto-Save Contract Amendment

## Decision

The authenticated User Preferences page saves on change. A person does not
need to discover or press a general Save preferences button after changing
either select.

This amendment supersedes only the page-interaction sentences in the
SURF-14A contract that require a server-rendered complete-form submit followed
by POST/Redirect/GET. Account ownership, exact enum values, CSRF, atomic
two-field persistence, request-local units, initiating-user WBT behavior, and
all project nonmutation rules remain unchanged.

## Normative interaction

- Changing either select schedules one same-origin, CSRF-protected POST of the
  complete current two-field form.
- Saves are serialized. If another change occurs while a request is active,
  the latest complete form is sent after the active request finishes. An older
  response cannot replace a newer browser selection.
- The page exposes a persistent polite live region. It announces
  `Saving preferences…` while a save is active and `Preferences saved.` after
  the latest selection is confirmed.
- Confirmed success uses the standard prominent success-alert treatment,
  rather than muted helper text. The text remains in the polite live region
  so confirmation is both visually salient and announced.
- A failed save exposes a visible assertive error message and leaves the
  person's current selection available for correction or retry. It must not
  claim that unsaved values succeeded.
- The POST endpoint returns a bounded JSON success/error representation when
  JSON is requested. Ordinary form POST remains supported as a no-JavaScript
  fallback and retains server validation plus POST/Redirect/GET.
- The ordinary Save preferences button is not shown in the enhanced
  interaction. A submit control may exist only in a `noscript` fallback.
- Both controls retain programmatic labels, field help, and field-level server
  errors. The two preference groups have clear visual separation.

## User-facing meaning

- Preferences follow the authenticated account, not a project owner.
- `Auto` units use each project's saved configuration.
- SI or English changes presentation for that viewing user without changing
  the project's saved units.
- WBT `Auto` uses the project's configured boundary behavior.
- `Warn and continue` may return a boundary-touching watershed with a warning.
- `Stop with an error` stops delineation so the initiating user can choose a
  different outlet or enlarge the extent.

## Usersum link correction

The WBT Channel Delineation guide is a manifest-backed Usersum document. The
generated runtime catalog must include
`usersum.weppcloud.controls.wbt_channel_delineation`, and route regression
coverage must prove the linked
`/usersum/view/weppcloud/wbt-channel-delineation.md` alias renders.

## Regression evidence

- template assertions for current explanatory text, live regions, field
  spacing hook, auto-save script, and `noscript` fallback;
- JavaScript tests for change-triggered save, serialized latest-value replay,
  success feedback, and failure feedback;
- route tests for JSON success, JSON validation failure, atomic persistence,
  login, and CSRF behavior;
- Usersum route coverage for the exact WBT alias; and
- focused Python/frontend/accessibility validation.
