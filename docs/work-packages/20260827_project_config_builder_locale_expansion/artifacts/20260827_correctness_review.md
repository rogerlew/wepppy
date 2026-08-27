# Correctness and User-Experience Review - WP12C

## Metadata

- **Package**: `docs/work-packages/20260827_project_config_builder_locale_expansion/`
- **Initiative / canonical branch**: `feature/project-owned-config` / `master`
- **Promotion policy**: WP12C pushes the initiative branch and deploys only to
  host `forest`; WP12 owns canonical merge and production
- **Reviewer**: pending independent reviewer
- **Date**: 2026-08-27
- **Scope reviewed**: pending implementation
- **Commit/branch context**: contract checkpoint pending
- **Canonical contracts**: project-owned config sections 7.2.2, 7.4, 9, and 15

## User Outcome

- **User goal**: select one of five geographic profiles and receive only the
  datasets applicable to it, including Canada-wide global data with Daymet.
- **Success presented to the user as**: dependent selects repopulate from the
  chosen locale, review shows the exact resolved choices, and creation opens a
  self-contained Preview run.
- **Failures that may reach the user**: stale registry, missing/invalid locale
  graph, unknown component, unsupported cross-locale choice, unavailable
  provider registry, authorization/ownership failure, or initialization
  failure with diagnostic details and correlation ID where required.
- **Partial-state behavior**: validation never creates a run; creation failure
  does not publish a ready run and releases its idempotency reservation under
  the existing creation contract.

## Stored-State Matrix

| State | Valid? | Required behavior | Required direct evidence |
| --- | --- | --- | --- |
| No capability section / legacy run | yes | Preserve legacy locale/catalog behavior; never inject WP12C axes | legacy reopen fixture |
| V1 capability section | yes when valid under v1 | Enforce only present v1 axes; never infer locale graphs | v1 partial fixtures |
| Historical Continental-US v2 | yes | Parse/enforce unchanged without consulting live registry | byte-stable round trip and reopen |
| New complete v3 for any exposed profile | yes | Enforce its stored axes/relations/defaults, including station database, only | one fixture and create/reopen per profile |
| Mandatory v2 axis or relation absent | no | Explicit incompatibility; no registry fallback or mutation | hostile fixture |
| Mandatory v3 station-database axis/default absent | no | Explicit incompatibility; no registry fallback or mutation | hostile fixture |
| Mandatory v2 axis/relation empty | no | Explicit incompatibility; no mutation | hostile fixture |
| Unknown locale ID or extra graph domain value | no | Explicit incompatibility; no mutation | hostile fixture |
| Newer schema version | no for mutation | Explicit degraded incompatibility; preserve bytes | newer-schema fixture |
| Persisted current value omitted from graph | compatibility carve-out | Render current value disabled for reselection; reject a newly submitted unsupported replacement | paired render/mutation fixture |

Historical schema-v2 update availability, preview, and apply use the frozen v2
resolver and original parent chain. They never synthesize a station-database
component or selection. An unavailable historical chain reports updates
unavailable and preserves project bytes.

## Request/Input Matrix

| Input | Required behavior | Mutation outcome |
| --- | --- | --- |
| Exact valid tuple for selected locale | Resolve deterministic bytes and review | create only after explicit create request |
| Dataset from another exposed locale | field-addressable `unsupported_combination` 4xx | none |
| Station database from another locale | field-addressable `unsupported_combination` 4xx | none |
| Unknown locale or component ID | field-addressable `unknown_component` 4xx | none |
| Missing locale graph in server description/registry | explicit Builder registry failure | none |
| Missing locale component population | explicit Builder registry failure | none |
| Legacy client reading singular graph/components | expose frozen schema-v2 Continental US for parsing | creation receives `409 unsupported_builder_schema`; none |
| Description-v2 client with version and station DB | validate selected locale's schema-v3 graph | create only after explicit create request |
| Missing/unsupported description version | `409 unsupported_builder_schema` | none |
| Stale `registry_revision` | canonical `409 stale_builder_schema` | none |
| Multiple OFE with TOPAZ or non-`wepp_260803` binary | field-addressable incompatibility 4xx | none |
| Duplicate/replayed idempotency key with same body | return original successful project | no duplicate |
| Reused key with different body | canonical idempotency conflict | none |
| Lost role/auth/ownership before create | canonical authorization/ownership rejection with diagnostics | none |
| Provider unavailable while loading registry | explicit atomic registry error; do not omit one item | none |

## Review Checks

- [x] Canonical intent and both state/input dimensions are named.
- [x] Absent, empty, populated, legacy, hostile, stale, and cross-locale states
  have required behavior.
- [ ] Direct unmocked evidence exists for every changed persistence/provider
  boundary.
- [ ] Paired UI/server evidence proves valid-state noninterference and hostile
  rejection.
- [ ] Locale-keyed graph and component mappings have paired compatibility,
  missing-member, and cross-locale tests.
- [ ] Independent reviewer has dispositioned all findings.

## Findings

No implementation findings can be closed before the standalone checkpoint and
implementation revision exist.

## Verdict

- **Gate status**: fail (implementation and independent review pending)
- **Release recommendation**: hold
