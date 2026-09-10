# Independent correctness review

Reviewer: `deval_identity_review`, September 10, 2026 UTC.

## Disposition

No unresolved major code findings in the final scoped change. The Docker-exec
identity correction conforms to the existing worker/run-data authority boundary.
Production boundary acceptance passed: complete uncached renders cover legacy
owner-only input on both worker hosts, regenerated soils, absent export, existing
output replacement through RQ, and authenticated Flask route readback. Broad
validation and final source publication remain package closure gates.

## Findings and disposition

1. **P1, existing identity defect: addressed.**
   `wepppy/rq/weppcloudr_backends.py`, `DockerExecBackend.render`, now selects
   the executing worker's effective numeric UID/GID. A worker-owned mode-0600
   file is therefore readable without changing its contents or mode. The IDs
   come from trusted process state, not request data. Existing argv/stdin
   transport, timeout, child error translation, logs, fencing, and artifact
   validation are unchanged. No root override or additional capability is added.
2. **P1, previous validation gap: addressed.**
   `docker/validate-weppcloudr-runtime-contract.sh` now creates real parquet as
   the worker image identity under umask 0077, reads it with R/Arrow as the same
   identity, writes output, and checks worker readback and unchanged input mode.
   The disposable mount is distinct from production run data. This establishes
   the owner-access mechanism, while the fresh complete report evidence covers
   the actual RQ process, run mounts, publication, and report readback.
3. **P2, direct Plumber endpoint: explicitly outside scope.**
   `weppcloudR/README.md`, One-shot renderer, records that the canonical report
   page uses RQ and that the legacy direct endpoint retains its container
   identity. The user explicitly rejected additional deployment modes and
   migration work. No Compose identity or legacy-output ownership migration is
   required for this scoped change, and no claim of repairing that separate
   ingress should be made.

## Coverage and residual risk

- New backend tests verify complete command construction for worker identities
  1002:130 and 1000:993, request data, fencing generation, and timeout. The RQ
  orchestration expectation also checks the selected execution identity.
- Reviewer ran `bash -n docker/validate-weppcloudr-runtime-contract.sh`: passed.
  Reviewer inspected `/tmp/deval-identity-focused.log`: 52 passed, 10 warnings,
  9.11 seconds. The reviewer did not independently repeat that run.
- The deployment probe obtains the worker image's default identity and uses a
  local temporary bind mount. It does not independently prove a Compose user
  override, NFS behavior, supplementary-group access, cold library/cache writes,
  or complete R Markdown rendering. The separately inspected production canaries
  close that gap for the deployed identities and mounts; future identity or
  mount changes still require the complete workflow check.
- Missing or malformed model inputs remain application failures. This change
  neither adds fallback behavior nor relaxes path, authentication, locking, or
  publication checks. Kubernetes execution is unchanged.
- Complete the package/tracker outcomes, broad validation, and final source
  publication before closure. Default/batch worker container layers were patched
  without restarts on both shared-queue hosts. Future container recreation must
  use the canonical deployment, which builds from the corrected source; this
  review does not claim older image artifacts contain the fix.

## Production evidence inspected

- `/tmp/deval-live-runtime-probe.log`: the actual image probe passed as
  1002:130 against renderer image
  `sha256:925dd175ef04ae944b141f07a3c7e677ae3690e0b28630d908ef6393d757fbc4`.
- `/tmp/deval-identity-canary.py` and `/tmp/deval-identity-canary.log`: actual RQ
  orchestration with `skip_cache=True`, effective worker 1002:130, valid soils
  mode 0600, unchanged input SHA-256/mode, and 13,494,027-byte output.
- `/tmp/deval-regenerated-canary.log`: deployed soils writer preserved DataFrame
  values, published mode 0644, and a fresh render created absent export output
  of 13,494,033 bytes. Copy-related NoDb working-directory warnings are recorded;
  the parity assertions and complete render succeeded.
- `/tmp/deval-queued-canary.log` records actual queued job
  `deb10627-1fbd-48d7-87e3-55fcc3ab1283` with input mode 0600. The operator's RQ
  inspection, recorded in the tracker, confirms completion at
  2026-09-10 04:22:21 UTC. The operator observed output mtime changing from
  1789014055394599000 to 1789014141541404000 nanoseconds.
- `/tmp/deval-route-readback.py` and `/tmp/deval-route-readback.log`: authenticated
  deployed Flask test-client GET returned 200 and all 13,494,023 bytes matched
  the published artifact SHA-256
  `a2e5361a5ae3c42ffe0796453e42b1a3633f0d7c5a6ebc8e5c61f5dd17aa75f5`.
  This verifies application-route serving, not a browser/Gunicorn round trip.
- `/tmp/deval-wepp2-canary.log`: the installed backend on the other shared-queue
  host completed a fresh render as 1002:130, retained input mode 0600 and
  SHA-256, and published 13,494,036 bytes.
