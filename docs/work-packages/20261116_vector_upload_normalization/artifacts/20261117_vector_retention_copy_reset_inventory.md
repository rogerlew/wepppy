# Retained vector evidence: copy and reset consumer inventory

Date: 2026-11-17 UTC. Reviewer: independent `code_review` agent. Inventory source:
`ee26389f099e9e950b5920d53790f8661548a5e3`; Omni cleaner closure inspected at
`860ba6760074d7db018c1b1b5a7d6f633d580b3d`.

## Boundary and current disposition

This is the failure-class inventory for the four exact retained-upload roots
(`roads/vector_upload_attempts`, `ag_fields/vector_upload_attempts`,
`_pups/omni/contrasts/vector_upload_attempts`, `resources/vector_upload_attempts`)
and `archives/private`. It covers project fork, Batch generation/reset, Omni
clone/cleanup and profile copy/reset consumers. It does not authorize a new clone
retention policy or broaden the package into arbitrary storage cleanup.

**HOLD for clone/reset acceptance pending the operator's retention disposition.**
Public fork can copy sensitive bytes into a destination owned by a source
non-owner. Whole-tree copies duplicate charged originals/receipts without fresh
admission, and whole-tree resets remove them without the retention lifecycle.
The independent, immediate Omni cleaner data-loss defect is closed separately.

## Confirmed consumers

| Consumer and source seam | Exact effect on these roots | Smallest control seam / required proof |
| --- | --- | --- |
| `project_rq_fork._build_fork_rsync_cmd()` and `prepare_fork_run()` (`wepppy/rq/project_rq_fork.py:580`, `:1349`) | `rsync -a` copies the complete project, except existing model-output/Omni exclusions. All retained roots and private archives are otherwise included; nested Omni children are included too. Source run authorization is broader than sensitive-evidence authorization. | One rsync filter policy at command construction, enforced again at the actual worker boundary if the injectable command builder remains. Prove every retained root/nested root disposition, canonical accepted-input preservation and source-byte preservation. |
| Fork admission and destination ownership (`wepppy/microservices/rq_engine/fork_archive_routes.py:950`, `:1462`) | Ordinary public-run access/anonymous CAPTCHA admits a fork; an authenticated requester is added to destination ownership (`:1542`). Therefore source non-owner access plus a full copy grants sensitive evidence access at the destination. | Keep public forking behavior while applying the ratified evidence-copy policy. Test source non-owner → destination owner and sensitive file readback/absence, rather than checking only rsync arguments. |
| Fork target replacement (`fork_archive_routes.py:1413-1429`) | Existing destination is renamed to a tombstone and recursively deleted. Any already retained destination evidence disappears, independently of whether new source copies exclude it. | Before rename, classify/fence the destination and implement the operator-selected preservation or refusal policy. Source exclusions alone do not close this consumer. |
| Batch leaf creation (`wepppy/nodb/batch_runner.py:563-593`) | `shutil.copytree(base_wd, runid_wd)` includes all retained roots and private archives from `_base`, with original receipt identities and no new charge. | One copytree ignore/filter seam for leaf creation; retain accepted canonical inputs and detached NoDb behavior. Prove the destination evidence disposition and unchanged source hashes. |
| Batch leaf rerun (`batch_runner.py:_reset_run_workspace`, `:580-582`) | Moves the whole existing leaf to `.stale.*`, then removes it; cleanup failure leaves the old evidence under the renamed tree. Neither success nor deferred cleanup updates accounting. | Classify before rename. Preserve or refuse evidence-bearing reset according to the ratified policy; test both successful removal and deferred cleanup, with accounting and original-byte readback. |
| Batch Omni reset (`wepppy/rq/batch_rq.py:_reset_omni_nodb_from_base`, `:147-181`, caller `:975`) | Removes destination `_pups/omni`, then copies source `_pups/omni`. This directly deletes and recopies Omni attempts even if whole-project copytree is fixed. | Apply the same copy policy to this subtree and a separate destination-preservation guard before removal. Cover existing leaf evidence and base evidence independently. |
| Batch base initialization (`batch_runner.py:_init_base_project`, `:1105-1110`) | Constructor calls this helper; it deletes an already existing `_base` before creating Ron. A repeated initialization can remove base-run evidence. | Classify before destructive initialization. The normal fresh-base path is unaffected; test repeated initialization with retained evidence. |
| Omni cleanup (`wepppy/nodb/mods/omni/omni_state_contrast_mixin.py:_clean_contrast_runs`, `_clean_stale_contrast_runs`) | Previously treated `vector_upload_attempts` as a generated contrast directory and removed it. Called by clear/reset/build or orchestration cleanup. | **Closed at `860ba6760`:** both cleaners preserve the exact retained directory alongside `_uploads`; regression tests cover clean/stale/reset/clear entrypoints. |
| Omni scenario/contrast workspace reset (`omni_clone_contrast_service.py:_reset_workspace`, callers `:142`, `:349`) and `_remove_scenario_artifacts()` / `_clean_contrast_run()` (`omni_state_contrast_mixin.py:173`, `:567`) | Removes a complete existing child project. If that child contains independently retained evidence, it is removed without accounting. The ordinary clone code does not itself seed those bytes (see negative inventory below). | Guard the same workspace deletion seam against evidence-bearing descendants. Distinguish a normal generated child with no evidence from a child with independently retained uploads; do not claim actual admission into a child was runtime-tested in this inventory. |
| Profile promotion (`wepppy/profile_recorder/assembler.py:156`) | Copies full `run_src` to `<profile>/run` with `dirs_exist_ok=True`, including retained evidence/private archives. Copying into the data repo can cross the configured retention filesystem. | Filter at the whole-run snapshot copy. Prove retained evidence disposition and ordinary replay assets; separately retain the configured profile authority boundary. |
| Profile sandbox cloning (`services/profile_playback/app.py:_prepare_sandbox_clone`, `:590`) and snapshot fallback (`_prepare_sandbox_run`, `:568-569`) | Copies the entire promoted snapshot into a fresh sandbox, carrying any evidence copied by old/current promotion. | Apply the copy policy when consuming snapshots too; filtering only future promotion leaves existing snapshots affected. |
| Profile archive export (`services/profile_playback/app.py:764-770`) | Removes an existing output and copies all of sandbox `archives`, including `private`. | Apply the ratified private-archive policy at archive export; a whole-project filter alone misses this subtree copy. |
| Profile playback cleanup (`wepppy/profile_recorder/playback.py:_prepare_run_directory`, `:121`) | Removes the previous deterministic playback workspace. The service also has several UUID sandbox cleanup calls before initialization. Retained uploads made during an earlier playback can be removed without accounting. | Classify existing workspace before cleanup. Fresh UUID cleanup is normally empty; deterministic reuse is the confirmed retained-workspace risk. |
| Developer smoke clone (`wepppy/rq/project_rq.py:test_run_rq`, `:912-962`) | Removes `<runid>-latest` and copies the complete source. Same copy/reset semantics, although no in-repository enqueue caller was found. | Treat the callable as an operator/developer consumer; apply the common policy if it remains supported, or explicitly exclude it from closure with documented enforcement. Do not label it an ordinary browser path. |

## Verified negative and excluded paths

- Ordinary `OmniCloneContrastService.omni_clone()` copies only `disturbed`, `rap`,
  `landuse`, `soils` and root NoDb files. Its final traversal creates empty
  directory structure for other roots, without copying their files. It does not
  copy the retained payloads or receipts. `run_contrast()` likewise copies only
  selected model roots and NoDb state. `_omni_clone_sibling()` replaces only
  disturbed/landuse/soils. Their destination resets remain listed above.
- Roads `_prepare_roads_runs_workspace()` copies only baseline `wepp/runs` into
  Roads model runs; Roads output cleanup and AgFields WEPP/watershed cleanup
  operate below generated-artifact directories, outside the retained roots.
- Omni report-sidecar cleanup targets `<run>/omni/contrasts`, distinct from the
  retained root under `<run>/_pups/omni/contrasts`; it is not the confirmed loss.
- Profile config-seed initialization copies the selected configuration directory,
  not an entire project. The snapshot fallback and explicit sandbox clone are
  the affected branches. Profile fork output uses the ordinary fork worker and
  therefore inherits its copy policy.
- Culvert clone/reset code contains whole-tree operations, but culvert API paths
  are explicitly excluded by the work package and were not promoted to closure
  consumers. Their presence is not a claim that current culvert inputs contain
  any of these retained roots.
- The bearer-protected test-support delete endpoint also removes whole test run
  trees (`wepppy/weppcloud/routes/test_bp.py:67`, `:169`). It is outside the four
  product workflows but can delete runs created for end-to-end testing. Record
  its fixture-cleanup disposition; do not count it as a normal user delete path.

## Evidence and closure requirements

The inventory used source traces of `copytree`, rsync command construction,
recursive removal and rename-before-remove paths in the named subsystems.
There is no claimed exhaustive arbitrary-filesystem audit.

The Omni defect was independently reproduced with the actual frozen cleaner
functions and a temporary production-shaped retained root. Both returned
`original_survives: false`. Review of `860ba6760` confirms both exact exclusions
and four cleanup-entrypoint regressions; downstream tests now use the actual
workflow directories and read the receipt after real Omni build/report work.

The smallest shared copy seam is a pure relative-path policy derived from the
existing five sensitive-root definitions, reused by rsync filters and copytree
ignore callbacks. It should not parse retained bytes or grant access. The
smallest reset seam is an evidence-presence preflight before each whole-workspace
rename/removal, followed by the operator-selected preservation/refusal lifecycle.
The existing global-maintenance/project-scope/obligation/rebuild mechanism remains
the accounting authority for any authorized deletion; a new queue or datastore
is unnecessary.

Before closing this failure class, retain one table mapping every confirmed row
to its implementation/test or explicit operator disposition. Tests must place
sentinels in all five roots, retain original/receipt hashes, check canonical model
input survival, exercise destination replacement as well as initial copy, and
read exact ledger totals where bytes are duplicated or removed. A blanket
"fork fixed" claim is insufficient for Batch subtree reset and old profile
snapshot consumption.
