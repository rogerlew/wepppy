# Execute WP00B project configuration source normalization

This ExecPlan is maintained under `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Project-owned configs must be reproducible bytes, not whichever spelling a
particular source happened to use. WP00B supplies a typed, deterministic
serializer and converts active shared sources to one lexical form without
changing their values. A developer can verify the outcome with one source
checker and a golden round-trip test. No project writer is enabled.

## Progress

- [x] (2026-08-05 03:09Z) Verified branch and WP00R/WP00A prerequisites.
- [x] (2026-08-05 03:09Z) Imported PC-05 and five stable checklist tasks.
- [x] (2026-08-05 03:09Z) Inventoried active/default lexical forms and reader
  accessor behavior.
- [x] (2026-08-05 03:09Z) Implemented typed parsing, canonical bytes, and source
  normalization.
- [x] (2026-08-05 03:09Z) Normalized 129 sources and proved typed parity.
- [x] (2026-08-05 03:28Z) Completed broad validation, closed documentation, and
  archived this plan.

## Surprises & Discoveries

- Observation: 128 of 129 active/default files are not real TOML.
  Evidence: `tomllib` rejects their `None` values; only one source parsed.
- Observation: the corpus was already close to canonical after an older
  migration but retained 14 capitalized booleans, 31 trailing-comma lists, 51
  bare strings, one single-quoted string, and one inline numeric comment.
  Evidence: the pre-normalization lexical inventory covers 3,341 assignments.
- Observation: formatting normalization touched every active source because
  assignment spacing and terminal newlines were inconsistent.
  Evidence: the mechanical rewrite reported 129 changed files while typed
  semantic comparison reported 129 of 129 equivalent.
- Observation: two `general.locales` values used tuple syntax, an accepted list
  form that the first lexical classifier treated as a bare string.
  Evidence: the first full suite stopped at 10 percent in
  `test_controller_state_routes_accept_rollout_compatible_read_scopes`; after
  explicit tuple-to-list conversion, 99 focused tests and all 5,932 collected
  repository tests completed without failure.

## Decision Log

- Decision: treat active `.cfg` files as INI, not TOML.
  Rationale: deployed readers use `CaseSensitiveRawConfigParser`; `None` is an
  accepted null marker but invalid TOML.
  Date/Author: 2026-08-05 / Codex.
- Decision: normalize only the default and active named presets.
  Rationale: legacy pseudo-TOML is not a future resolver source and changing it
  would expand WP01 compatibility risk.
  Date/Author: 2026-08-05 / Codex.
- Decision: use typed values as the parity boundary.
  Rationale: raw byte equality would defeat normalization; accessor-compatible
  typed equality proves values did not change.
  Date/Author: 2026-08-05 / Codex.

## Outcomes & Retrospective

WP00B closed PC-05. All 3,341 assignments in 129 active/default sources now use
one of six canonical encodings, and typed comparison against the starting
revision proves value parity. The deterministic serializer has checked-in
golden bytes, stable ordering, strict ambiguity rejection, and WP00A secret
gating. The full repository result was 5,872 passed and 61 skipped. WP03 owns
registry integration; no writer was enabled here.

## Context and Orientation

The active source corpus is `_defaults.toml` plus the top-level `.cfg` files in
`wepppy/nodb/configs`. These are INI-style inputs despite the historical
defaults suffix. `wepppy/project_config_serialization.py` defines typed parsing
and byte serialization. `tools/normalize_project_config_sources.py` checks or
atomically rewrites source lexical forms. The future registry in WP03 will
produce the typed map consumed by `serialize_config`.

## Plan of Work

Inventory all active source assignments and current accessor semantics. Ratify
the smallest type system they support. Implement strict parsing and sorted
serialization with explicit rejection. Add a source-preserving normalizer,
rewrite the active corpus, and compare typed maps against the starting Git
revision. Add golden and rejection tests, run existing accessor regressions,
update the roadmap/checklist, and close the package.

## Concrete Steps

From `/home/workdir/wepppy`, run:

    /workdir/wepppy/.venv/bin/python tools/normalize_project_config_sources.py
    /workdir/wepppy/.venv/bin/python tools/check_project_config_secrets.py
    PYTHONPATH=/home/workdir/wepppy /workdir/wepppy/.venv/bin/python -m pytest tests/nodb/test_project_config_serialization.py tests/nodb/test_config_sanitization.py -q
    wctl doc-lint --path docs/work-packages/20260804_project_config_source_normalization
    git diff --check

The source checker must report 129 files with zero changes. Golden bytes must
round-trip exactly, and ambiguity tests must fail with `CanonicalConfigError`.

## Validation and Acceptance

Acceptance requires all 3,341 assignments in the supported inventory, typed
parity for all 129 sources, byte identity from equivalent maps, an exact golden
fixture, rejection of every form named by contract section 8.1, continued
WP00A secret gating, and no writer enablement.

## Idempotence and Recovery

The checker is read-only by default. `--write` writes a sibling temporary file
and atomically replaces only sources whose normalized bytes differ. Repeating
it produces zero changes. Git retains the original bytes for review or
recovery. The operation never touches legacy snapshots or project data.

## Artifacts and Notes

The lexical inventory and semantic-parity transcript are recorded in
`artifacts/2026-08-05_lexical_inventory_and_parity.md`.

## Interfaces and Dependencies

`serialize_config(mapping)` returns canonical UTF-8 bytes.
`parse_config_text(text)` accepts only canonical typed text.
`validate_canonical_config_text(text)` additionally enforces exact byte layout.
`normalize_source_text(text)` converts only inventoried legacy lexical forms.
Serialization invokes WP00A's `assert_materialization_safe` before returning.
