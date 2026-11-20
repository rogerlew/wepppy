# WEPP Exec legacy alias decision

Starting revision `9b78a9d66333fb643327beff26dbc663b2d11999`. On 2026-11-20 the
operator directed that the WEPP Exec hint appear only when `latest` is selected,
that the picker hide `latest`, and that the backend continue to accept it.
[ADR-0154](../../../adrs/ADR-0154-deprecate-wepp-latest.md) records the deprecation.

This is an intended run-page presentation change under the
[contract-first standard](../../../standards/contract-first-change-standard.md).
The [WEPP Exec contract](../../../ui-docs/contracts/wepp-exec-version-selection-contract.md)
governs the change. The [shared controller contract](../../../ui-docs/controller-contract.md)
continues to govern select fields and their submission. The
[executable selection contract](../../../schemas/wepp-executable-selection-contract.md#run-page-deprecation-of-latest-2026-11-20)
defines the exception to parity with API enums. Project-specific
capability rules in the
[project-owned config contract](../../../schemas/project-owned-config-contract.md)
continue to govern the supplied explicit choices.

The alias will be unavailable for a new selection. Existing alias projects
retain the saved value until another choice is made. Scope excludes Config
Builder, AgFields, executable lookup, and request parsing. The presentation
change does not add a security boundary or a fallback executable.

Check absent or empty choices, supported explicit values and saved legacy
values. Verify the run-page serializer keeps the current alias and that
native form omission preserves the saved setting. A new choice cannot
reselect the alias, and the hint appears only while the alias is active.
Other unavailable values retain the existing disabled treatment.
Malformed submissions still use the existing server validation.

Implementation conformance is pending independent review and validation.

## Independent reviews

- Compatibility review accepted preserving saved and disabled states. The
  hint stays outside the field's persistent accessible description, so it
  leaves the reading order when hidden.
- Scope and security review accepted the reciprocal contract links and
  existing API validation. WebKit keyboard testing showed that hiding the
  option alone still allowed reselection. Mark the saved option disabled and
  hidden. The run-page JSON serializer retains the selected value and native
  omission continues to preserve the project's setting.

Both reviewers found the updated scope ready for implementation.
