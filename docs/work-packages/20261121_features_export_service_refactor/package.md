# Features Export service refactor

**Status** Closed 2026-11-21
**Timezone** UTC

## Scope

Give carrier identity alignment and cached artifact validation explicit homes
so maintainers can follow export orchestration in
`wepppy/nodb/mods/features_export/service.py`. This package targets faithful
extraction with the current request, artifact, cache, and publication contracts.

## Complexity Budget

Use two internal Python modules and the existing join planner, cache metadata,
and format checks. The existing service calls and focused tests provide the
acceptance path. The budget has no infrastructure or dependency additions.

## Generated Artifact Validation

Use existing fixtures that select a real spatial layer and read its generated
ZIP, GeoPackage metadata, and feature table. Run the cache-hit and regeneration
cases against on-disk job and cache metadata, and the published download cases
against the persisted registry. Include carrier tests for identity key selection
and rejection of ambiguous mappings. Fixture inputs exercise the changed
boundaries in a disposable local test environment. The acceptance claim is
local validation of the refactor.

## Review and Acceptance

Security impact is low. Cache format eligibility is security-adjacent, so
review its handling of invalid artifacts and retain the service's run-relative
path resolution and call sites. Access control and publication authority follow
the existing service contract. Dedicated security review is optional for low
impact. There is no parameterization change.

The maintainer owns execution and integration. Acceptance requires the
extractions to be wired into the existing service, focused tests and artifact
readback to pass, and a commit-preserving PR merge to master. The operator
waived the full test suite.

## Outcome

The service delegates carrier identity alignment and cached artifact format
checks through its existing calls. The service decreased from 3,629 to 3,061
lines. [Validation evidence](artifacts/validation.md) records 231 focused
passes and the fixture artifact readback.
