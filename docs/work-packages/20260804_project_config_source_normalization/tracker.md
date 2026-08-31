# Tracker - Project Configuration Source Normalization (WP00B)

## Quick Status

**Started**: 2026-08-05 03:09 UTC
**Current phase**: Closed
**Last updated**: 2026-08-05 03:28 UTC
**Security impact**: `low`
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `2c3816bd49`

## Task Board

### Done

- [x] Imported PC-05 and all five WP00B checklist task IDs.
- [x] Inventoried 3,341 assignments across 129 active/default sources.
- [x] Ratified six canonical scalar/list encodings.
- [x] Implemented typed parsing, deterministic serialization, and source
  normalization tooling.
- [x] Normalized all 129 sources and proved typed semantic parity.
- [x] Added golden, round-trip, rejection, source-corpus, and WP00A integration
  tests.
- [x] Corrected legacy tuple-list classification after the broad suite exposed
  the route-level regression.
- [x] Passed focused and full repository tests, closed PC-05, and archived the
  ExecPlan.

## Requirement Ledger

| Task | Evidence | Status |
| --- | --- | --- |
| `WP00B-PC05-N060` | equivalent-map byte identity test | verified |
| `WP00B-PC05-N061` | checked-in canonical-v1 golden fixture | verified |
| `WP00B-PC05-N062` | lexical inventory, normalized corpus, round trip | verified |
| `WP00B-PC05-N063` | duplicate/collision/unsupported/non-finite rejection | verified |
| `WP00B-PC05-R002` | golden bytes and stable reserialization | verified |

## Decisions

### Explicit supported type set

Only null, boolean, integer, finite float, string, and flat scalar list are
supported. This matches current reader capabilities without inventing a new
nested data model. Ambiguous forms fail instead of being guessed.

### List booleans retain Python spelling

Top-level booleans are lowercase because `config_get_bool` is case-insensitive.
List booleans use `True`/`False` because the deployed `config_get_list` uses
`ast.literal_eval`. This preserves mixed-version reader compatibility.

### Active sources only

The default and named `.cfg` presets are resolver inputs and are normalized.
Legacy pseudo-TOML snapshots keep their bytes because they begin with a
non-INI `from =` directive and remain WP01 compatibility inputs.

## Validation Log

- Source normalization: 129 files checked, zero drift after rewrite.
- Typed semantic parity: 129 of 129 sources passed against `2c3816bd49`.
- Focused serializer/sanitizer/accessor/rq-engine tests: `99 passed`.
- Full repository suite: `5,872 passed, 61 skipped` from 5,932 collected.
- Initial broad run stopped at 10 percent because two accepted tuple-list
  sources had been quoted as strings. The final focused and broad reruns passed
  after explicit tuple-to-list normalization.
