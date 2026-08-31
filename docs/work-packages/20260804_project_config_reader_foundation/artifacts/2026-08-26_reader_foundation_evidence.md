# WP02 Reader Foundation Evidence

**Date**: 2026-08-26 UTC
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`
**Promotion policy**: merge only at the roadmap promotion gate
**Starting revision**: `ceb10fc9686925f89288d4411c3d36cd9d6ccbaf`
**Implementation revision**: `cb7698b28`

## Reader Inventory

Runtime configuration consumers converge on `NoDbBase._configparser` through
the `config_get_*` facade. Repository inventory found 32 direct `NoDbBase`
controller subclasses under `wepppy/nodb/core/` and `wepppy/nodb/mods/`; web,
rq-engine, and RQ modules obtain those controllers rather than implementing a
second config parser. The 82 route/job files matching config/controller access
therefore cross the same wired boundary. The exceptional non-run readers are
setup catalog discovery, profile seed recording, and the root-resource
migration tool; WP01 already moved those to canonical defaults resolution and
they do not reopen a run's flattened config.

The direct-reader search used:

    rg -n "_configparser|CaseSensitiveRawConfigParser" wepppy \
      -g '*.py'
    rg -l "config_get_|config_stem|\\.config\\b" \
      wepppy/weppcloud/routes wepppy/rq \
      wepppy/microservices/rq_engine -g '*.py'

## Contract Fixtures

`tests/nodb/test_project_config_reader_foundation.py` constructs these states
with real temporary files and the production parser/reader:

- default-off, explicit true/false, and invalid feature-flag values;
- valid preset-basename and fixed builder `config.cfg` flattened files;
- query-bearing stable tokens whose overrides are ignored after flattening;
- missing, malformed, unsupported, and non-boolean flattened schemas;
- legacy local and shared layering with query overrides retained;
- manifest-v1 builder, preset, and byte-copied fork provenance;
- missing/malformed/common-field-invalid/secret-bearing/newer manifests;
- filename inconsistency and digest mismatch;
- child-local legacy precedence and parent-root flattened inheritance;
- child-local flattened rejection, sibling-prefix escape, config symlink
  escape, and manifest symlink escape;
- byte-for-byte no-mutation checks for degraded reads; and
- per-controller structured-warning deduplication.

WP02 exposes immutable status for later header UI work. It deliberately adds no
route, writer, queue edge, amendment, or config/manifest repair path.

## Validation Evidence

- Focused WP02: 42 passed after the final exact-legacy-exception fixtures.
- WP02 + WP01 defaults + WP00A sanitization: 63 passed before the final
  symlink-boundary additions; the final WP02 target then passed 38 tests.
- NoDb suite: 1,699 passed, 26 skipped.
- Stubtest: `wepppy.nodb.base` and
  `wepppy.nodb.project_config_reader` passed.
- Stub completeness: passed.
- Changed broad-exception enforcement: passed with net delta zero.
- `git diff --check`: passed.
- Exact final-tree full repository suite: 6,827 passed, 63 skipped in 11m02s.

## Development Stack

The mounted feature-branch code was restarted in the services that read run
configuration:

    docker compose -f docker/docker-compose.dev.yml restart \
      weppcloud rq-engine rq-worker rq-worker-batch caddy

All five services returned to `Up`; `http://127.0.0.1:8080/` returned the
expected HTTP 301 front-door redirect. Deployment remains default-off because
WP11 owns fleet activation. The explicit enabled reader path is exercised by
the focused fixtures with `WEPPPY_PROJECT_CONFIG_READER_ENABLED=1`.

## Downstream Handoff

- WP04/WP06 consume manifest validation and filename behavior for real writers.
- WP08 consumes `updates_enabled`; digest mismatch alone remains amendment-safe.
- WP09 consumes `project_config_status` for authenticated, nonblocking header
  presentation and nested linkage. WP02 makes no UI claim beyond this seam.
- WP10 replaces synthetic fork/nested fixtures with lifecycle evidence.
- WP11 owns deployed reader flag, mixed-version, restart, and rollback proof.
