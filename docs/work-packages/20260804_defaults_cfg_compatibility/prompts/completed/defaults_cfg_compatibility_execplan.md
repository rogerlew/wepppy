# Execute WP01 defaults CFG compatibility

This ExecPlan is maintained under
`docs/prompt_templates/codex_exec_plans.md`. It is a living document; the
`Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes &
Retrospective` sections must remain current throughout execution.

## Purpose / Big Picture

WEPPpy currently gives its shared INI-style defaults file a misleading TOML
suffix. WP01 makes `_defaults.cfg` canonical while keeping every legacy project
and older deployed reader working. A developer can observe the outcome by
opening the canonical file directly, opening the old name through a relative
symlink, and running a matrix proving local/shared precedence without changing
effective parameter values. No flattened-config writer is added or enabled.

## Progress

- [x] (2026-08-26 17:12Z) Verified branch, upstream tracking, WP00R, and the
  completed WP00A/WP00B prerequisites.
- [x] (2026-08-26 17:12Z) Inventoried requirements, reader paths, direct
  consumers, tests, tooling, and documentation.
- [x] (2026-08-26 17:12Z) Scaffolded package/tracker/plan and recorded the
  compatibility/regression plan before editing schema paths.
- [x] (2026-08-26 17:18Z) Moved the shared file, created the relative alias,
  implemented four-name precedence, and excluded the reserved seed from named
  preset discovery.
- [x] (2026-08-26 17:26Z) Updated direct consumers, tools, tests, and
  user/developer documentation; focused tests and docs lint pass.
- [x] (2026-08-26 17:41Z) Passed targeted, NoDb, full repository, docs, stub,
  broad-exception, normalization, secret, and live development-stack gates.
- [x] (2026-08-26 17:41Z) Completed correctness review, WP11 handoff, roadmap,
  tracker/package closure, and archived this plan.

## Surprises & Discoveries

- Observation: `_defaults.toml` is parsed by `RawConfigParser`, not a TOML
  parser, and WP00B already canonicalized its INI-like content.
  Evidence: `NoDbBase._configparser` calls `read_file`; WP00B typed tests cover
  129 default/preset sources.
- Observation: defaults selection is centralized for controllers but several
  setup/profile/migration consumers still obtain or spell the shared path
  independently.
  Evidence: repository inventory at starting revision `c45726072`.
- Observation: moving defaults under the `.cfg` suffix made the file match the
  existing named-preset glob.
  Evidence: `get_configs()` used an unfiltered `configs/*.cfg` glob; WP01 now
  excludes the reserved `_defaults` stem and tests the 128-preset inventory.

## Decision Log

- Decision: use ordered existing-file selection and retain parser behavior.
  Rationale: the contract changes authority precedence, not syntax or error
  translation; selected malformed files must keep failing explicitly.
  Date/Author: 2026-08-26 / Codex.
- Decision: retain one regular shared file plus one relative symlink.
  Rationale: mixed-version readers must see identical bytes and cannot tolerate
  two independently maintained copies.
  Date/Author: 2026-08-26 / Codex.
- Decision: treat this as a faithful migration requiring fixture and running
  development-stack evidence.
  Rationale: a renamed file alone is not proof that current and old consumers
  are wired.
  Date/Author: 2026-08-26 / Codex.
- Decision: exclude only the exact reserved `_defaults` stem from named-preset
  discovery.
  Rationale: this prevents the canonical seed from becoming user-selectable
  without speculating about other underscore-prefixed future files.
  Date/Author: 2026-08-26 / Codex.

## Outcomes & Retrospective

WP01 closed as implemented on the feature branch. PC-02 is verified and PC-03
is locally verified with deployed Forest/rollback evidence retained by WP11.
The canonical file and relative alias work through current and old readers,
all four precedence locations are covered, the running development stack uses
the canonical path, 128 presets remain discoverable, and no writer was added or
enabled. The full suite passed with 6,785 tests and 63 skips. The key lesson is
that a suffix-only source migration also changes glob membership; the reserved
defaults seed now has an explicit catalog regression.

## Context and Orientation

`wepppy/nodb/configs/_defaults.toml` is the current shared defaults source;
despite its suffix, it contains the same INI-like syntax as named `.cfg`
presets. `wepppy/nodb/base.py` layers defaults and a selected preset in
`NoDbBase._configparser`; `_resolve_defaults_path` currently checks only the
legacy basename in the project directory and then the one shared path.
`get_default_config_path` exposes that shared path to setup discovery and
profile recording. `wepppy/tools/migrations/unroll_root_resources_batch.py`
also resolves project-local/shared defaults. WP01 must change those discovery
paths without changing parsed values, query overrides, or the serialized
`NoDbBase._config` token.

The canonical contract is
`docs/schemas/project-owned-config-contract.md`, especially sections 6.2, 6.3,
14.1-14.3, and 15. The roadmap assigns PC-02 and PC-03 plus twelve checklist
tasks to WP01. Shared `_defaults.toml` compatibility is temporary, but support
for a project-local legacy `_defaults.toml` is permanent.

## Plan of Work

First rename the tracked shared regular file to `_defaults.cfg` without byte
changes and create `_defaults.toml` as a relative symlink. In
`wepppy/nodb/base.py`, define canonical and legacy shared paths, make
`get_default_config_path()` prefer canonical and fall back to the shared alias,
and make each controller choose project-local cfg, project-local toml, shared
cfg, then shared toml. Do not catch open/parser errors.

Next update direct consumers and WP00B tooling so new output and checks name
the canonical source while explicit legacy fixtures continue to cover the old
name. Add a focused NoDb compatibility module that constructs every precedence
state with distinguishable values, proves normal defaults-plus-preset
layering, exercises missing and malformed failures, inspects the repository
symlink through an older hard-coded reader, and proves persisted config tokens
contain neither defaults basename. Update configuration documentation.

Finally run targeted tests, the complete NoDb and repository suites, stub/API
gates if applicable, Markdown lint, and a restarted development-stack probe.
Record exact results in the tracker and this plan. Produce a correctness review
artifact because production reader behavior changes. Close the package and
move this ExecPlan to `prompts/completed/` only after all local exit gates pass;
WP11 retains Forest deployment acceptance.

## Concrete Steps

From `/home/workdir/wepppy`:

    git branch --show-current
    rg -n "_defaults\\.(toml|cfg)" wepppy tests tools docs
    wctl run-pytest tests/nodb/test_defaults_cfg_compatibility.py
    wctl run-pytest tests/nodb --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl run-stubtest wepppy.nodb.base
    wctl doc-lint --path docs/work-packages/20260804_defaults_cfg_compatibility
    git diff --check

The focused matrix must pass every ordered location and explicit failure. The
repository shared paths must report `_defaults.cfg` as a regular file and
`_defaults.toml -> _defaults.cfg` as a relative symlink. The running dev stack
must import `get_default_config_path()`, open the returned file, and resolve a
known default option.

## Validation and Acceptance

Acceptance requires observable proof that project-local cfg wins all other
names, project-local toml wins both shared names, canonical shared cfg wins its
legacy alias, and the alias remains a working fallback. A preset still layers
over the selected defaults. Missing defaults and malformed selected defaults
fail explicitly. Current and old hard-coded readers see the same bytes. A
serialized controller retains its original config token and contains no
defaults filename. WP00B normalization/parity checks still pass. All relevant
tests and documentation checks are green, and the dev stack uses the canonical
path with no writer flag enabled.

## Idempotence and Recovery

The source move is recoverable through Git. Recreating the exact relative
symlink is idempotent after verifying its target. Resolver selection is
read-only and deterministic. Tests use temporary directories and do not mutate
run data. If broad validation finds an unrelated failure, record it separately;
do not weaken precedence or add fallback exception handling. The user's
pre-existing dirty files are outside WP01 scope and must remain untouched.

## Artifacts and Notes

The tracker will hold concise test transcripts and a WP11 handoff. The
correctness review will enumerate absent, malformed, canonical-only,
legacy-only, and both-present states. No production or Forest deployment is
authorized by this package.

## Interfaces and Dependencies

`get_default_config_path() -> str` returns the first existing shared defaults
path in canonical-then-legacy order. `NoDbBase._resolve_defaults_path() -> str`
returns the first existing defaults path in project-cfg, project-toml,
shared-cfg, shared-toml order, or the canonical shared path when none exists so
the subsequent open raises the existing explicit `FileNotFoundError`. No new
external dependency, config token, manifest, feature flag, or writer API is
introduced.

Plan revision note (2026-08-26 17:12 UTC): Initial self-contained WP01 plan
created from the ratified contract, roadmap, checklist, and source inventory.

Plan revision note (2026-08-26 17:26 UTC): Recorded completed implementation,
the preset-glob discovery/correction, focused results, and the remaining broad
validation work.

Plan revision note (2026-08-26 17:41 UTC): Recorded all final gates, closure
evidence, WP11 deployment handoff, and the completed outcome.
