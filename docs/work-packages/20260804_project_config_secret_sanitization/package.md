# Project Configuration Secret Sanitization (WP00A)

**Status**: Closed (2026-08-05)
**Security impact**: `high`
**Initiative branch**: `feature/project-owned-config`
**Canonical branch**: `master`

## Overview

WP00A removes credential material from the shared NoDb configuration corpus and
provides the reusable fail-closed gate that future project-config writers and
archive validation must invoke. It closes PC-04 without enabling any flattened
configuration writer.

## Scope

Included work comprises all 270 tracked active, legacy, and batch NoDb config
sources; classification of secret-bearing and runtime-host-bound forms; removal
of confirmed stale credentials; a redacted source/project/archive scanner; unit
tests; operator/developer guidance; and dedicated security review.

Excluded work comprises canonical scalar/list encoding (WP00B), defaults file
renaming (WP01), writer integration (WP04/WP06), lifecycle integration (WP10),
deployment (WP11/WP12), credential rotation, and feature-flag enablement.

## Owned Requirements

- PC-04.
- `WP00A-PC04-N003`
- `WP00A-PC04-N092`
- `WP00A-PC04-N093`
- `WP00A-PC04-N098`
- `WP00A-PC04-R054`

## Success Criteria

- [x] The 270-file source corpus contains no classified secret or host-bound
  materialization value.
- [x] The stale `w3w_api_key` literal is absent from active and legacy sources.
- [x] A reusable pre-write API rejects unsafe config and manifest text without
  retaining or printing raw values.
- [x] The CLI scans sources, project directories, manifests, ZIP files, and tar
  files without extraction.
- [x] Tests cover source, generated-project, manifest, ZIP, and tar boundaries.
- [x] Dedicated security review has no unresolved high or medium finding.
- [x] Documentation and repository checks pass.

## Compatibility and Regression Plan

The removed key has no current code consumer: repository search finds only
stale config assignments and historical What3Words-derived display state.
Removal therefore preserves current runtime behavior. Existing data paths,
URLs, and ordinary project options remain allowed; the gate rejects only
classified secret names, a small explicit host-bound key set, environment
references, secret-file paths, and credential-bearing URIs. Future writers
must call `assert_materialization_safe` before publishing project artifacts.

## Deliverables

- `wepppy/project_config_sanitization.py`
- `tools/check_project_config_secrets.py`
- `tests/nodb/test_config_sanitization.py`
- `artifacts/2026-08-04_configuration_inventory.md`
- `artifacts/2026-08-04_security_review.md`
- `prompts/completed/project_config_secret_sanitization_execplan.md`

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Rationale**: no model default, formula, threshold, conversion, or fallback
  heuristic changes.

## Dependencies and Handoff

WP00R is complete at commit `5d43a8bb0`. WP00A does not advance WP00B or WP01.
When closed, WP04, WP06, WP10, WP11, and WP12 inherit the scanner and must
provide their package-specific project/archive invocation evidence.
