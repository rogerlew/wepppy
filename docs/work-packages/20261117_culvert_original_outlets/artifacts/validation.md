# Validation: original culvert outlets

Observed 2026-11-17 08:27 UTC on forest, isolated worktree fix/culvert-original-outlets.
Contract ancestor: 066b04755995404a4d54dbd25d6141f68a837a2a. Validation consumed the dirty implementation in this worktree, not shared master.

## Incident replay

Copied input only from wepp1 batch ab283192-441e-41a1-baad-6c2df0c36d31.
Payload SHA-256: c0a466520041a5aded8461d69d34f0fcd26f9fe94cd9477fb13fd6c9d1a56431.
Native WBT binary /workdir/weppcloud-wbt/WBT/whitebox_tools SHA-256:
28208e075a51f37d254a51b2a9f27c0ef7e5f273344c8665a0749b4714766777.
WBT repository revision: df62f57c10f3d33010a41c785ea85a000f6b12fc; reported version 2.4.0.

Run the retained scripts from this checkout with the project dependencies and native WBT:

```sh
python docs/work-packages/20261117_culvert_original_outlets/artifacts/replay_selection.py PAYLOAD_ZIP DISPOSABLE_ROOT incident_replay.json
python docs/work-packages/20261117_culvert_original_outlets/artifacts/replay_topology.py DISPOSABLE_ROOT incident_topology.json
```

Do not point the scripts at a retained production batch. The scripts write disposable rasters.
[Selection readback](incident_replay.json): 33/33 resolved and selected, 31 at one pass and two at zero. All seven formerly rejected points retain one pass. Supplied road points are unchanged.
[Topology readback](incident_topology.json): all seven generated native TOPAZ subcatchments and channels. The replay performs actual outlet object parsing, cropped-coordinate translation, existing mask inclusion, junction generation, watershed generation, Strahler order, and HillslopesTopaz. It checks outlet membership in the consumed netw0 raster. Point1751 resolves one cell downstream of its polygon: cropped row/column [26,8], outlet pixel coordinates [8,26], one generated channel. This does not claim full model/soil/climate execution.

## Automated validation

Canonical wctl run-pytest rejected this worktree because the shared container mounts /home/workdir/wepppy. No shared stack was restarted or remounted. Used /home/workdir/wepppy/.venv/bin/python against this worktree with PYTHONPATH set to the actual checkout. The local virtualenv lacks the runtime python_multipart import package; copied that package from the running dev image into disposable /tmp/culvert-test-deps. A disposable Redis server on localhost:16389 supported local NoDb tests, with persistence disabled; no shared Redis was used.

Focused command: python -m pytest tests/culverts tests/rq/test_culvert_rq_helpers.py tests/microservices/test_rq_engine_culverts.py -q --maxfail=1 (REDIS_PORT=16389; PYTHONPATH=checkout:/tmp/culvert-test-deps). Final result: 113 passed, 1 skipped (16.17 seconds). A final RQ-only follow-up after preserving the existing find_outlet progress timestamp passed 13 tests (9.09 seconds).
Coverage includes real WBT off-stream resolution, pruning fallback, crop propagation, altered outlet/input identities, downgrade/orphan rejection, failed no-outlet preparation, old policy, native archive/restore, admission injection, and parent preparation ordering.

Broad command: python -m pytest tests --maxfail=1 -q. Blocked during collection by pre-existing environment configuration: tests/weppcloud/routes/test_rq_info_details.py imports Flask requiring SECRET_KEY. Result: 2 skipped, 1 collection error; no full-suite success claimed.

Scoped wctl doc-lint with explicit --project-dir passed for canonical spec, API spec, developer guide, ADR and package docs. ADR date gate: 146 valid. Broad-exception changed-file gate passed with zero increase; an existing diagnostic boundary received an inline rationale after line-number drift. git diff --check passed.

## Independent correctness review

contract_review_one approved after requiring guards against missing policy and removed selection basis, plus direct downstream evidence for1751. Both fixes/evidence are retained. Two independent pre-implementation contract reviews approved ancestor066b04755 after reconciling legacy seeding descriptions. No remaining blocking review findings. Production deployment and full WEPP acceptance remain separate.
