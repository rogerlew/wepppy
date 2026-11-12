# CI producer integration boundary

Status: independently reviewed design; integration and actual CI acceptance open.

Extend the existing isolated `test-baseline` job in
`.github/forest_workflows/stubtest.yml`, then regenerate workflows. Preserve
`forest_bootstrap: false`, `remote-ci`, `contents: read`, and checkout without
persisted credentials. Add production Dockerfile/requirements and security
tool/configuration paths to triggers. The current pinned test base cannot prove
that a requirements change works in its resulting common image.

Build from a clean checkout before generated controller assets modify it.
Bind the clean source, lock, build inputs and resulting immutable image ID in
the build receipt. Derive the test image from that ID, verify inherited layers,
runtime sentinel versions and the running container's image. Keep all required
full test commands; do not substitute a selected suite.

`wctl run-npm` executes on its caller's host even with `--compose-file`.
An exact-runtime frontend claim therefore requires invoking the canonical CLI
inside the isolated test container, with its CLI dependencies qualified, or
explicitly recording a separate pinned Node runtime for the exact source/lock.
This does not waive the required `wctl run-npm lint` and `wctl run-npm test`.

The collector requires qualified scanner binaries, the immutable carrier image,
approved scientific manifest, CA bundle and sufficient scratch space. Missing
inputs fail explicitly. Do not satisfy them with production mounts, private
store credentials or registry-write access. Keep DB/npm refresh network access
separate from offline image scans.

Write evidence to a unique private `RUNNER_TEMP` directory for the run/attempt.
After collection, expose only its private path, source/image/manifest identities
and a bounded retrieval deadline. Provide the selected manual SSH/SCP retrieval
window before `always()` cleanup. The operator imports into the protected store
and independently retains destination readback. An optional runner acknowledgment
can release cleanup but cannot establish acceptance: candidate code can forge it.

Timeout, cancellation or absent external import evidence leaves M3 incomplete.
Cleanup removes only the job's owned containers, images and scratch; no raw
Actions artifact or new transfer service is introduced. Acceptance needs an
actual CI-produced bundle imported before cleanup, plus timeout/failure checks
and workflow generation parity. The synthetic runner-02 transfer proves access
only. The deployment resume decision is separate and remains pending.
