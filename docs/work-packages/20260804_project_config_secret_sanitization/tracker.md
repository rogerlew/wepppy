# Tracker - Project Configuration Secret Sanitization (WP00A)

## Quick Status

**Started**: 2026-08-04 23:59 UTC
**Current phase**: Closed
**Last updated**: 2026-08-05 00:04 UTC
**Security impact**: `high`
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `5d43a8bb00`

## Task Board

### In Progress

- None.

### Done

- [x] Imported PC-04 and all five WP00A checklist task IDs.
- [x] Inventoried 270 tracked shared configuration sources.
- [x] Traced `w3w_api_key`; confirmed no current runtime consumer.
- [x] Removed seven stale key assignments from active and legacy sources.
- [x] Implemented redacted config, manifest, directory, ZIP, and tar scanning.
- [x] Added focused regression tests and operator CLI.
- [x] Completed validation and security disposition.
- [x] Closed PC-04 and archived the ExecPlan.

## Decisions

### Stale What3Words key removal

The identical value appeared in four active/default sources and three legacy
sources. Current code never reads `w3w_api_key` and performs no What3Words API
request. The retained `Ron.w3w` property only reads historical `_w3w` state.
The key is therefore removed rather than migrated to a live runtime secret.

### Narrow, structural classification

The gate classifies option names and structural runtime references. It does not
use entropy or opaque-value guessing, which would create fragile false
positives in scientific identifiers. Findings contain source, location, key,
and rule only; raw values never enter the finding object or CLI output.

### Downstream invocation ownership

WP00A supplies and verifies the gate. WP04 and WP06 own invocation before
project publication, while WP10 owns archive-path integration and WP11 owns
Forest evidence. This package proves those boundaries with synthetic artifacts
without claiming those later packages are executed.

## Requirement Ledger

| Task | Evidence | Status |
| --- | --- | --- |
| `WP00A-PC04-N003` | source inventory, redacted pre-write API | verified |
| `WP00A-PC04-N092` | secret/host-bound classification tests | verified |
| `WP00A-PC04-N093` | stale removal, scanner, security review | verified |
| `WP00A-PC04-N098` | writer remains disabled; callable gate exists | verified |
| `WP00A-PC04-R054` | project/manifest/ZIP/tar rejection tests | verified |

## Validation Log

- Host scanner: passed for all 270 source files.
- Host focused tests: `16 passed, 2 warnings`.
- Mypy: success for both production modules.
- Broad-exception readback: only narrow `JSONDecodeError`,
  `UnicodeDecodeError`, and `tarfile.ReadError` catches exist. The repository
  changed-file helper passed but did not include untracked files, so this manual
  readback is the applicable evidence.
- `wctl run-pytest` unavailable because the dev `weppcloud` service is down;
  the repository virtualenv uses the same locked requirements and passed.
