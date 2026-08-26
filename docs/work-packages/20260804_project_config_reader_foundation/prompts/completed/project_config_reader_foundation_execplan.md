# Deliver the project-owned configuration reader foundation

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must stay current.
Maintain it according to `docs/prompt_templates/codex_exec_plans.md`.

Initiative branch: `feature/project-owned-config`. Canonical branch: `master`.
Promotion policy: merge only at the roadmap promotion gate.

## Purpose / Big Picture

After WP02, an explicitly enabled WEPPpy reader can open a project-local config
marked as flattened without consulting mutable shared defaults or presets. A
damaged provenance manifest cannot brick an otherwise valid project, but it
does disable future updates and emits safe operator status. Nested controllers
inherit only a validated top-level authority. No package code creates or edits
either artifact.

## Progress

- [x] (2026-08-26 18:15 UTC) Verify branch/prerequisites and inventory readers.
- [x] (2026-08-26 18:15 UTC) Scaffold package and record compatibility plan.
- [x] (2026-08-26 18:30 UTC) Implement reader collaborator, feature flag, and facade integration.
- [x] (2026-08-26 18:38 UTC) Add flattened, manifest, nested, symlink, and representative reader fixtures.
- [x] (2026-08-26 19:03 UTC) Run final-tree broad validation, archive plan, and close WP02.

## Surprises & Discoveries

- Observation: all ordinary NoDb config access converges on the
  `NoDbBase._configparser` property, including route/RQ consumers through their
  controller facades.
  Evidence: repository inventory found direct `_configparser` use only in the
  base facade and controller internals, while callers use `config_get_*`.
- Observation: current nested containment uses string `startswith`, which does
  not distinguish sibling prefixes.
  Evidence: `/root/run2/child`.startswith(`/root/run`) is true despite not being
  contained.
- Observation: a compatibility collaborator can accidentally change failure
  contracts even when successful values match.
  Evidence: the first enabled legacy implementation wrapped file/parser
  exceptions and accepted `=` inside an override value; the final implementation
  preserves the original exception and split behavior, covered by direct tests.

## Decision Log

- Decision: keep the facade stable and place new resolution/validation in a
  focused collaborator.
  Rationale: one reader boundary covers web and RQ consumers and avoids growing
  the persistence facade with manifest mechanics.
  Date/Author: 2026-08-26, Codex.
- Decision: use an explicit default-off reader environment flag.
  Rationale: the roadmap requires reader-first dormant rollout and reserves
  deployed activation/rollback proof for WP11.
  Date/Author: 2026-08-26, Codex.
- Decision: manifest validity controls update eligibility, not flattened config
  loading.
  Rationale: this is the ratified degraded-mode contract and avoids silent
  shared fallback.
  Date/Author: 2026-08-26, Codex.
- Decision: reject flattened config symlink escapes, but treat a manifest
  symlink escape as degraded provenance.
  Rationale: the config is runtime authority and cannot reside outside the run
  root; the manifest is non-runtime provenance whose invalidity must not brick a
  valid config.
  Date/Author: 2026-08-26, Codex.

## Outcomes & Retrospective

WP02 is implemented and wired behind its default-off reader flag. The focused,
NoDb, and exact final-tree full suites, stack restart, stubs, docs, correctness,
and security gates pass. No writer exists. Downstream real creation, UI,
lifecycle, Forest, and rollback evidence remains with its roadmap packages.

## Context and Orientation

`wepppy/nodb/base.py` is the public NoDb facade. Its `_configparser` property
currently loads resolved defaults, then a local or shared preset, then query
overrides. WP01 made defaults discovery compatible with both `_defaults.cfg`
and `_defaults.toml`. `docs/schemas/project-owned-config-contract.md` now adds a
second mode: a project-local file whose `[config]` section says
`flattened = true`, `schema_version = 1`, and `resolver_version = 1` is complete
runtime authority and must load alone. `config-manifest.json` records provenance
but is not a source of runtime options. `parent_wd` is persisted on nested
controllers and is the only allowed parent identity when no child-local legacy
config exists.

The feature is a faithful extension: implemented means the collaborator and
facade behavior exist; wired means the central accessor calls it when the
reader flag is enabled. WP02 closeout requires both. Generated model-output
evidence is not applicable because reads must not mutate or generate run
artifacts; unchanged artifact bytes plus central-accessor fixtures are the
appropriate boundary proof. WP11 owns live Forest and rollback evidence.

## Plan of Work

Create a focused module under `wepppy/nodb/` that selects legacy, flattened,
and nested authority; validates the exact flattened marker/schema; validates
manifest-v1 structure and sanitization; computes the observed SHA-256; and
returns the parser plus immutable status. Errors for malformed or unsupported
flattened schema must be explicit. Degraded manifest conditions must return a
valid parser with updates disabled. Structured digest warnings may contain only
run ID, filename, declared digest, and observed digest.

Update `NoDbBase._configparser` to delegate only when the reader feature flag is
true. Keep the legacy body as the flag-off path. Persist the latest status on
the controller and deduplicate equivalent warnings on that instance so repeated
`config_get_*` calls do not flood logs. Replace string-prefix containment with
resolved path ancestry without changing valid nested run IDs or persistence.

Add deterministic tests under `tests/nodb/`. Construct absent, empty,
populated, valid legacy, valid flattened, malformed, unsupported, invalid
manifest, secret-bearing manifest, newer manifest, digest mismatch, child-local
legacy, child-local flattened, valid parent, and escaping parent states. Compare
legacy effective values with the flag off and marker absent. Assert read-only
operation by hashing fixture files before and after. Exercise representative
controller access used by web and RQ paths through the common facade.

Finally update the reader inventory/evidence, correctness review, security
review, package, tracker, roadmap/checklist dispositions, and project tracker.
Move this plan to `prompts/completed/` only after all gates pass.

## Concrete Steps

From `/home/workdir/wepppy`, implement with small patches and run:

    wctl run-pytest tests/nodb/test_project_config_reader_foundation.py --maxfail=1
    wctl run-pytest tests/nodb --maxfail=1
    wctl run-stubtest wepppy.nodb.base
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260804_project_config_reader_foundation
    git diff --check

Restart the development stack through the canonical `wctl` dev-compose path,
then use a temporary run fixture to show the disabled legacy path and explicitly
enabled flattened path both load. Record concise transcripts in the evidence
artifact without config contents.

## Validation and Acceptance

Acceptance requires the central accessor to return a sentinel value present
only in a valid flattened file while a conflicting shared value is ignored.
Malformed or unsupported flattened schema must raise the named reader error and
must not return the shared sentinel. Missing/invalid/newer manifests and digest
mismatch must still return the flattened sentinel, expose updates-disabled or
warning status as contracted, and leave both files byte-identical. A child with
a legacy local config must keep it; a child without one must inherit only a
contained explicit parent; sibling-prefix and escaping parents must fail.

The full suite, documentation lint, correctness review, and security review
must contain no unresolved medium/high finding. No writer, route, queue edge,
or generated config artifact may be introduced.

## Idempotence and Recovery

All implementation behavior is read-only and tests use temporary directories.
The feature flag defaults off, so reverting the integration patch restores the
existing reader without data migration. Do not delete or rewrite run configs or
manifests while debugging. If a test exposes ambiguous legacy behavior, retain
the baseline and record the conflict before changing the canonical contract.

## Artifacts and Notes

The package will retain a reader inventory/evidence artifact, a correctness
review, and the required high-impact security review. Exact test counts and the
feature-branch implementation revision will be added during closeout.

## Interfaces and Dependencies

Use Python's existing `configparser`, `json`, `hashlib`, `logging`, `pathlib`,
and immutable dataclasses; add no dependency. The collaborator must expose a
testable boolean flag seam, explicit reader exceptions, a load result containing
the `CaseSensitiveRawConfigParser`, and immutable status/warning records. The
NoDb facade must expose read-only status for later WP09 use while preserving all
existing `config_get_*` signatures.

Plan revision note (2026-08-26): initial executable plan created from the
ratified contract, roadmap, checklist, and current reader inventory.

Plan revision note (2026-08-26 18:50 UTC): recorded implemented reader,
containment/security discoveries, validation evidence, and the final exact
legacy-failure compatibility correction.

Plan revision note (2026-08-26 19:03 UTC): recorded the exact final-tree suite,
closed all WP02-local gates, and prepared the plan for archival.
