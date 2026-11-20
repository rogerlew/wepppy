# ADR-0154: Deprecate the WEPP latest alias

Status: Accepted
Date: 2026-11-20

## Context

WEPPcloud projects can store `latest` as their executable selection. The
shipped Linux executable for that alias is byte-identical to
`wepp_dcc52a6` and `wepp_dcc52a6_hill`.

## Decision

Officially deprecate `latest` in WEPP Advanced Options > WEPP Exec. Remove it
from the choices users can pick. When a project has `latest` saved, show it as
the current value and display a short deprecation hint until the user picks a
specific version.

Keep `latest` pinned to `wepp_dcc52a6` for existing projects and retain existing
backend acceptance rules. Future releases do not move the pin. The user can
select `wepp_dcc52a6` explicitly to retain this executable.

## Rationale and alternatives

Moving the alias with releases could change results on reruns of a saved
project and obscure the model build that produced them. Removing the alias
would break projects that have it saved. Leaving it selectable would
continue to invite ambiguous version choices.

## Decision provenance

The WEPPcloud operator approved the pin, compatibility policy, and scoped UI
deprecation in the November 20, 2026 task conversation. Codex implemented
the presentation and documentation changes.

## Evidence and rollback

The
[WEPP Exec version selection contract](../ui-docs/contracts/wepp-exec-version-selection-contract.md)
defines the presentation rules. The
[WEPP Forest changelog](../../wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md)
records the compiler, source commit, and legacy build. The picker change can be
reverted independently of the pinned executable.
