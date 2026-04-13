# Execute WP-00 Parity Harness in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` were maintained during execution and are now final for WP-00 closure.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, WP-00 for Iterative First-Order Link Prune is complete in `/workdir/weppcloud-wbt`: parity fixtures are cataloged, TopAZ oracle outputs are documented and checksum-pinned, comparison harness scripts are runnable, and deterministic reruns are proven. This gives the implementation team a stable, reproducible parity baseline before WP-01+ coding starts.

## Progress

- [x] (2026-04-13 04:03Z) ExecPlan authored and activated under WEPPpy work-package procedure.
- [x] (2026-04-13 04:16Z) Executed WP-00 in `/workdir/weppcloud-wbt` and generated required artifact docs under `docs/iterative-first-order-link-prune/wp-00/`.
- [x] (2026-04-13 04:14Z) Implemented WP-00 harness utilities under `/workdir/weppcloud-wbt/tools/`.
- [x] (2026-04-13 04:16Z) Ran deterministic reruns and captured evidence in `determinism-report.md`.
- [x] (2026-04-13 04:18Z) Completed review/test/parity gate evidence and updated WP-00 orchestration row to `done`.
- [x] (2026-04-13 04:19Z) Moved ExecPlan to `prompts/completed/` and appended outcome summary.

## Surprises & Discoveries

- Observation: `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` already included WP-00 deliverable/checklist scaffolding, so execution could proceed directly.
  Evidence: WP-00 section listed required artifact and harness paths.
- Observation: deterministic canonical parity reports were identical across two clean runs while full JSON manifests differed due run-root path/timestamp fields.
  Evidence: canonical report hash `9a171ade68bfc94b31b28285bf2393ea30b3b631ac54d1f83c6f606c1d40237e` for both run1/run2.

## Decision Log

- Decision: Treat this WEPPpy work-package ExecPlan as canonical orchestration, while executing all WP-00 implementation work in `/workdir/weppcloud-wbt`.
  Rationale: Preserves established WEPPpy package governance while keeping technical changes in the WBT repository.
  Date/Author: 2026-04-13 / Codex.
- Decision: Keep TopAZ usage strictly as black-box oracle behavior evidence.
  Rationale: Maintain clean-room constraints for subsequent implementation work.
  Date/Author: 2026-04-13 / Codex.
- Decision: Define deterministic parity acceptance against a path-free canonical JSON output.
  Rationale: Absolute run paths and timestamps differ across clean runs; canonical metric payload must remain stable.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

### Artifacts produced

- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/fixture-catalog.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/topaz-oracle-manifest.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/parity-metrics-spec.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/determinism-report.md`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_prepare_fixtures.py`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_run_topaz_oracle.sh`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_compare_outputs.py`

### Parity and determinism results

- Fixture count: 3 (includes required `/wc1/runs/cl/clueless-aftertaste/dem/wbt` anchor fixture).
- Run1 parity summary: exact binary parity `3/3`, mismatches `[]`.
- Run2 parity summary: exact binary parity `3/3`, mismatches `[]`.
- Canonical determinism hash:
  - run1: `9a171ade68bfc94b31b28285bf2393ea30b3b631ac54d1f83c6f606c1d40237e`
  - run2: `9a171ade68bfc94b31b28285bf2393ea30b3b631ac54d1f83c6f606c1d40237e`

### Gates

- `cargo check -p whitebox_tools`: pass.
- `python -m py_compile tools/ifolp_wp00_prepare_fixtures.py tools/ifolp_wp00_compare_outputs.py`: pass.
- Harness end-to-end reruns: pass.

### Unresolved gaps and recommendations before WP-01

- Threshold values for two repository fixtures (`blackwood_60_5`, `gatecreek_10m_30_2`) are naming-convention inferred; confirm against original run metadata before final parity sign-off.
- WP-00 baseline compares oracle-staged candidates; WP-01+ should immediately run non-trivial candidate outputs through the same harness.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Governing documents in WBT repo:
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

Required anchor fixture:
- `/wc1/runs/cl/clueless-aftertaste/dem/wbt`

Required WP-00 output docs in WBT repo:
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/fixture-catalog.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/topaz-oracle-manifest.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/parity-metrics-spec.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/determinism-report.md`

Required WP-00 harness utilities in WBT repo:
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_prepare_fixtures.py`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_run_topaz_oracle.sh`
- `/workdir/weppcloud-wbt/tools/ifolp_wp00_compare_outputs.py`

## Plan of Work

Milestone 1 establishes reproducible fixture inventory and oracle manifest. Build a fixture catalog including the required `/wc1/runs/cl/clueless-aftertaste/dem/wbt` anchor, define fixture IDs and intended role coverage, and pin checksums for all input artifacts and generated oracle outputs.

Milestone 2 builds the harness utilities and metrics contract. Implement repeatable scripts/commands that prepare fixtures, run or ingest TopAZ oracle outputs, and compare outputs using required metrics: exact binary equality, stream-cell delta, connected components, junction count, and outlet reachability.

Milestone 3 proves determinism and records gate evidence. Run the full harness from a clean workspace at least twice, verify identical result artifacts, and publish deterministic evidence plus command transcripts. Complete review phases, disposition findings, and update WP-00 orchestration status in the implementation-plan table.

## Concrete Steps

Run from `/workdir/weppcloud-wbt`.

1. Read governing docs.
   - `sed -n '1,220p' AGENTS.md`
   - `sed -n '1,260p' docs/iterative-first-order-link-prune/specification.md`
   - `sed -n '1,340p' docs/iterative-first-order-link-prune/implementation-plan.md`

2. Create WP-00 artifact directory and seed files.
   - `mkdir -p docs/iterative-first-order-link-prune/wp-00`
   - create the four required markdown outputs listed above.

3. Implement harness utilities in `tools/`.
   - Add prepare/oracle/compare scripts with documented CLI usage.
   - Ensure scripts are idempotent and rerunnable.

4. Run harness and deterministic reruns.
   - Use a clean output directory (for example `/tmp/ifolp_wp00`).
   - Execute full run twice or more.
   - Compare hash/manifests of run outputs to prove repeatability.

5. Validation gates.
   - `cargo check -p whitebox_tools`
   - `python -m py_compile tools/ifolp_wp00_prepare_fixtures.py tools/ifolp_wp00_compare_outputs.py`
   - run documented harness command(s) end-to-end.

6. Complete documentation and status updates.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-00 table row:
     - `Status=done`,
     - `Code Review=done`,
     - `Test Gate=done`,
     - `Parity Gate=done`,
     - fill Started/Completed/Notes.

## Validation and Acceptance

This ExecPlan is accepted when all of the following are true:

- All four WP-00 artifact docs exist and are populated with reproducible commands, checksums, and results.
- Harness utilities exist and execute end-to-end without manual ad-hoc intervention.
- Determinism report demonstrates at least two identical reruns from clean output directories.
- Required parity metrics are computed for each fixture and clearly interpreted.
- WP-00 orchestration row in the WBT implementation plan is updated to `done` with gate statuses complete.

## Idempotence and Recovery

- Scripts allow safe rerun with `--overwrite` behavior.
- Oracle capture and parity outputs are run-scoped under `/tmp/ifolp_wp00/<run_id>/`.
- Canonical parity output isolates deterministic metric payloads from run-path/timestamp noise.

## Artifacts and Notes

- WP-00 artifacts remain in `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/`.
- Work-package tracker for handoff status:
  - `docs/work-packages/20260412_ifolp_wp00_parity_harness/tracker.md`

## Interfaces and Dependencies

- No production API changes are included in WP-00 scope.
- TopAZ remains an external behavior oracle dependency only; no source-code transfer is permitted.
- Existing WBT toolchain dependency for sanity gate:
  - `cargo check -p whitebox_tools`

---
Revision Note (2026-04-13 / Codex): WP-00 execution completed; plan moved from `prompts/active/` to `prompts/completed/`.
