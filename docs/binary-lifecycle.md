# WEPP and CLIGEN Binary Lifecycle

## Scope

Lifecycle policy for vendored watershed/hillslope binaries in `wepp_runner/bin`
and the Linux CLIGEN 5.3.2 executable in
`wepppy/climates/cligen/bin/cligen532`.

## Canonical Build Environment

- Canonical build host compiler: `/usr/bin/gfortran`
- Disallowed toolchains for vendored builds: Homebrew, Conda, or user-local compiler/runtime stacks
- Required ELF interpreter: `/lib64/ld-linux-x86-64.so.2`
- Required `libgfortran` source: system package libraries (`/lib*` or `/usr/lib*`), not vendored runtime blobs

## Provenance Rejection Criteria

Automatic reject if interpreter, `RPATH/RUNPATH`, or resolved library paths include any of:
- `/home/linuxbrew/.linuxbrew/lib/ld.so`
- `/opt/homebrew/...`
- `/home/*/miniconda*/...`
- `/home/*/miniforge*/...`

Automatic reject if:
- interpreter differs from `/lib64/ld-linux-x86-64.so.2`
- `libgfortran` resolves outside system library prefixes
- non-system dynamic dependency paths are present

## Required Gate

Run for every candidate vendoring operation:

`tools/check_wepp_binary_provenance.sh <binary> [<binary> ...]`

The gate validates interpreter, compiler/runtime fingerprints, `RPATH/RUNPATH`, and `ldd` resolution paths.
Nonzero exit means the binary is not eligible for vendoring.

## Vendoring Enforcement

`tools/rebuild_vendor_wepp_260319.sh` enforces provenance twice:
1. on `wepp-forest/release` build outputs before install into `wepp_runner/bin`
2. again on vendored targets after install

This prevents non-compliant binaries from passing the vendoring path.

## Runtime Enforcement

`wepp_runner` now enforces this provenance contract at runtime before launching any
hillslope, flowpath, or watershed WEPP executable. The runtime guard checks:

- ELF interpreter equals `/lib64/ld-linux-x86-64.so.2`
- no Homebrew/Conda path fingerprints in interpreter or resolved dependencies
- `RPATH/RUNPATH` entries remain in system library prefixes only
- dynamic binaries resolve `libgfortran` from system library prefixes

The guard intentionally fails fast with an explicit remediation error if a selected
binary violates policy. For emergency triage only, operators can bypass the guard by
setting `WEPP_RUNNER_SKIP_BINARY_PROVENANCE_CHECK=1`.

Legacy static binaries (`ldd` reports `not a dynamic executable`) are permitted for
backward compatibility, but all dynamically linked binaries are enforced against the
full provenance policy.

## CLIGEN 5.3.2 Release Pair

CLIGEN source releases are built in `/home/workdir/jimf-cligen532` with:

    RELEASE_LABEL=<reviewed-label> \
      COMPILER=/usr/bin/gfortran \
      tools/build_cligen_release.sh

That command builds in a disposable directory and creates
`release/linux/gfortran/cligen532` plus the adjacent `cligen532.json`. The
`cligen-binary-provenance-v1` sidecar records the binary SHA-256 and size,
CLIGEN version, source commit and tree, canonical source-file manifest,
compiler identity, flags, build time, and ELF metadata. The source build
rejects dirty `.f`, `.inc`, and makefile inputs.

From `/workdir/wepppy`, validate and install the pair with:

    python3 tools/vendor_cligen_release.py \
      --source-root /home/workdir/jimf-cligen532 \
      --expect-source-commit <full-commit> \
      --expect-release-label <reviewed-label>

The vendor tool requires the source checkout to match its remote-default
branch, validates every source-manifest entry, checks the system compiler and
ELF interpreter, stages both files, and installs modes `0755` and `0644`.
Separate files cannot be replaced in one atomic filesystem operation. The tool
therefore validates before replacement, restores both prior files after a
caught failure, and relies on strict runtime verification to reject any mixed
pair left by an external interruption.

Every packaged `cligen532` launch requires the adjacent sidecar and verifies
the binary digest, size, optimized role, clean-source claim, source identities,
and canonical manifest digest before process creation. The run-local CLIGEN log
records the CLIGEN version, release label, binary and sidecar digests, source
commit/tree/manifest digest, and `binary_identity_status=verified`. Historical
`cligen43`, `cligen52`, and `cligen53` executables remain runnable without
sidecars but are explicitly logged as `legacy_unverified`.

The JSON hashes provide integrity and connect the binary to claimed source
bytes. They do not authenticate the publisher. Publisher authentication needs
a separately governed and verified signature over the sidecar.

## Vendored WEPP Release Log

| Date | Release | Source | Binary SHA-256 | Notes |
| --- | --- | --- | --- | --- |
| 2026-10-07 | `wepp_261007`, `wepp_261007_hill` | `wepp-forest` source commit `9c36ae950591e0bd9353662aec0a0f1486ba40db`, merged to default branch `wepp_260430_negmeltfix_comparator` by `687fe7fc` | watershed `9a19c3c8ed83576a2a1c175a9c8c4e0c5ac6c82fa61a293cd3052ee344d12343`; hillslope `e3b554cf22f2229651697438c201b41804fafd0d210c89503a5ea66a1c12d183` | Channel hydrograph volume repair release. Vendored sidecars: `77fbc5ad41163912f8b8648c625e20319952da3374d56cc9792cc78448e7f946` and `68b35a7cf7c574085668023deee8d1e48acf801f5e5ad03e741275fec5fe9f55`. Source-side evidence: focused tests 7/7, full pytest 92/92, source and release host smoke, hillslope watchlist 12/12, artifact policy, JSON/hash checks, and system ELF interpreter checks. WEPPpy evidence: provenance, host smoke, and runner/output regressions passed. |

## Withdrawn Releases

- `wepp_260727` and `wepp_260727_hill` were removed from the WEPPpy vendor set
  on 2026-08-05. Their sidecars select the HBP pass family exclusively, so the
  generated `H*.hbp` files cannot participate in workflows that merge them with
  legacy flat-file `H*.pass.dat` inputs, including AgFields integrated-watershed
  assembly when another required source remains legacy-pass.
- Do not mix pass families or silently substitute another executable. A project
  that persisted `wepp_260727` must explicitly select an installed compatible
  binary and regenerate the dependent hillslope/pass artifacts before watershed
  integration.
