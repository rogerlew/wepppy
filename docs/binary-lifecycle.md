# WEPP Binary Lifecycle

## Scope

Lifecycle policy for vendored watershed/hillslope binaries in `wepp_runner/bin`.

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
