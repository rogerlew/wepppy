# Forest Compose Integration Evidence

**Host**: `forest` development (`wc.bearhive.duckdns.org`)
**Date**: 2026-08-21
**Result**: PASS

## Scope

Restarted only `weppcloud`, `rq-worker`, and `weppcloudr` from
`docker/docker-compose.dev.yml`. No volume, mount, Compose YAML, Kubernetes, or
other-host operation was performed.

## Mount Comparison

Normalized `docker inspect` mount snapshots for `weppcloudr` and
`wepppy-rq-worker` had identical before/after SHA-256:

`0d6ad8fcf13aa23488bf3a84fecb2236ea2496681b98e8f4a175c42cc4141829`

The worker retained `/wc1`, `/geodata`, the source repositories, secrets, and
`/var/run/docker.sock`. WEPPcloudR retained `/wc1`, `/geodata`, both R source
trees, and the renv cache volume. Compose YAML has no package diff.

## Render Result

- URL target:
  `https://wc.bearhive.duckdns.org/weppcloud/runs/branching-hubbub/disturbed9002_wbt/`
- Successful RQ job: `d77753a7-5505-4a1b-bce3-3008a30d29b7`
- Backend snapshot: `docker-exec`
- Run WD: `/wc1/runs/br/branching-hubbub`
- Enqueued: `2026-08-21 19:26:55.876633 UTC`
- Started: `2026-08-21 19:26:55.919196 UTC`
- Ended: `2026-08-21 19:27:11.601224 UTC`
- Artifact: `export/WEPPcloudR/deval_branching-hubbub.htm`
- Artifact size: `14,077,008` bytes
- Artifact SHA-256:
  `2234c3682b0a50c80d9c97920bba4524d67a04f0587d5b418e35bba08b89c1a1`
- Artifact mode: `0644`; content begins with an HTML doctype.
- Protected stdout/stderr modes: `0660`; sizes were 3,027 and 489 bytes.
- Monotonic Compose fencing generation after the successful retry: `2`.

An unauthenticated GET reached the expected CAP verification boundary with
HTTP 200. The authorized render itself was submitted through the normal RQ
task with the exact URL run/config and `skip_cache=true`; the finished RQ
result points to the artifact above.

## Dispositioned First Attempt

Job `f2a60ac9-221c-43e1-8497-525e880ccdf8` rendered successfully inside R but
the worker rejected the root-owned `0640` artifact as unreadable. Publication
was corrected to explicit `0644`, matching the report-serving requirement, and
the second no-cache render passed. The failed attempt preserved its bounded
protected logs and did not change mounts.

## One-Shot Request-v1 Execution

The strict `render-request-v1.R` entrypoint was also executed directly in the
authorized `weppcloudr` container with its working directory set to the same
canonical run WD and the existing generation-2 cached artifact. A valid,
digest-bound request returned a terminal-success receipt with:

- RQ job ID `oneshot-validation-20260821`;
- request SHA-256
  `2ac92c41cf4a254ec608b69534040d296459e23ed6f48f2fdc73fcb49b3bdb12`;
- the same artifact path, 14,077,008-byte size, and
  `2234c3682b0a50c80d9c97920bba4524d67a04f0587d5b418e35bba08b89c1a1`
  artifact digest; and
- fencing generation `2`.

Re-execution with a wrong trusted digest exited `2` with `request digest
mismatch`. A correctly digested request containing one extra field exited `2`
with `request fields do not match schema version 1`. The temporary trusted
request file was removed afterward; the cached report and run mounts were not
changed.
