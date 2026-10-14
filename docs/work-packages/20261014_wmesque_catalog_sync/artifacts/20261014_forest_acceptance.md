# Forest acceptance — M1–M5

Date: 2026-10-14 UTC. Contract checkpoint: `193df8b8c`.
Scope: forest implementation and isolated acceptance; no wepp.cloud or Kubernetes
deployment. Default routing remains wepp.cloud and recurring sync remains disabled.

## Execution environment

Canonical commands use the installed forest `wctl` and development Compose file.
Server and real batch worker run as UID 1000, GID/group 993, umask 0022. Existing
`/geodata` is 1000:993 mode 755; the worker-created fixture catalog is 1000:993
mode 600 and readable by the same server identity. Fixtures live on the existing
shared NFSv4.2 `/wc1` mount, not a new service volume. No production dataset was published.

Read-only forest1 parity check used its installed `wctl`: batch identity is also
1000:993, umask 0022, with `/geodata` 1000:993 mode 755. Both existing images have
rsync but lack the SSH executable. Both Dockerfiles now include `openssh-client`;
the missing executable is direct evidence for this bounded transport dependency.
No daemon, credential mount, queue, privilege change, or Python dependency is added.
Forest1 is not restarted or activated by this work. Its live SSH export, network,
and writer-path acceptance remain rollout gates, as do Kubernetes NFS semantics.
Forest development UID 1000 currently lacks a passwd entry; forest1 resolves it
as `roger`. Thus local forest fixture acceptance does not claim SSH identity/home
readiness. No runtime identity workaround is introduced.

## Behavioral evidence

Run scripts with `wctl exec -T weppcloud python` and the repository path under
`/workdir/wepppy/docs/work-packages/20261014_wmesque_catalog_sync/artifacts/`.
The scripts fail on unmet acceptance conditions; they do not skip remote errors.

| Evidence | Result |
| --- | --- |
| `forest_acceptance.py` | Actual scheduler `--once` enqueues on `batch`; adoption, stale revision fallback, corrupt-copy failure/recovery, concurrent retrieval and stopped-local fallback |
| `interruption_acceptance.py` | Killed copy after 2,031,616 of 268,484,850 bytes; catalog retained old revision; OS lock released and retry succeeded |
| `project_acceptance.py` | Isolated canonical project fork; real DEM, landuse, SSURGO, PRISM acquisitions; fresh model inputs and hillslope execution |
| `downstream_acceptance.py` | Rebuilds actual soil summaries/files and PRISM spatial climate before repeating model preparation/execution |
| `mod_projected_acceptance.py` | Projected EPSG:32611 request matches NLCD pixels; tree-canopy raster 195×199, range 0–89 |
| `output_readback.py` | Production native interchange and report dataframe reader validate fresh loss and daily-water outputs |

Initial scheduled jobs were `700fe961-02f6-49ac-8a23-6ffda505b53c` (finished),
`3e800c2f-6820-44b1-bd8b-3f5d115f7387` (intentional failure), and
`61545622-b57b-4b7f-b996-5469d9da0e26` (recovery finished). Live inspection confirmed
`origin=batch`, `func_name=wepppy.rq.wmesque_rq.sync_wmesque_rq`, no dependencies.
Retained JSON artifacts identify the final run's jobs, revisions, and readbacks.
These were one-shot scheduler invocations; no recurring fixture task remains.

Project root: `/wc1/runs/wm/wmesque-acceptance-1792010682`. Source
`/wc1/runs/an/anisotropic-sassafras` was never changed. The source selected a retired
WEPP executable; only the acceptance clone selected installed `wepp_261010`.
Model evidence uses hillslope 67 over 100 years. Optional `InterceptionStorage`
values are absent in the native output; required water-balance fields are checked
for finite values, positive area and nonnegative precipitation/runoff. This is
an artifact/readability check, not scientific calibration evidence.

## Validation commands

```sh
wctl run-pytest tests/services/test_wmesque_catalog.py tests/services/test_wmesque_priority.py tests/services/test_wmesque_retrieve.py tests/tools/test_scheduler_runtime.py tests/tools/test_scheduler_env_ints.py
wctl run-pytest tests/nodb/test_climate_edde_build.py tests/nodb/test_climate_build_helpers.py
wctl run-stubtest wepppy.all_your_base.geo.webclients.wmesque
wctl run-stubtest wepppy.webservices.wmesque2
wctl check-test-stubs
wctl check-rq-graph
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
wctl run-pytest tests --maxfail=1
```

Focused service/scheduler result: **72 passed, 1 skipped** (the preexisting opt-in
network smoke). EDDE/helper regression: **59 passed**. Both stubtest modules,
stub completeness, RQ graph, and changed exception checks pass. The real acceptance
scripts supply network/artifact evidence independently of the skipped legacy smoke.
Broad suite and fresh image validation results will be recorded before handoff.

Fresh image validation: canonical `wctl build weppcloud` succeeded, image
`sha256:f03d9c55f49229bd1dfb9f720c420ef2568de7919b132ddd7c735a71f4652bcf`.
A one-shot `rq-worker-batch` passed its real native interchange startup preflight
and **67 focused tests**, with no skips. The idle batch worker was recreated using
`wctl up -d --no-deps rq-worker-batch`; the scheduled acceptance was repeated
successfully against that worker. Final job details live in `forest-rq-evidence.json`.
`wctl restart wmesque2` loaded the final server code, followed by actual local NLCD
readback: 195×199 pixels, range 21–90. The old image remains tagged
`wepppy-dev:wmesque-before-m5`; no image or service on forest1/wepp.cloud was changed.

The new package installation added openssh-client plus libcbor/libfido2; it adds
no daemon or Python dependency. A real UID-1000 SSH invocation reports
`No user exists for uid 1000`, confirming the documented development identity
prerequisite. No remote-SSH success is inferred from local fixture or unit tests.

Code-quality observability ran, but local radon was unavailable and the report
did not produce changed-file metrics. It is observe-only, not correctness evidence.

## Rollout limits

Master SSH credentials, host trust, authorized export, capacity, and receiving
writer access are not fabricated by forest fixture success. Validate them using
the actual task before M6/M7 activation. New images supply the SSH client, not
credentials. The initial publisher validates contained GeoTIFF/VRT closure and
standard TIFF sidecars; validate any additional source family before publishing.
Current NED mosaics reference mutable `/vsicurl/` sources, which must be
materialized before assigning managed revisions. Legacy retrieval still works.

No automatic project-wide pinning, deletion/retention, upstream publication, or
ownership database is introduced. Existing unversioned servers remain usable;
only managed releases can satisfy an explicit revision requirement.
