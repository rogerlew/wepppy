# Tracker - Project Config Registry and Serializer (WP03)

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-26 19:16 UTC
**Current phase**: Closed
**Last updated**: 2026-08-26 19:51 UTC
**Next milestone**: WP04 project-owned writer; WP11 retains Forest acceptance
**Security impact**: `low`
**Dedicated security review**: no
**Security artifact**: N/A
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate
**Starting revision**: `8ee87a2e65b57adcf8194a0a1dbdbd2efb902435`
**Implementation revision**: `1bb9e49f4`
**Upstream**: `origin/feature/project-owned-config`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Verified branch/upstream and WP00R/WP00B prerequisites (2026-08-26 19:16 UTC).
- [x] Imported all 20 WP03-owned checklist tasks and wrote the compatibility plan before code edits (2026-08-26 19:16 UTC).
- [x] Inventoried WP00B serializer and current continental-US runtime keys/values (2026-08-26 19:16 UTC).
- [x] Implemented typed schema, strict TOML loader, 13-document corpus, and deterministic resolver (2026-08-26 19:39 UTC).
- [x] Corrected climate IDs to the exact ratified underscore tokens during correctness review (2026-08-26 19:43 UTC).
- [x] Passed focused, NoDb, exact full-suite, stub, broad-exception, and correctness gates (2026-08-26 19:51 UTC).

## Requirement Ledger

| Contract area | Tasks | Planned evidence | Status |
| --- | --- | --- | --- |
| PC-06 | N-011, N-030, N-058, N-059, N-064 through N-067, R-003, R-029, R-030, A-003 | TOML/schema/evolution/order/writeover/stable-ID tests | verified |
| PC-07 | N-028, N-031 through N-033, N-049, R-032, R-033, R-037 | descriptor, initial matrix, exclusions, DEM defaults | locally verified; WP11 retains Forest gate |
| PC-05 integration | N-062 contribution | canonical byte round-trip from resolved registry | verified |

## Decisions Log

### 2026-08-26 19:16 UTC: Keep shared defaults as the explicit base contributor

**Context**: Shared defaults are the first composition layer but are not a
builder component document and already have a canonical typed parser.

**Decision**: Load/accept the WP00B typed defaults map as an explicit immutable
base contributor with a content revision; TOML documents own every subsequent
component write.

**Impact**: The registry does not duplicate the entire defaults file, while
resolved output remains snapshot-independent and provenance-complete.

### 2026-08-26 19:16 UTC: Make collision permission local to the later writer

**Context**: Ordered contributors may intentionally overwrite earlier values,
but undeclared collisions must fail.

**Decision**: Each component declares both owned keys and the subset it may
overwrite. A later collision without that declaration fails explicitly and
effective-writer provenance changes only after a permitted write.

**Impact**: Composition order stays expressive without turning precedence into
an implicit blanket override.

### 2026-08-26 19:16 UTC: Model initial capability selections as registered sources

**Context**: Soil, land-use, and climate IDs need durable provenance and locale
constraints even where a climate selection does not itself change a static
runtime option.

**Decision**: Register domain capability components, allow zero-write
components, and compose selected capability IDs deterministically after mods.
The umbrella capability profile owns the resolved `[capabilities]` lists.

**Impact**: Selected IDs remain explicit without inventing unsupported runtime
settings; WP05 can later enforce the same stable IDs.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Registry invents non-runtime option names | High | Low | used current normalized config keys and exact stable IDs | Mitigated |
| Writeover silently masks a collision | High | Low | declared override validation and provenance tests | Mitigated |
| Initial combination exposes unvalidated ID | High | Low | closed allowed-reference sets and matrix tests | Mitigated locally; WP11 retained |
| Result aliases mutable registry/default maps | Medium | Low | deep-copy and snapshot-independence tests | Mitigated |

## Verification Checklist

- [x] Focused WP03/WP00B tests pass.
- [x] NoDb and exact final-tree full suite pass.
- [x] Stub/API and broad-exception checks pass.
- [x] Documentation lint and `git diff --check` pass.
- [x] Correctness artifact has no unresolved medium/high findings.
- [x] No writer/route/queue/deployment flag is introduced.

## Progress Notes

### 2026-08-26 19:16 UTC: Scaffold and contract inventory

**Agent/Contributor**: Codex

**Work completed**:

- Verified the feature branch at `8ee87a2e6`, tracking its matching remote.
- Imported PC-06/PC-07 closure tasks and the WP00B integration contribution.
- Recorded the project-data compatibility plan before adding registry schemas.
- Mapped initial IDs to existing `general`, `watershed`, `wepp`, `soils`,
  `landuse`, `nodb`, and future `capabilities` sections.

**Blockers encountered**: None.

**Next steps**: Implement schema/loader, TOML corpus, resolver, and tests.

**Test results**: WP02 exact full-suite baseline is 6,827 passed, 63 skipped.

### 2026-08-26 19:51 UTC: Implementation and closure

**Agent/Contributor**: Codex

**Work completed**:

- Added immutable public records, strict atomic TOML validation, deterministic
  content revision, field-addressable selection constraints, and ordered
  resolution through the WP00B serializer.
- Added the exact continental-US v1 corpus and tests for all owned PC-06/PC-07
  tasks plus the retained PC-05 integration contribution.
- Completed correctness review with both findings resolved and explicitly
  retained deployed Forest acceptance in WP11.

**Blockers encountered**: None.

**Next steps**: WP04 consumes this resolver for first-write materialization;
WP05/WP06 expose and authorize it; WP11 validates deployed combinations.

**Test results**: 60 focused passed; 1,740 NoDb passed and 26 skipped; exact
final suite 6,864 passed and 63 skipped; stubtest/check-test-stubs/broad-
exception/diff checks passed.

**Implementation commit**: `1bb9e49f4`.

## Watch List

- WP11 must accept or remove each DEM/backend combination against deployed data.
- WP05 must consume, not re-declare, the stable capability identifiers.
