# M0 operations checkpoint review

Date: 2026-11-16  
Reviewer: independent `ops_security_control_agent` (`ops_checkpoint`)  
Source: task worktree at `05e3450fa7d3b24572e65161100670ae542a6ea8`, with uncommitted M0 documents.  
Verdict: approve isolated evidence collection; hold numeric-envelope acceptance and implementation until the complete M0 checkpoint passes its other gates.

## Evidence inspected

Read root/Docker/wctl guidance, the active plan, dependency draft, canonical
integration/history standard, ADR-0142, dev Compose, `tools/wctl2/context.py`,
`checkout_identity.py`, `commands/python_tasks.py`, and the predecessor final-4
qualification and five-lane review. Read the canonical deploy script's parser
release preflight, fail-closed stop, readiness, and recovery paths. No runtime
source, installed wrapper, shared service, image, or production state changed.

Read-only Docker observations on 2026-11-16:

| Object | Observed identity and relevant state |
| --- | --- |
| Running `weppcloud` | Image `sha256:659eb59a98ce2e69a74cd36538b9e392c8e33d66de3c8ee5303e02bd243d01a0`; UID/GID `1000:993`; `/home/workdir/wepppy` mounted at `/workdir/wepppy` |
| Running `wepppy-shape-converter` | Image `sha256:c1f1e84d6beec7562fc184ab9b5ed48398bb955d938aa139768fcea7da777361`; UID/GID `10001:10001`; read-only root; 1 GiB memory; 256 PIDs; 1.5 CPUs |
| Available reviewed predecessor `shape-converter:final4` | Image `sha256:b9e78b16718911ff16dc213b27d719477d95880ebcdca500cc858cea13c05ae8`; UID/GID `10001:10001` |

The running converter is neither the accepted final-4 image nor the current
1.5 GiB reviewed envelope. It must not be used as evidence of either. This is a
local observation, not authorization to change the running stack or a claim
about production.

## Checkout selection is resolved for docs

Executed from the task worktree:

```sh
wctl --project-dir /tmp/wepppy-vector-upload-normalization \
  doc-lint --path docs/schemas/vector-upload-normalization-contract.md
```

Result: `1 files validated, 0 errors, 0 warnings`, exit 0. The explicit project
selection changes the host subprocess working directory. No wrapper change is
needed. An absolute `--path` is unnecessary.

Pytest is different: `--project-dir` selects the expected source, but does not
remount an existing container. `checked_test_command` requires a fresh nonce
created in that selected worktree to be visible at container `/workdir/wepppy`.
The running shared `weppcloud` cannot satisfy that candidate identity. Never
remove the nonce check, copy the nonce to the shared checkout, or count a shared
stack run as candidate validation.

## Runnable isolated test-container design

Use the existing dev image by full immutable image ID in a disposable Compose
project; this is a local test harness, not new production topology. The retained
`20261116_candidate_test.compose.yml` uses a read-only candidate-source mount,
no host Docker socket, no secrets, no real run/geodata mounts, no published
ports, and no external network. It preserves the observed dev service UID/GID.
Its only long-lived process is `sleep`; tests write to `/tmp`.

Run through wctl with the harness file as the sole Compose file. Do not merge it
with the full dev Compose file: fixed container names, dependencies and host
mounts in the latter could touch the shared stack. Clear inherited extra-file
selectors when invoking. The harness has its own explicit project name.

```sh
set -euo pipefail
candidate=/tmp/wepppy-vector-upload-normalization
harness=docs/work-packages/20261116_vector_upload_normalization/artifacts/20261116_candidate_test.compose.yml
unset WCTL_COMPOSE_FILE_EXTRAS WCTL_COMPOSE_FILES
wctl --project-dir "$candidate" -f "$harness" docker compose config --quiet
wctl --project-dir "$candidate" -f "$harness" docker compose up -d --no-build weppcloud
trap 'wctl --project-dir "$candidate" -f "$harness" docker compose down' EXIT
wctl --project-dir "$candidate" -f "$harness" run-pytest \
  tests/shape_converter -o cache_dir=/tmp/pytest-cache
```

The `config --quiet` command passed, exit 0, against this exact harness. Container
creation and pytest commands are a prepared design, not executed acceptance
evidence. Run `docker inspect` on the
harness container and retain image, mount, UID/GID and cgroup evidence before
counting results. `wctl run-pytest` then supplies the live-checkout nonce. The
read-only source can expose tests that write next to fixtures; repair test
scratch ownership or document the affected gate rather than making shared data
writable. Use `/tmp` for isolated Redis/socket fixtures when needed. Runtime
package resolution must be checked inside the harness before interpreting import
failures; do not add production dependencies to make a test harness pass.

This harness can validate source tests. It cannot by itself establish browser,
authentication, CSRF, queue, mounted-run identity or real downstream workflow
acceptance. M3-M5 require bounded disposable project fixtures under the intended
service identities and actual receiving boundaries. Keep their receipts
separate from unit/API-test results.

## Exact candidate image qualification

Build the existing shape-converter Dockerfile from the committed task revision,
with both parser provenance pairs bound to that revision and locked graphs.
Retain the resulting image ID. No source bind mounts are permitted in the
exact-image acceptance container: a bind mount would replace the built Python
payload. Use the predecessor envelope: UID/GID 10001, read-only root, all
capabilities dropped, no-new-privileges, 256 PIDs, 1.5 GiB memory, 1.5 CPUs,
384 MiB `/tmp` tmpfs and 8 MiB `/run/shape-converter` tmpfs. The no-network probe
must use the built image's actual binaries and local API loopback. Container
CLI probes do not replace real HTTP tests on a separately isolated internal
network for the receiving workflows.

Measure cgroup `memory.current`, `memory.peak`, `memory.events`, CPU usage,
process/descriptor counts, scratch bytes, output bytes and cleanup. Record
before/after measurements for ordinary geometry, near-limit valid data, malformed
headers, dictionary expansion, timeout, repeated cancellation and saturation.
Successful readiness must execute both real parsers, verify both provenance
pairs and reconcile semantic artifacts. Binary existence alone is insufficient.
Run pinned Syft/Grype against the new exact image; the predecessor scan cannot
clear changed crates or binaries.

## Resource review

Proposed new ceilings are footer 1 MiB, page header 64 KiB, compressed and decoded
page 8 MiB each, aggregate decoded data 128 MiB, 64 columns, 128 row groups,
100,000 rows, and WKB 4 MiB. Inherit the parser 384 MiB address-space limit,
60-second CPU/90-second wall limit, 32 descriptors, 16 MiB IPC, 32 MiB output,
320 MiB scratch, and global/per-client single-flight controls.

These are plausible probe targets, not independently measured safe maxima.
The 128 MiB decoded counter must cover every column and dictionary across the
whole request; resetting it per row group/page defeats the aggregate invariant.
Page headers and encoded dictionary cardinalities must be checked before
allocation. Counts are separate budgets from encoded bytes. A 64-column reader
can retain dictionaries and decoding buffers concurrently, so multiplying a
per-page ceiling by column count is not an acceptable memory argument.

At one instant the API can hold upload bytes, tmpfs files, parser address space,
IPC byte/text/object copies, geometry objects and serialized output. The inherited
single-flight limit must cover both formats and both inspect/convert endpoints,
not one slot per parser. The existing 16 MiB IPC and 32 MiB output ceilings also
mean an accepted 100 MiB Omni upload is not guaranteed to normalize successfully;
the contract must state the resource failure without silently lowering Omni's
upload admission cap. The resource ADR must distinguish byte admission from
supported decoded/output workload.

## Findings and disposition required

| ID | Severity | Finding | Closure evidence |
| --- | --- | --- | --- |
| OPS-M0-01 | High | Candidate exact-image and aggregate-memory evidence does not exist yet. Independent ceilings do not prove overlap safety. | M2 exact-image measurements under reviewed envelope, all failure/cancellation outcomes drained, no cgroup OOM, readiness recovery |
| OPS-M0-02 | Medium | Shared running converter differs from final-4 acceptance identity and envelope. | Use isolated exact candidate, retain immutable identity; do not infer predecessor qualification from running shared service |
| OPS-M0-03 | Medium | Python candidate test identity cannot be established on the shared mount. | Disposable harness source mount plus wctl nonce, actual image/mount readback; no tests reported before identity proof |
| OPS-M0-04 | Medium | Resource budget must be aggregate across pages, columns, row groups and formats. | ADR/contract explicit accounting and implementation probes; shared admission rather than independent parser queues |

OPS-M0-02/03 are resolved design constraints, not external blockers. No registry,
publication, production-host or deployment access is needed to continue local
implementation after M0 approval. Dependency adoption/resource ratification and
missing empirical acceptance remain gates, not permission to relax controls.
The root agent subsequently reported an external account-security eligibility
gate terminating the dedicated dependency/security reviewer. This operations
review does not substitute for that required independent review or authorize a
retry around the gate. M0 cannot pass until the required review is available and
accepts the complete checkpoint.

## Rollout and recovery boundary

Production deployment and image publication remain excluded. Prepare the
canonical `scripts/deploy-production.sh` release preflight to require both parser
provenance/readiness checks and preserve its secure-or-stop behavior and exit-88
recovery contract. Do not run deployment from this package. Recovery disables
new binary admission and restores previously accepted GeoJSON workflow behavior
without migrating/deleting saved projects. Never roll back to a permissive parser
fallback. Keep the previous image by immutable ID and require post-recovery
GeoJSON artifact readback, service identity, unrelated-service health and parser
scratch/process cleanup in a separately authorized rollout receipt.
