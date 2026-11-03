# Current-project v2 recovery: independent sequence review

Reviewer: `mipa_contract_correctness`, 2026-11-03 UTC. Additive review; earlier
declarations, reviews and failed v1 outputs remain unchanged. No native model call
or original-project mutation was performed by this reviewer.

## Finding and bounded disposition

**Source review PASS for fresh v2 preparation and the declared public-controller
sequence.** The observed failure is a harness lifecycle omission. The initial
review missed that manually resetting only runs/output omitted `Wepp.clean()` and
its other required directories; the failed attempt remains a failed workflow.
No native or scientific failure is inferred from that directory error.

Independent v1 readback confirmed all 66 hillslope completion logs and the
watershed completion log contain the expected r7 role-specific binary hashes.
The workflow then failed at `Wepp.make_loss_grid` when GDAL could not create
`wepp/plots/loss.tif`. No completed-workflow receipt exists. All 3,374 protected
original source files still match the pre-copy inventory.

`run_wepp_rq` invokes `wepp.clean()` before preparation
(`wepppy/rq/wepp_rq.py:799`). The canonical method resets runs, output, plots,
stats, flowpath runs and flowpath output (`wepppy/nodb/core/wepp.py:2037`). The
v2 helper preserves each of these existing copied directories before invoking
the actual method. Rebased NoDb paths and containment assertions protect the
original project. `ensure_bootstrap_main` is a no-op for this bootstrap-disabled
source. The normal map-resolution calls remain, and complete `prep_hillslopes`
already includes phosphorus/baseflow maps and every configured runtime companion.
No additional preparation prerequisite was identified for this configuration.

## Controller scope versus RQ scope

The parent explicitly retained the previously declared public-controller lane;
this review does not substitute a manually reconstructed queue pipeline.

- The queued MOFE pipeline skips the separate loss-grid job
  (`wepp_rq_pipeline.py:356`), whereas public `Wepp.run_watershed` invokes loss-grid
  generation with configured spatial export (`wepp_run_service.py:325`). V2
  retains and tests that public method's behavior, with its directory prerequisite
  now supplied. It does not disable export to hide the failure.
- RQ cleanup separately relocates `tc_out.txt` and creates TC interchange
  (`wepp_rq_stage_post.py:112`); the public method leaves that file in runs.
  This was confirmed in v1. RQ also provides return-period TSV export and
  query-engine activation beyond this bounded lane.
- These differences are documented in the v2 protocol. The result must not be
  described as RQ/browser rollout, queue-pipeline parity, TC/return-period export
  acceptance or query-catalog availability. Existing Roads lifecycle/accounting
  checks remain separate.

The unchanged execution sequence remains full native hillslopes, canonical fresh
hillslope interchange with raw files retained, and public watershed execution
including configured reports/export. Preparing watershed inputs before freezing
the declaration is sound here: `WeppPrepService.prep_watershed` consumes prepared
project/configuration data and does not consume native hillslope outputs. The
original NoDb/config, binary and runtime-flag bindings remain in the v2 executor.

## Exact reviewed sources and remaining checks

| Artifact | SHA256 |
| --- | --- |
| `current_r7_project_v2.py` | `911c81cb979b58331efa5d97a54cda59471bfb2f61656350e9b5be17b07f6006` |
| `execute_current_r7_project_v2.py` | `a30a61f2a832e6c57274c68fc857fd375132b9ffdb14befa29aa22211d8b720b` |
| `resumption-r7-current-project-v2-protocol.md` | `3e83851c0f5ae4b0324d12e2629bf86dad4431de61b35626440d68eb8a403ce5` |

After preparation, require fresh declaration/input readback, the six canonical
directory targets, source integrity and the retained 66-hill/193-OFE/16-year
configuration before execution. Compare newly prepared native input semantics
with v1 to confirm that cleanup introduced no model-treatment change. Following
execution, verify actual binary traces, calendars, fresh native/interchange
artifacts and the configured controller report/export products. Source review
alone does not claim successful recovery or scientific acceptance.
