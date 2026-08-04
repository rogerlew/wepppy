# Operator-only: `wctl` workflows (wepppy)

Use `wctl` as the canonical entrypoint for running the WEPPcloud Docker stack and companion tooling.

Do not use this reference for normal WEPPcloud web users.

## Quick start (local dev)

1. From the `wepppy` repo root, install the shim:
   - `./wctl/install.sh dev` (or `prod`)
2. Confirm the CLI is available:
   - `wctl --help`
3. Use Typer discovery:
   - `wctl run-test-profile --help`
   - `wctl run-python --help`
4. Use compose passthrough when needed:
   - `wctl ps`
   - `wctl logs weppcloud`

Canonical docs live in `wepppy/wctl/README.md`.

## Profile playback (deterministic runs)

Typical loop:
- `wctl run-test-profile <profile> --dry-run`
- `wctl run-fork-profile <profile> --timeout <seconds>`
- `wctl run-archive-profile <profile> --archive-comment "<note>" --timeout <seconds>`

If the user says “run a known scenario”, prefer using profiles first (repeatable + debuggable).
