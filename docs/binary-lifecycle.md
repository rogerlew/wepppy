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
