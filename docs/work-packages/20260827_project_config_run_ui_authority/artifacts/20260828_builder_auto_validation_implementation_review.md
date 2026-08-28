# Config Builder Automatic Validation Implementation Review

## Review identity

- Amendment: `PC-13/WP12D-20260828-6`
- Baseline checkpoint: `8e62aefba55349ae2ee94c4faf27e83a99417dfa`
- Candidate branch/HEAD: `feature/project-owned-config` at
  `1e8efa20a9bcfe0a01f1264f3ec53713a5f71e7e`
- Review date: 2026-08-28
- Reviewer: independent `implementation_correctness_review` agent
- Scope: the five ratified source/test/documentation paths plus read-only
  confirmation that the ignored generated `controllers-gl.js` contains the
  changed controller source

## Verdict

**READY** after final remediation and generated-runtime parity review.
Unresolved findings: High 0; Medium 0; Low 0.

The implementation correctly removes the manual Review Selections action,
automatically validates once after successful description hydration, retains
change-triggered validation, ignores obsolete validation responses, disables
selection controls during description reload and after its failure, preserves
validation diagnostics, and avoids focus movement during automatic validation.
CBAV-IMP-01 and CBAV-IMP-02 are resolved. The exact current ignored
`controllers-gl.js` bundle contains the reviewed source behavior loaded by the
page.

## Findings

### Resolved High - CBAV-IMP-01: a form change could defeat creation idempotency while Create was active

The initial candidate's `ConfigBuilder.create()` used the shared `busy` flag to
reject a second immediate click and allocated one `creationKey` for the request
(`config_builder.js:392-405` at initial review). Selection controls remained
enabled while that request was pending. The delegated change handler cleared
`creationKey` and called `validate()` (`config_builder.js:522-535`). A fast
validation response then set
the same shared `busy` flag to false and enables Create
(`config_builder.js:346-377`) even though the first creation request is still
unresolved.

The reviewed remediation adds a dedicated `creating` state, disables every
selection control for the active request, ignores programmatic change events
while creating, and re-enables the controls only on a non-stale failure.
Validation state can no longer clear the active creation key or re-enable
Create. The deferred-creation regression proves one `/create` request, one
unchanged key, no extra validation, disabled controls during the request, and
control recovery after failure.

Disposition: **resolved**.

### Resolved Medium - CBAV-IMP-02: stale selections/defaults/replacements are exact

The initial stale-reload path captured the prior complete selection object at
`config_builder.js:442`, but restoration at `:482-504` visits only the ordinary
graph-default fields. A still-allowed `cellsize_override` was never restored;
`_renderCellsize()` subsequently reset it to the DEM default at `:240-254`.
That silently discards a registered user selection.

In that initial candidate, `_setOptions()` announced the browser's newly
selected first option at `config_builder.js:131-152`. The defaults loop later
changes that field to its registered graph default at `:482-504`. When the
default is not the first option, the live explanation names a value different
from the value actually validated. Model selections that remain registered but
become relationship-incompatible are likewise reduced to the first compatible
tuple by `_renderDependencies()` at `:188-210`, rather than explicitly applying
the affected fields' current graph defaults. Repeated replacements also
overwrite the single change-reason node, so the page need not explain every
replacement.

The reviewed remediation now validates a prior backend/representation/binary
tuple as a relationship, applies the exact graph defaults when that tuple is no
longer valid, restores a still-allowed `cellsize_override` after dependency
rendering, and announces standard-field replacements only after their final
values settle. The regression exercises a non-first DEM default, invalidated
Multiple OFE tuple, preserved non-default override, final labels, and refreshed
validation payload.

The final remediation also compares the prior `cellsize_override` with the
final effective selection. If refreshed allowed sizes remove it or override
capability disappears, the payload omits the override and the live reason names
the Advanced cell-size override plus the exact registered DEM default. The new
regression removes `30` from the refreshed allowed set and asserts the final
`10` control value, omitted payload field, exact announcement, and refreshed
registry revision on validation. Disposition: **resolved**.

## Confirmed conformance and validation evidence

- Initial hydration issues one description request followed by one validation,
  renders only the server review, enables Create, and preserves focus.
- User changes invalidate prior review state and validation sequence guards
  reject obsolete validation responses.
- Description-load sequence state invalidates prior validation, disables all
  selection controls, and leaves them disabled with the exact description-load
  diagnostic after failure.
- Refreshed validation failure retains its field association, page summary,
  diagnostic details, and disabled Create state.
- The template contains no Review Selections control or dead validation hook;
  the actual rendered-template test checks the remaining review and Create
  surfaces.
- The ignored generated bundle contains the new description sequence,
  creation-pending lifecycle, final advanced-override announcement, and no dead
  Config Builder validation hook.

Independent focused checks:

- `wctl run-npm test -- config_builder`: 18 tests passed after final remediation.
- `wctl run-pytest tests/weppcloud/routes/test_config_builder_ui.py
  --maxfail=1`: 8 tests passed.
- `wctl run-npm lint`: passed.
- Scoped `git diff --check`: passed.

The complete frontend suite also passes 817 tests across 107 suites, and the
complete Python suite passes 7,269 tests with 63 skipped. These broader gates
were recorded after the independent source and runtime-parity review.

These green checks confirm the implemented happy path, creation isolation,
stale-refresh preservation/defaulting, removed-override announcement, failure
diagnostics, focus behavior, and rendered-template surface.

## Release disposition

Amendment `PC-13/WP12D-20260828-6` is implementation **READY** for its bounded
WP12D handoff. CBAV-IMP-01 and CBAV-IMP-02 are closed. This review does not
authorize backend, payload, deployment, merge, or production changes; those
remain outside this amendment and reserved to the parent WP12 gate.
