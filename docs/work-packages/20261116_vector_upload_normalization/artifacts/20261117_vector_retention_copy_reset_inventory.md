# Retained vector evidence: copy and reset consumer inventory

Updated: 2026-11-17 UTC. Original inventory: independent `code_review` at
`ee26389f099e9e950b5920d53790f8661548a5e3`. Original Omni cleaner fix:
`860ba6760074d7db018c1b1b5a7d6f633d580b3d`. Sharing checkpoint:
`bbb216c0bc48674f8b24f5e69f20ec58e57b795a`.

## Boundary and current disposition

This inventory covers the four retained-upload roots
(`roads/vector_upload_attempts`, `ag_fields/vector_upload_attempts`,
`_pups/omni/contrasts/vector_upload_attempts`, `resources/vector_upload_attempts`)
and `archives/private`, including nested project copies. It maps project forks,
Batch generation/reset, Omni cleanup, and profile copy/reset consumers. It is not
an exhaustive audit of arbitrary filesystem operations.

**The sharing decision is resolved; lifecycle implementation and regression
coverage are mapped below. Final frozen-revision validation and independent
acceptance reviews remain pending.** The test references identify coverage in the
candidate; this inventory does not independently certify those tests as passed.

The operator explicitly permits users admitted by existing public/team copy
workflows to inherit originals, rejected attempts, receipts, and private archives.
Do not filter those records or require separate source-owner approval. Direct
sensitive-download restrictions remain unchanged. The authority and rationale are
in [the canonical contract, “Sharing, copies, and existing workspace resets”](../../../schemas/vector-upload-normalization-contract.md#sharing-copies-and-existing-workspace-resets)
and [the sharing decision](20261117_sharing_contract_decision.md).

Managed copies preserve source upload provenance and charge new physical bytes
to the verified copier, or the existing unattributed bucket for automated/legacy
callers. `retention_actor` records that charge separately from immutable upload
`actor`; `copied_from` and `copy-source-receipt.json` record inheritance. Existing
replacement/reset semantics remain authorized. Explicit offline profile exports
retain bytes under their storage owner's authority; managed reentry is charged.

## Discovery history - 2026-11-17

The original review found that whole-tree copies duplicated retained bytes without
new admission, while reset/removal paths could delete them without ledger repair.
It also observed that ordinary public-fork admission could make a source non-owner
the destination owner. The proposed source-only evidence/filter policy and its
operator-decision HOLD are superseded by `bbb216c0b`: the public/team inheritance
is intended behavior, while physical-byte accounting remains required.

The separate Omni cleaner defect was reproduced using actual cleaner functions:
both removed the owning project's `vector_upload_attempts`. Commit `860ba6760`
preserved that directory alongside `_uploads`; current wrappers additionally
account for independently retained evidence inside removed child workspaces.

## Shared implementation and regression boundary

`wepppy/microservices/vector_retention_lifecycle.py::retained_tree_operation`
wraps the existing copy/reset operation. It checks the exact configured root,
acquires global maintenance and project scopes, admits incoming bytes without
speculative deletion credit, persists a deterministic repair obligation, verifies
copied bytes/provenance, syncs evidence, rebuilds exact totals, and clears repair
markers only after successful readback. Stale/tombstone paths remain part of
configuration checks. Ordinary model symlinks may remain links; linked retained
evidence cannot be materialized as an uncharged copy. Omni can lend an already
owned scope; nonblocking maintenance acquisition avoids a lock-order wait cycle.

`tests/microservices/test_vector_retention_lifecycle.py` covers accepted/rejected/
incomplete copies, repeated-copy provenance, copier charges, quota rejection,
partial-copy retry, missing receipts, symlink rejection, borrowed scopes, active
reservation preservation, release failure, and replacement headroom. Consumer
coverage below supplements those common helper tests.

For compact references, **Fork** means `tests/rq/test_vector_fork_retention.py`,
**Routes** means `tests/microservices/test_rq_engine_fork_archive_routes.py`,
**Consumers** means `tests/nodb/test_vector_retention_copy_consumers.py`, and
**Profile** means `tests/profile_recorder/test_retained_profile_lifecycle.py`.
All test identifiers below are in those files unless explicitly qualified.

## Confirmed consumer mapping

| Consumer | Candidate implementation / operator disposition | Regression coverage |
| --- | --- | --- |
| Project fork copy | `project_rq_fork.prepare_fork_run()` wraps actual rsync in `fork_copy`, with source/destination scopes and verified copy actor. Existing copy options remain; no new sensitive-root filter. | **Fork**: `test_fork_copies_originals_and_private_archives_with_copy_charge`, `test_fork_copy_rejects_recipient_quota_before_copy`; source receipts/bytes, copied inheritance and exact principal/global totals. |
| Public/team fork admission and destination ownership | Resolved by the sharing decision. `fork_archive_routes._fork_retention_actor()` derives the copier from verified claims/user; admission stores actor metadata and `project_rq.fork_rq()` forwards it. Ownership/authentication behavior is preserved. | **Routes**: `test_fork_storage_actor_uses_verified_copier` and fork enqueue test rejecting client actor substitution; **Fork**: `test_worker_passes_admission_actor_to_fork_copy`. These are actor-boundary tests, not a claim of a deployed public-fork canary. |
| Fork target replacement | `fork_archive_routes._delete_fork_replacement_tree()` wraps rename/removal in `fork_target_replace`; a stable `.replacing-retained` tombstone supports absent-target retries. | **Fork**: `test_fork_replacement_repairs_absent_target_and_previous_tombstone`, `test_absent_fork_target_preserves_retained_tombstone_without_configuration`; partial removal/rebuild failure, either marker authority, exact totals and unchanged retained bytes on configuration failure. |
| Batch leaf creation | `BatchRunner._run_batch_hillslopes_owned()` wraps complete `_base` copy in `batch_leaf_copy` before controller rebinding. Copies inherit all five roots and use the unattributed copy-charge bucket. | **Consumers**: `test_batch_leaf_copy_preserves_all_retained_roots_and_charges_copy`; all five roots, source hashes, receipt inheritance, ordinary rerun and ledger readback. |
| Batch leaf replacement/rerun | The same `batch_leaf_copy` boundary surrounds `_reset_run_workspace()` and replacement copy; pending repair forces completion even when the ordinary reset option is disabled, and stale siblings remain charged. | **Consumers**: `test_partial_batch_copy_retry_recopies_when_reset_option_disabled`, `test_workspace_retry_requires_identity_for_retained_stale_sibling[batch]`; common helper replacement-headroom regression. |
| Batch Omni subtree reset | `batch_rq._reset_omni_nodb_from_base()` wraps source/destination Omni subtree copy/removal in `batch_omni_reset`; no whole-project-only shortcut. | **Consumers**: `test_batch_omni_subtree_reset_accounts_removed_and_copied_attempts`; source and old destination evidence, rebound controller path and exact ledger. |
| Batch base initialization | `BatchRunner._init_base_project()` wraps removal/recreation in `batch_base_reset`. Fresh initialization stays valid; retained old-base bytes are reconciled. | **Consumers**: `test_batch_base_reinitialization_reconciles_removed_evidence`. |
| Omni bulk/stale cleanup | `_clean_contrast_runs()` and `_clean_stale_contrast_runs()` retain owning `_uploads`/`vector_upload_attempts`, and use `omni_contrast_cleanup` for removable children. | `tests/nodb/mods/test_omni_state_contrast_mixin.py::test_contrast_cleanup_preserves_retained_upload_bytes` covers clean/stale/reset/clear; **Consumers**: `test_omni_bulk_cleanup_retry_preserves_owner_evidence_and_repairs_absent_children`, `test_omni_cleanup_borrows_live_upload_scope_and_preserves_reservation`. |
| Omni scenario/contrast workspace reset and individual child deletion | `omni_clone_contrast_service._reset_workspace()` uses `omni_workspace_reset`; `_remove_scenario_artifacts()` / `_clean_contrast_run()` use their individual delete identities. Absent-child retry and deferred stale bytes remain observable/accounted. | **Consumers**: `test_omni_workspace_reset_counts_deferred_stale_evidence`, `test_workspace_retry_requires_identity_for_retained_stale_sibling[omni]`, `test_omni_single_child_delete_repairs_after_child_is_absent`. |
| Profile promotion | `ProfileAssembler.promote_draft()` marks capture and whole-run promotion as explicit exports (`profile_promote_capture`, `profile_promote_run`). Outside the managed root, original bytes/modes remain intact without run-filesystem charge. | **Profile**: `test_offline_promotion_preserves_complete_retained_records_without_runfs_configuration`; common helper `test_explicit_export_inside_root_requires_identity` prevents an export flag from bypassing a managed destination. |
| Profile sandbox clone / snapshot fallback | `services/profile_playback/app.py::_prepare_sandbox_clone()` and `_prepare_sandbox_run()` use `profile_sandbox_clone` / `profile_sandbox_reset`. Existing snapshots receive the same managed reentry accounting as new exports. | **Profile**: `test_managed_profile_reentry_preserves_provenance_and_charges_copy`, `test_evidence_reentry_does_not_classify_missing_configuration_as_offline_export`, `test_interrupted_profile_clone_retains_repair_and_retry_converges`. |
| Profile archive export | `archive_profile()` wraps output replacement/copy in explicit `profile_archive_export`; private archives remain included. Outside-root exports are not additional run-filesystem bytes. | **Profile**: `test_archive_export_copies_all_records_outside_runfs_without_charging_export`; compares complete exported/sandbox records and managed totals. |
| Profile deterministic playback and sandbox cleanup | `PlaybackSession._prepare_run_directory()` uses `profile_playback_reset`; service sandbox removal is inside the copy/reset boundaries above. | **Profile**: `test_deterministic_playback_reset_releases_old_retained_charge`, `test_deterministic_playback_reset_without_identity_preserves_existing_evidence`; interrupted clone/retry tests exercise reused sandbox destinations. |
| Developer smoke clone | `project_rq.test_run_rq()` wraps existing target removal/full source copy in `test_run_copy`, before the model pipeline. It remains a callable developer consumer, not a newly exposed browser workflow. | **Fork**: `test_developer_test_run_replaces_and_accounts_before_pipeline`, with absent and existing destination states, originals, unattributed charge and exact totals. |

## Verified negative and excluded paths

| Path | Retained-root disposition and evidence boundary |
| --- | --- |
| Ordinary `OmniCloneContrastService.omni_clone()`, `run_contrast()`, `_omni_clone_sibling()` copy bodies | Copy selected model roots/root NoDb files; other traversal creates empty directories rather than retained payloads. No new evidence-copy filter is needed. Destination resets are covered separately above. |
| Roads `_prepare_roads_runs_workspace()` and model-output cleanup; AgFields WEPP/watershed cleanup | Operate below generated-artifact roots, outside retained attempts. Existing canonical model inputs remain within normal workflows; the exact downstream suite exercises real Roads/AgFields artifacts. |
| Omni report-sidecar cleanup | Targets `<run>/omni/contrasts`, distinct from owning retained attempts under `<run>/_pups/omni/contrasts`. This is not the reproduced cleaner loss. |
| Profile config-seed initialization | Copies selected configuration rather than the full recorded project. **Profile**: `test_config_seed_playback_does_not_expand_into_full_snapshot_copy`. Profile fork output uses the ordinary fork worker and inherits its managed copy boundary. |
| Culvert clone/reset and D-Tale | Explicit package scope exclusions remain. No claim that current culvert inputs contain retained vector evidence or that these paths were qualified. |
| Bearer-protected test-support deletion (`wepppy/weppcloud/routes/test_bp.py::_cleanup_run_directory`, `delete_run_endpoint`) | Fixture-only exclusion, not a product delete consumer or retention-safe cleanup claim. The endpoint still removes whole test trees directly. Retention lifecycle tests use disposable roots and explicit accounting teardown; they do not establish safe ledger repair through this endpoint. |

## Remaining acceptance evidence

The mapping replaces the obsolete HOLD/filter recommendation with the ratified
byte-preserving policy and candidate implementation. It does not close M5 on its
own. Freeze the integrated revision, retain exact commands/results/skips and
ledger/artifact readback, and complete independent correctness, code, QA,
security and operations reviews. Preserve the explicit exclusions above and
resolve any confirmed remaining consumer defect before claiming closure.
Publication, production deployment and remote-host parity remain separate gates.
