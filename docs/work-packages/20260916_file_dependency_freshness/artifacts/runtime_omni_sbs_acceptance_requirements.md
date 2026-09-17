# S01 actual native acceptance preparation

Status: **direct native acceptance passed after the coordinated development
restart**; see `runtime_omni_sbs_correctness_acceptance.md` for final evidence.
This is a direct-owner native acceptance gate, separate from live
HTTP/RQ, browser and global climate/postfire acceptance.

## Prepared workflow

`runtime_project_copy.py` copies the complete ordinary-file Grizzly project from
`/wc1/runs/th/thespian-cleanness` into a new disposable identity. Each source is
hashed during the independent copy; no hardlinks or source controller hydration
are used. Unexpected symlinks, preexisting Omni children and existing destinations
reject explicitly. Root NoDb metadata receives the canonical fork-style path and
runid rewrite plus the disposable batch/interactive identity. Only the copied
query catalog root is rebased. All scientific settings, primary config/manifest,
climate years and baseline WEPP artifacts remain present. Failed copies remain
with a failure manifest. This fixture utility does not replace the canonical
user-facing fork workflow.

Preparation command already started under the existing service container:

```sh
wctl run-python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_omni_sbs_acceptance.py --prepare-only --root /wc1/batch/qa-omni-native-20260917-a61f3e
```

`runtime_omni_sbs_prepare_initial.log` retains the actual command and outcome.
The preparation branch does not import NoDb/GDAL owners or execute native models.
Actual preparation completed in76.73seconds under UID1000/GID993:3916 files,
6,375,730,842 logical bytes. Every copied inode is independent and source versions
remained unchanged. `runtime_omni_sbs_prepare_readback.json` verifies all10 root
controllers, the copied catalog, primary-config hash, original SBS hash and218
baseline management files. The larger logical byte total includes sparse data;
the named project's allocated size was approximately2.60GB.

Before any copied owner hydration, review identified that ordinary `RedisPrep`
uses the leaf basename as its Redis namespace. The initial generic `runs/grizzly`
leaf therefore required a preparation correction. The authorized bounded rename
and root JSON rebase established
`/wc1/batch/qa-omni-native-20260917-a61f3e/runs/qa-omni-native-20260917-a61f3e-grizzly`.
The original manifests and preparation readback remain; the correction is retained
in `runtime_omni_sbs_identity_correction.json` and the disposable root's
`copy-identity-correction.json`. No native work or owner hydration preceded this
correction. The source and copy must have no `.redisprep-run-id` override. After
restart, the native script uses the existing destination-only canonical fork
marker reset before model work, preserving baseline completed-task timestamps.
The SBS filename also includes the unique root name, isolating the child leaf.

After a successful preparation and the root agent's restart signal, run:

```sh
wctl run-python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_omni_sbs_acceptance.py --copy-manifest /wc1/batch/qa-omni-native-20260917-a61f3e/copy-manifest.json --ncpu 4
```

The CLI refuses to overwrite a prior native attempt. A failure requires retaining
its manifest and working files, then explicitly preparing another independent
copy for any rerun. The existing `WEPPPY_NCPU` limit bounds the WEPP execution
paths that honor it; it is not a promise that every native/library worker uses
that cap. No shared configuration changes are made.

## Assertions and evidence

The full copied project has217 hillslopes and46 climate years in the inspected
baseline. The checked `p*` generated-file set has218 entries, including the
watershed `pw0` file; the manifest's historical `hillslopes` count field includes
that watershed entry. The script derives two explicitly synthetic low/high class controls
on the real599196-byte Grizzly SBS footprint, projection and nodata mask. It uses
the canonical SBS export palette. These are labeled controls, not claims about
the historical fire's actual class distribution. The original raster's hash and
both supplied controls are retained. The second upload uses the same pathname
and restores the first upload's mtime.

Both runs call ordinary `Omni.parse_scenarios` and `run_omni_scenarios`: real
Disturbed validation, existing landuse/soil acquisition/builds, management
preparation, hillslope and watershed WEPP binaries, interchange and summaries.
There are no injected native, queue or scientific seams. Required network/data
services use the existing project workflow; an unavailable service is a retained
failure, not a reason to substitute a mock or shorten the climate.

The script verifies the admitted source receipt and consumed upload, native
child raster classes, complete generated `.man`/`.sol`/`.run` hillslope sets,
nonempty readable watershed/hillslope Parquet outputs and the complete year set.
Low/high replacement must change actual management and soil bytes. After each
execution, the consumed-source invocation must skip and preserve the hashes and
physical versions of numerical artifacts. This tests ordinary direct admission,
not a surrogate helper call.

Every regular child file is independently copied into a retained generation
folder before the next normal child reset. Shared links are recorded as paths
within the disposable parent, without following or recreating them in the
evidence folder. Source hashes, generated artifact hashes, owner UID/GID/groups,
umask, selected binary identities, production module hashes, elapsed durations,
accepted NoDb metadata and failure tracebacks are retained in the disposable
root. The complete named source is independently rehashed after success; failures
still perform a source-version check. No cleanup runs on failure.

The script's two native generations and consumed-source skips passed, with
retained manifests and source verification. The subsequent actual RQ extension
also passed, as recorded in the final acceptance artifact. Live UI remains a
separate root-owned gate. Durations are observations, not a replacement
for the separately ratified S01 component budgets.

## Shared copy API

Other acceptance scripts can import `runtime_project_copy.prepare_project_copy`
with `(source, destination, manifest_path=None)` and use the returned source
manifest with `verify_source(manifest, hash_bytes=True)` afterward. Supported new
destinations are `/wc1/batch/qa-NAME/runs/qa-NAME-SUFFIX` and
`/wc1/runs/qa/qa-*`. Source identity markers reject before copying; destination
markers reject before hydration. A prepared generic batch leaf can be corrected
with `relocate_prepared_copy` before owner hydration, preserving prior manifests.
The copied
project must remain distinct for each concurrently mutating acceptance workflow.
