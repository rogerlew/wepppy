# Execute WP-05 Iterative Parity Remediation (Cycle-N)

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current.

## Purpose / Big Picture

Drive additional WP-05 remediation cycles for residual IFOLP parity mismatches (`F-002`, `F-003`, `F-004`) with strict sequence control and anti-retest governance:
1. bounded hypothesis-driven modification,
2. immediate parity testing,
3. post-parity code review/disposition.

## Anti-Retest Gate (Mandatory)

Before any code edit:
1. Assign/update a hypothesis ID in `hypothesis_log.md`.
2. Define `change_fingerprint`.
3. If the same fingerprint already has a terminal disposition (`confirmed`, `rejected`, `partial`, `deferred`), do not run unless retry-gate evidence is logged.
4. Retry-gate evidence must be one of:
   - fixture provenance changed,
   - oracle/harness contract changed,
   - previous run invalid,
   - materially different code path (new fingerprint + `supersedes`).

## Progress

- [x] Activate cycle-N hypothesis candidates in `hypothesis_log.md`.
- [x] Execute exactly one bounded hypothesis modification with unique fingerprint.
- [x] Run immediate parity compare and record evidence.
- [x] Execute post-parity code review/disposition.
- [x] Repeat for additional hypotheses as needed.
- [x] Run full run1/run2 reruns and confirm canonical determinism hash stability.
- [x] Run final gates (`cargo check`; targeted IFOLP tests).
- [x] Update tracker + mismatch disposition + WBT implementation-plan row.
- [x] Execute second clean-room TopAZ contract investigation for F-003/F-004 with explicit F-002 regression check.
- [x] Patch IFOLP specification and WP-05 artifacts (`second_clean_room_analysis.md`, tracker, mismatch disposition).
- [x] Update WP-00 parity protocol to enforce basin-masked apples-to-apples candidate/oracle comparisons (tooling + docs + determinism rerun).
- [x] Archive this plan to `prompts/completed/` at cycle closure.

## Surprises & Discoveries

- H-004 (`phase_b.tie_break_last_within_epsilon.v1`) changed unit-test-observable tie behavior but had zero fixture-level parity movement.
- Retained-state canonical hash stabilized at `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` across run1/run2 basin-masked reruns.
- Current WP-00/WP-05 oracle capture path is checksum-pinned `snapshot_copy`; it does not encode native-runtime executable/build/options identity for non-anchor fixtures.
- Non-anchor fixture thresholds (`blackwood_60_5`, `gatecreek_10m_30_2`) remain inferred from naming convention, preventing high-confidence root-cause closure.
- Manual map QA discovered stage-alignment mismatch in visualization/comparison inputs: candidate rasters are full-extent binary (`0/1`) while oracle rasters are channel-only (`1` + `NoData`); basin-masked diagnostics are required to interpret pruning direction reliably.
- Protocol remediation landed: WP-00 tooling now defaults to basin-mask comparison domain and pins basin-mask checksums in fixture manifests, preventing future stage-mismatch parity misreads.
- Provenance-aligned threshold probes (`blackwood 5/60`, `gatecreek 2/30`) produced deterministic low residual FP-only deltas (probe hash `cd013e16...`), and stakeholder accepted current Rust behavior as effectively parity-equivalent for WP-05 closure.

## Decision Log

- Rejected H-004 and reverted it because parity metrics and canonical hash were unchanged, so retaining the behavior change added no remediation value.
- Kept IFOLP code unchanged during second clean-room cycle and prioritized specification hardening plus provenance/runtime contract classification as the lowest-risk path to unblock F-003/F-004 attribution.
- Applied oracle/harness contract update (retry-gate category) by moving parity acceptance to basin-masked comparison domain with deterministic v2 reports.
- Closed WP-05 with effective parity acceptance after H-009/H-010/H-011 retained-state verification and provenance-aligned non-anchor probes.

## Outcomes & Retrospective

- Executed iterative anti-retest-compliant cycles through H-011 plus provenance probe evidence capture (H-005 partial).
- Final retained code state includes H-002 + H-009 + H-010 + H-011.
- Required final gates passed:
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`
- Second clean-room cycle delivered specification-level contract closure:
  - added explicit provenance/runtime/unit/numeric/pass-ordering/acceptance contracts to IFOLP specification,
  - published second investigation artifact with first-divergence localization, topology-context decomposition, and boundary sensitivity evidence,
  - confirmed no F-002 regression signal under bounded CSA/MSCL/epsilon perturbations.
- Closure disposition:
  - anchor fixture reached exact parity,
  - non-anchor residuals are low-severity and stakeholder-accepted as effective parity equivalence for WP-05 scope.

## Concrete Steps

Run from `/workdir/weppcloud-wbt` unless noted.

1. Confirm baseline artifacts and existing canonical hash:
   - `/tmp/ifolp_wp05_remediate/run1/reports/parity-report.final.canonical.json`
   - `/tmp/ifolp_wp05_remediate/run2/reports/parity-report.final.canonical.json`

2. In `/workdir/wepppy`, update `hypothesis_log.md`:
   - Add/refresh `H-00x` row with unique fingerprint.
   - Check duplicate fingerprint rule.
   - If retrying, log retry-gate evidence.

3. Implement one bounded code change in IFOLP modules and targeted tests.

4. Immediate parity evidence:
   - `cargo build -p whitebox_tools`
   - regenerate candidate outputs for affected fixtures.
   - `python tools/ifolp_wp00_compare_outputs.py ... --output-json ... --canonical-json ...`
   - append results to `hypothesis_log.md`.

5. Post-test review/disposition:
   - classify findings with severity.
   - update `mismatch_disposition.md`.

6. Iterate steps 2-5 until convergence point for this cycle.

7. Full reruns for retained change set:
   - rerun run1 + run2 parity reports.
   - `sha256sum` canonical reports and confirm stability.

8. Final validation gates:
   - `cargo check -p whitebox_tools`
   - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

9. Update governance artifacts:
   - `tracker.md`
   - `hypothesis_log.md`
   - `mismatch_disposition.md`
   - `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/implementation-plan.md`

## Acceptance

Cycle is complete only when:
- no duplicate fingerprint attempts were executed without retry-gate evidence,
- each executed hypothesis has parity evidence and disposition,
- retained change set passes rerun determinism and required cargo gates,
- residual mismatches are either reduced or explicitly hard-blocked with new evidence.
