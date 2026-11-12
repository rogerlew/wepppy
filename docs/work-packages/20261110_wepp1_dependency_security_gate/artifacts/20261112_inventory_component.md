# Exact-image inventory component qualification

This records exploratory component evidence, not accepted inventory, M1/M4,
or deployment acceptance. Subsequent security review reproduced a High trust
failure: candidate Python startup can forge inventory JSON before the mounted
probe executes. Isolation and matching output do not prove verifier execution.
The candidate-side method below is superseded. The replacement streams a
never-started container's exported filesystem under trusted host Python, without
extracting, importing, or executing candidate files; real qualification is pending.

The final confined historical-candidate trial verifies 308 installed Python
versions, 432 Debian versions, all 15,574 approved scientific file paths/hashes,
and 3,415 native executable paths exactly equal to the qualified Syft report.
All 1,316 available native SBOM hashes agree. The remaining 2,099 native
ownership/advisory-coverage gaps still require dispositions; inventory equality
does not clear them. The copied static-build lock hash matches the established
lock, but only a trusted clean-build receipt can bind the actual builder input.

The probe fails on changed/extra/missing scientific entries, symlink parents,
nonregular paths, binary/archive content, and filesystem traversal errors.
Independent review reproduced a hidden-file bypass because Python's default
glob omitted dot names while Syft matched them. Explicit hidden matching fixes
it; hidden ZIP and directory regression tests pass. The component suite passes
13 tests; combined collector/inventory tests pass 24. Collector integration is
still under independent review and has not completed its real-image trial.

The first strict traversal failed at owner-private `/home/roger` with all
capabilities dropped. Operations review rejected `DAC_READ_SEARCH` because it
also enables `open_by_handle_at` through Docker's default seccomp policy.
The bounded inventory-only alternative adds `DAC_OVERRIDE`, retaining read-only
root/public input mounts, no network, no Docker socket, isolated namespaces,
no-new-privileges, and resource limits. No production privilege changes occur.
There are no user-added writable data mounts; Docker's normal runtime mounts
still exist. Scanner, refresh, and npm phases do not receive this capability.

Final runtime readback confirms CapEff=2, NoNewPrivs=1, Seccomp=2, and read-only
root/input files. The exact image declares no volumes. The named disposable
container was removed after completion. Private records under
`evidence/crypto-batch-20261111/`:

- `inventory-probe-f6-inventory-ec9eb155263c.json`, SHA-256
  `d42b4d2a38e839ea05a6d81f766f0fcf98793acd99b6ec6ad41e49c03f3039a0`.
- Adjacent `.receipt.json`, SHA-256
  `76b3b45c3e69b4877615de0ec9f2803d8aa8895d03b42d62f4ed02ecd21357fa`.
- `f6-inventory-ec9eb155263c-inspect.json`: selective live mount/config readback.
- `inventory-ec9eb155263c-reconciliation.json`: full path/hash reconciliation.

Earlier exploratory output used one reused filename across successful and
failing trials; it is superseded and must not serve as final receipt evidence.
The final uniquely named output, source copies, command receipt and reconciliation
are retained privately. Future trials must use new exclusive output paths.

## Replacement: trusted filesystem archive reader

`tools/security/archive_inventory.py` now reads a Docker-exported merged
filesystem without extracting or executing it. The collector creates but never
starts the exact candidate container, verifies its image/never-started state,
exports it and removes only that container. The retained parser snapshot runs
under trusted host Python with `-I -S -B`, a 2 GiB address-space bound and 600 CPU
seconds. No additional container capability is needed.

The replacement rejects unsafe/duplicate/conflicting paths, unresolved/cyclic
hardlinks, linked metadata roots, malformed/duplicate package identity headers,
and partial Debian package states. Held installed Debian packages are included.
Regular legacy `.egg-info` files are parsed. Actual uv-cache metadata uses
hardlinks; qualified aliases preserve every path and inherit identity only from
an already validated regular metadata target. Symlink metadata remains rejected.
The final independent archive suite passes 32 tests; reviewed probe SHA-256:
`178358935dcc84cf4d24259b5684b85d0974faf9de57c7f30645cc7410376726`.

A retained-export trial for the clean parser image reports 702 Python metadata
locations (including installed, cache and vendored copies), 432 installed Debian
packages, 3,421 native paths and all 15,574 approved scientific files. Full fresh
SBOM reconciliation is pending. The collector retains its exact parser source,
commands and hashes; the evaluator now requires build/scientific/probe evidence
rather than relying on Syft's output descriptor for excluded-file scope.

The qualified scanner carrier declares `/data`; the collector validates that
exact metadata and overrides it with a read-only/noexec tmpfs. Candidate and npm
images must declare no volumes. Scanner execution remains unprivileged and
confined, with no Docker socket or runtime mounts. Independent security review
approved this bounded override. Failed trials remain private; no incomplete
bundle is accepted. Trial 4 predates final source/receipt fields and is not final
integration evidence. A frozen complete rerun remains required.
