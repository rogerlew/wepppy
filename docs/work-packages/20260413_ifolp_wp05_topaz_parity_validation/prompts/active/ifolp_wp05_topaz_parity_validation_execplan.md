# Execute WP-05 TopAZ Parity Validation for IFOLP in weppcloud-wbt

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this plan is executed, IFOLP parity against TopAZ-oracle fixture outputs is either confirmed or mismatches are fully triaged with reproducible evidence and disposition. This creates the acceptance baseline required before robustness hardening (WP-06) and optimization (WP-07).

## Progress

- [x] (2026-04-13 08:00Z) ExecPlan authored and activated.
- [ ] Prepare fixture manifests and verify required anchor inclusion.
- [ ] Capture and checksum-verify oracle rasters for run1.
- [ ] Generate IFOLP candidate outputs for run1 and run parity comparison.
- [ ] Repeat full run as run2 and confirm canonical determinism hash stability.
- [ ] Triage/disposition parity mismatches with severity and root-cause category.
- [ ] Apply required parity fixes in IFOLP code and rerun parity until acceptance criteria are met.
- [ ] Complete code-review findings/disposition with no unresolved high/medium issues.
- [ ] Run validation gates and update WBT WP-05 row to `done`.
- [ ] Archive ExecPlan to `prompts/completed/` with closure outcomes.

## Surprises & Discoveries

- Observation: WP-00 currently validates harness determinism by copying oracle outputs into candidate paths; WP-05 must replace that with real IFOLP candidate generation.
  Evidence: `docs/iterative-first-order-link-prune/wp-00/determinism-report.md` run transcripts copy `oracle/*/stream.tif` into `candidate/*/stream.tif`.
- Observation: IFOLP is now fully executable (Phase A + Phase B + output write) and no longer uses a Phase B placeholder.
  Evidence: `iterative_first_order_link_prune.rs` now runs input preparation, Phase A, Phase B, and `write_stream_mask_output`.

## Decision Log

- Decision: Use WP-00 fixture/oracle/metrics tooling as the canonical parity harness for WP-05 rather than introducing a second comparison path.
  Rationale: Keeps parity evidence and thresholds consistent across work packages.
  Date/Author: 2026-04-13 / Codex.
- Decision: Require two full reruns (`run1`, `run2`) and canonical report hash equality before claiming deterministic parity.
  Rationale: Single-run parity can mask nondeterministic behavior.
  Date/Author: 2026-04-13 / Codex.

## Outcomes & Retrospective

- Pending execution.

## Context and Orientation

Primary execution repository:
- `/workdir/weppcloud-wbt`

Required governing docs:
- `/workdir/weppcloud-wbt/AGENTS.md`
- `/workdir/weppcloud-wbt/DEVELOPING_TOOLS.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/fixture-catalog.md`
- `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/wp-00/parity-metrics-spec.md`

Required harness/tooling assets:
- `tools/ifolp_wp00_prepare_fixtures.py`
- `tools/ifolp_wp00_run_topaz_oracle.sh`
- `tools/ifolp_wp00_compare_outputs.py`
- `target/debug/whitebox_tools` or `target/release/whitebox_tools`

## Plan of Work

Milestone 1 prepares reproducible parity inputs and oracle outputs. Generate a run-root fixture manifest, confirm the required anchor fixture is present, and stage oracle captures with checksum verification.

Milestone 2 generates IFOLP candidate outputs and computes parity metrics. Run IFOLP per fixture with manifest-provided thresholds and compare candidate/oracle outputs using WP-00 parity metrics.

Milestone 3 validates determinism and dispositions findings. Repeat the full campaign in a second run-root, compare canonical hash outputs, and disposition every mismatch/review finding with severity and rationale.

Milestone 4 finalizes WP-05 closure. Apply any required parity fixes, rerun parity and gates, update WBT/WEPPpy trackers, and archive this ExecPlan.

## Concrete Steps

Run from `/workdir/weppcloud-wbt`.

1. Prepare fixture manifests.
   - `python tools/ifolp_wp00_prepare_fixtures.py --run-root /tmp/ifolp_wp05/run1 --overwrite`
   - `python tools/ifolp_wp00_prepare_fixtures.py --run-root /tmp/ifolp_wp05/run2 --overwrite`

2. Verify required fixture inclusion.
   - `jq -r '.fixtures[].fixture_id' /tmp/ifolp_wp05/run1/manifests/fixture-manifest.json`
   - Confirm `clueless_aftertaste_anchor_10_100` is present.

3. Stage oracle captures.
   - `./tools/ifolp_wp00_run_topaz_oracle.sh --manifest /tmp/ifolp_wp05/run1/manifests/fixture-manifest.json --oracle-root /tmp/ifolp_wp05/run1/oracle --overwrite`
   - `./tools/ifolp_wp00_run_topaz_oracle.sh --manifest /tmp/ifolp_wp05/run2/manifests/fixture-manifest.json --oracle-root /tmp/ifolp_wp05/run2/oracle --overwrite`

4. Build IFOLP executable.
   - `cargo build -p whitebox_tools`

5. Generate candidate outputs from IFOLP for each run-root.
   - Use the manifest to invoke `target/debug/whitebox_tools` for each fixture with:
     - `--run=IterativeFirstOrderLinkPrune`
     - `--d8_pntr=<staged d8 raster>`
     - `--upstream_area=<staged area raster>`
     - `--output=<candidate/<fixture_id>/stream.tif>`
     - `--csa=<manifest thresholds.csa_ha>`
     - `--mscl=<manifest thresholds.mscl_m>`
     - add `--esri_pntr=true` if `pointer_encoding == "esri"`.

6. Compute parity metrics and canonical reports.
   - `python tools/ifolp_wp00_compare_outputs.py --manifest /tmp/ifolp_wp05/run1/manifests/fixture-manifest.json --oracle-root /tmp/ifolp_wp05/run1/oracle --candidate-root /tmp/ifolp_wp05/run1/candidate --output-json /tmp/ifolp_wp05/run1/reports/parity-report.json --canonical-json /tmp/ifolp_wp05/run1/reports/parity-report.canonical.json --fail-on-mismatch`
   - `python tools/ifolp_wp00_compare_outputs.py --manifest /tmp/ifolp_wp05/run2/manifests/fixture-manifest.json --oracle-root /tmp/ifolp_wp05/run2/oracle --candidate-root /tmp/ifolp_wp05/run2/candidate --output-json /tmp/ifolp_wp05/run2/reports/parity-report.json --canonical-json /tmp/ifolp_wp05/run2/reports/parity-report.canonical.json --fail-on-mismatch`

7. Validate determinism.
   - `sha256sum /tmp/ifolp_wp05/run1/reports/parity-report.canonical.json /tmp/ifolp_wp05/run2/reports/parity-report.canonical.json`
   - Hashes must match.

8. Mandatory mismatch/review disposition.
   - Record each mismatch and review finding with:
     - severity (`high`/`medium`/`low`),
     - root-cause category,
     - disposition (`fixed`/`accepted`/`deferred`),
     - evidence (report paths, fixture IDs, test output).
   - Closure gate: no unresolved high/medium findings.

9. Required gates after any parity-fix edits.
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

10. Update status artifacts.
   - Update `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md` WP-05 row:
     - `Status=done`
     - `Owner=<executor>`
     - `Code Review=done`
     - `Test Gate=done`
     - `Parity Gate=done`
     - fill `Started`, `Completed`, `Notes` with parity/disposition summary.

## Validation and Acceptance

This ExecPlan is accepted when all of the following are true:

- Required anchor fixture is present in parity manifest.
- Candidate outputs exist for every fixture and pass geometry checks.
- Parity report indicates exact-binary parity for accepted fixtures per WP-00 metrics.
- Canonical parity report hash is identical across reruns.
- Mismatch/review findings are dispositioned with no unresolved high/medium items.
- `cargo check` and targeted IFOLP tests pass after parity fixes.
- WBT WP-05 row is marked `done` with review/test/parity gates complete.

## Idempotence and Recovery

- Always use `--overwrite` for run-root regeneration to avoid stale artifacts.
- If parity mismatch persists, isolate by fixture and rerun only that fixture after fix.
- If determinism hash differs across reruns, stop closure and record the divergence cause before proceeding.

## Artifacts and Notes

- WP-05 governance tracker:
  - `docs/work-packages/20260413_ifolp_wp05_topaz_parity_validation/tracker.md`
- WBT status table:
  - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`
- Expected parity artifacts:
  - `/tmp/ifolp_wp05/run1/reports/parity-report.json`
  - `/tmp/ifolp_wp05/run1/reports/parity-report.canonical.json`
  - `/tmp/ifolp_wp05/run2/reports/parity-report.json`
  - `/tmp/ifolp_wp05/run2/reports/parity-report.canonical.json`

## Interfaces and Dependencies

- Preserve IFOLP interface contract from WP-01 and algorithm semantics from WP-03/WP-04.
- Reuse WP-00 harness contracts; do not introduce alternate parity metric definitions in WP-05.
- No WEPPpy integration changes in WP-05.

---
Revision Note (2026-04-13 / Codex): Initial WP-05 ExecPlan authored with deterministic-rerun parity and mandatory findings-disposition closure gates.
