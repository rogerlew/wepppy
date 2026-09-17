# S01 Omni SBS input identity: bounded correctness proposal

**Confirmed defect; proposed upload-content correction, not implementation
approval.** No production/tests, named runs, model execution or queue wiring were
changed. Parent will draft the canonical checkpoint. This proposal does not
certify all raster sidecars or change C07 completion ordering.

## Actual supported path and evidence

1. `omni_routes._prepare_omni_scenarios` saves one upload with overwrite into
   `omni/_limbo/<index>/<filename>`. Accepted upload suffixes remain tif/tiff/img,
   with the existing 100-MB bound. Programmatic `sbs_file_path` is also supported.
2. `OmniInputParsingService.parse_scenarios` keeps SBS type and selected path.
   `_scenario_name_from_scenario_definition` uses the filename for stable scenario
   naming; do not put a content digest into that public name or rename the child.
3. `OmniStationCatalogService.scenario_signature` currently serializes only the
   definition. Both direct and RQ parent reuse compare that signature and the
   dependency loss SHA1. Direct orchestration additionally checks year-set parity;
   RQ currently does not. Preserve that existing distinction in this bounded fix.
4. The worker receives the parent's `signature`, and normally publishes it after
   execution without rechecking selected SBS content. Both direct execution
   passes have the same admission concern. Merely hashing at enqueue time would
   permit queued/execution-time drift to receive the older signature.
5. `OmniCloneContrastService.omni_clone` recreates the scenario child and copies
   the parent's `disturbed/`. `OmniModeBuildServices.apply_scenario_mode` copies
   **only the selected main file** over `child/disturbed/<basename>`, deletes the
   selected source, then calls `Disturbed.validate` on the child file. Validation
   and downstream landuse/soils/WEPP work read the child context.

The retained [baseline](remaining_semantic_inventory.md#s01--high-same-name-omni-sbs-re-upload-skips-the-changed-scenario)
uses real upload/parser/direct orchestration: class 1 then same-name class 3
produces `executed`, then `skipped`, with only class 1 reaching the executor seam.
It is not a full WEPP run. The RQ omission is confirmed at its actual dispatcher
and worker call sites; a new RQ regression remains required.

`omni_sbs_copy_boundary_probe.py/.json/.log` adds **1 passing actual copy-branch
probe**. Only expensive landuse/soils and directory-lock boundaries are isolated.
The main-file hash survives copying; the limbo main is deleted and its `.tfw`
remains. Native GDAL reads the copied TIFF using an already-present destination
worldfile: source origin/cell size 500000/30 becomes destination 600000/10.
Thus source-sidecar identity is not equivalent to the data consumed by the
child. The copied child's ordinary/native dependencies are a separate boundary.

## Smallest compatible behavior to ratify

Keep existing scenario definitions, filenames, scenario names, child locations,
base-loss comparison, direct year rule, queue ordering and native computations.
Add a versioned SBS **main-byte receipt** to the existing private scenario
signature/provenance, using the current verified ordinary-file SHA-256 helper.
It binds the selected path and captured upload bytes to the known child copy.
Non-SBS signatures remain unchanged. The existing serialized `signature` worker
argument can carry the observation without adding a queue edge, task or service;
the checkpoint must specify its exact private encoding and legacy behavior.

Use one owned comparison path in direct and RQ dispatch. A present selected SBS
must be read successfully, regardless of an older accepted entry. Different
bytes at the same path miss reuse; equal bytes with only metadata changes retain
eligible reuse. Do not replace read denial/malformed receipt with an unavailable
sentinel that compares equal, or fall back to an older copied file when a newer
selected upload is present but unreadable. Preserve existing source symlink and
programmatic-path authority; do not import post-fire's stricter path rules.

Before cloning/execution, reobserve the selected input and compare it to the
captured direct/queued receipt. This rejects a stale queued request before the
existing destructive workspace reset. During the copy, bind bytes to the opened
source and verify the resulting copied main against that capture. A changed
source must not be blindly unlinked as though it were the consumed upload;
preserve a newer same-name upload and fail the attempt on observed drift.

After native work and before recording successful dependency metadata, verify
the retained child's main bytes against the same receipt. Also recheck current
scenario selection and any present upload at the selected path, so a replacement
arriving during execution cannot receive a success entry for older work. Repeat
the appropriate observed-version/selection guard at the existing locked metadata
update; do not attach an after-the-fact hash to whichever output exists. Apply
this in both direct passes and the RQ worker, including its optional-signature
fallback. A reuse decision also needs a matching post-observation before recording
`skipped`; no unverified observation should become a new strong receipt.

Failures keep the existing exception/status route and do not install a new
successful dependency entry. Preserve failed child diagnostics through the
existing project browse/archive lifecycle. The existing clone reset is not an
atomic output-generation publisher: this bounded correction must not claim
rollback of all prior child outputs after work has already started or introduce
a replacement orchestration/storage architecture to make that claim.

## Missing/consumed and legacy states require explicit handling

Normal success deletes the original selected main. A design that always hashes
`sbs_file_path` will therefore regress valid later skips. For new receipts,
recognize an intentionally consumed upload only through accepted provenance
bound to the same scenario/path and its expected copied-child location. Verify
the retained copy; do not invent a fresh source path from arbitrary receipt data.
An absent source without that accepted association retains the existing missing
source behavior when execution is required.

Legacy entries have no historical SBS hash. Preserve their existing missing-source
reuse behavior as **legacy, unverified content history**, rather than forcing a
previously skippable consumed-upload scenario to fail or silently assigning a
hash from today's child. A present newly supplied upload must establish the new
receipt through actual execution, even if old definition/loss metadata match.
After that successful execution, its copied-source association supports the new
consumed-source path. Malformed/unknown new receipts are not legacy. Document
rollback-reader cache misses and prove they do not falsely certify currentness.
This compatibility choice is a proposed checkpoint decision, not an approved
on-read migration or proof that old results consumed today's copied bytes.

Do not let that legacy rule resurrect a prior success after a new rerun resets
the child and then fails. RQ's skip test lacks the direct path's year/output
check. Once this scenario actually begins destructive clone replacement, its
old reusable association must no longer certify the new/partial workspace.
Invalidate only that association or prove an unchanged accepted child generation;
retain the existing audit/error evidence. Pre-clone queue-drift rejection should
leave the prior association intact. This failure case needs an explicit test,
not a blanket preservation of every old dependency-tree value.

The first bounded correction fixes **same-name uploaded main-content reuse**.
It does not prove scientific equality of inherited/changed destination masks,
PAM/world files, IMG companions, VRT references or other native inputs. Hashing
the limbo source's sidecars would be wrong for the demonstrated copy behavior.
Do not silently start copying/deleting sidecars, reject IMG, or claim universal
raster closure. A future effective-child dependency checkpoint must identify
what `Disturbed.validate` and its native readers actually consume. That remaining
scope must be explicit in closeout rather than hidden inside a main-file digest.

## Owners and acceptance evidence

The existing normative behavior is in
[Omni README, Dependency Tracking and scenario execution](../../../../wepppy/nodb/mods/omni/README.md#dependency-tracking).
Amend that contract and its source-consumption/legacy explanation before code.
Keep [upload endpoint rules](../../../schemas/upload-endpoint-contract.md),
[RQ response rules](../../../schemas/rq-response-contract.md), NoDb locking,
and [artifact observability](../../../standards/artifact-observability-standard.md).
UI payload/submit behavior is documented in
`docs/ui-docs/control-ui-styling/control-inventory.md` under Omni. Closed Omni
work packages are historical evidence, not living authority.

Required regressions: real same-name route upload→direct/RQ rerun; equal bytes
and metadata changes→reuse; consumed source/new proof and consumed legacy states;
denied present upload; copy mutation/new-upload preservation; enqueue-to-worker
and native-to-admission replacement; malformed proof; and unchanged non-SBS/mulch
ordering. Cover `test_omni_run_orchestration_service.py`, `test_omni_rq.py`,
`test_rq_engine_omni_routes.py` and the actual mode-build copy branch without
type-only signature stubs. Validate actual child SBS, management/soil inputs,
generated WEPP outputs and archive retention. Measure representative cold/settled
receipt checks plus copy overhead before ratifying a performance gate.

C07 remains separate. Its native probe deliberately keeps the completion receipt
fixed while changing stream pixels. Normal `build_channels` removes subwta and
`build_subcatchments` clears/stamps its receipt around successful work, so that
probe does not prove an ordinary-writer ordering defect. Preserve those receipts
and distinguish their supported orchestration role from unresolved arbitrary
source/restore/sidecar currentness; do not broaden S01 into a pruning rewrite.
