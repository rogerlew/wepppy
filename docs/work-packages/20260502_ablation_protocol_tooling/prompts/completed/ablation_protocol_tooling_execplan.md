# Implement `tools/ablation_protocol.py` with test-backed parity

Outcome: Completed on 2026-05-02. Tool and tests were ported, local templates were added for default-root usability, targeted pytest passed (`17 passed`), and code-review disposition was recorded in package artifacts.

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, contributors can run `python tools/ablation_protocol.py init --incident-id <id>` to create an ablation incident folder and `python tools/ablation_protocol.py finalize --incident-id <id>` to regenerate manifest/checksum evidence with policy-era contract checks. This removes the current gap where `wepppy` referenced the ablation protocol workflow but did not ship the tool locally.

## Progress

- [x] (2026-05-02 21:17 UTC) Scoped and scaffolded work package at `docs/work-packages/20260502_ablation_protocol_tooling/`.
- [x] (2026-05-02 21:21 UTC) Ported `tools/ablation_protocol.py` implementation into `wepppy`.
- [x] (2026-05-02 21:22 UTC) Added `tests/tools/test_ablation_protocol.py` coverage and local path/marker adjustments.
- [x] (2026-05-02 21:24 UTC) Added local `docs/ablation/TEMPLATE_*` files and README for default-root usability.
- [x] (2026-05-02 21:27 UTC) Ran `wctl run-pytest tests/tools/test_ablation_protocol.py` (`17 passed`).
- [x] (2026-05-02 21:29 UTC) Completed code review sweep and updated package + project tracker docs.

## Surprises & Discoveries

- Observation: `wepppy` documentation referenced `docs/ablation/` and `tools/ablation_protocol.py`, but the tool file and template directory were absent.
  Evidence: discovery `rg` output plus `ls docs/ablation` failure before implementation.

## Decision Log

- Decision: Port behavior from `/workdir/wepp-forest/tools/ablation_protocol.py` instead of designing a reduced local variant.
  Rationale: Existing work-package artifacts already rely on that contract and test scenarios were available to validate parity.
  Date/Author: 2026-05-02 / Codex

- Decision: Add local `docs/ablation/TEMPLATE_*` files in the same package.
  Rationale: Without templates, `init` fails against the default root, leaving the tool effectively unusable in-repo.
  Date/Author: 2026-05-02 / Codex

## Outcomes & Retrospective

Delivered a working local ablation protocol toolchain with deterministic tests and review evidence. Porting implementation plus regression suite together kept semantic behavior aligned with the known upstream workflow and reduced ambiguity around policy-era validations.

## Context and Orientation

`wepppy` previously lacked `tools/ablation_protocol.py` but referenced it in package artifacts. The expected behavior existed in `/workdir/wepp-forest/tools/ablation_protocol.py` and `/workdir/wepp-forest/tests/test_ablation_protocol.py`.

Key files delivered by this plan:
- `tools/ablation_protocol.py`
- `tests/tools/test_ablation_protocol.py`
- `docs/ablation/TEMPLATE_incident.md`
- `docs/ablation/TEMPLATE_notes.md`
- `docs/ablation/TEMPLATE_matrix.csv`
- `docs/ablation/TEMPLATE_artifacts.md`
- `docs/ablation/README.md`

## Plan of Work

The implementation sequence was: scaffold package, port tool, port tests, adapt local test harness paths/markers, add required templates, run targeted validation, and capture review evidence in package docs.

## Concrete Steps

Executed from repository root `/workdir/wepppy`:

1. Copied tool and test baselines from `/workdir/wepp-forest`.
2. Adjusted `tests/tools/test_ablation_protocol.py` module path (`parents[2]`) and added `pytestmark = pytest.mark.unit`.
3. Added `docs/ablation/TEMPLATE_*` files and `docs/ablation/README.md`.
4. Ran:
   `wctl run-pytest tests/tools/test_ablation_protocol.py`
5. Ran:
   `git diff --check`
6. Updated package tracker, code review artifact, and `PROJECT_TRACKER.md`.

## Validation and Acceptance

Acceptance evidence:
- Tool supports `init` and `finalize` subcommands.
- Targeted tests passed via `wctl run-pytest tests/tools/test_ablation_protocol.py` (`17 passed, 2 warnings`).
- Code-review disposition captured in `docs/work-packages/20260502_ablation_protocol_tooling/artifacts/20260502_code_review.md`.

## Idempotence and Recovery

- `init` intentionally fails on non-empty incident directories unless `--force` is provided.
- `finalize` can be rerun repeatedly and rewrites manifest/checksum deterministically.
- If policy validation fails, errors are explicit and point to file/row for correction.

## Artifacts and Notes

- `docs/work-packages/20260502_ablation_protocol_tooling/artifacts/20260502_code_review.md`
- `docs/work-packages/20260502_ablation_protocol_tooling/tracker.md`

## Interfaces and Dependencies

- `tools/ablation_protocol.py` uses Python stdlib only (`argparse`, `csv`, `hashlib`, `pathlib`, `dataclasses`, `datetime`, `re`).
- Public workflow contract:
  - `init` subcommand creates incident scaffold from template files.
  - `finalize` subcommand validates matrix/policy metadata, writes artifact manifest, and rewrites checksums.
