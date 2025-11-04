# wctl/AGENTS.md
> Agent guide for maintaining the wctl wrapper and associated tooling.

## Authorship
**This file is owned by the AI agents. Update it whenever you add, modify, or remove commands or implementation details in the `wctl` directory.**

## Scope
The `wctl` toolset is composed of:
- `wctl/install.sh` — installer that generates the shim (`wctl.sh`) and optional symlink.
- `wctl/wctl.sh` — lightweight wrapper that resolves the project root, exports `WCTL_COMPOSE_FILE`, and invokes `python -m wctl2`.
- `wctl/README.md` — human-facing quick reference for the Typer CLI.

The legacy man page has been retired; Typer help (`wctl --help`) is now the canonical documentation. Changes to any of the pieces above must be reflected in this document.

## Requirements When Adding or Removing Commands

1. **Update all touch points**
   - `install.sh`: ensure the shim exposes the correct compose file and environment to `wctl2`.
   - `wctl.sh`: verify the generated script matches the intended defaults (usually dev compose).
   - `wctl/README.md`: add/remove bullet(s) describing the command with example usage.

2. **Prefer host vs container clarity**
   - Host commands (e.g., `run-npm`) should continue to check for required binaries (`npm`, etc.) inside the Typer command implementations.
   - Container commands must route through the compose helpers in `tools/wctl2/docker.py` so that context logging stays consistent.

3. **Environment handling**
   - `CLIContext` already merges `docker/.env` → optional host override (`.env` or `WCTL_HOST_ENV`) → shell overrides. New commands should reuse the context instead of re-opening env files.
   - Avoid leaking secrets to stdout/stderr. Mask or omit sensitive values.

4. **Error handling & exit codes**
   - The shim still runs with `set -euo pipefail`; Typer commands should raise `typer.Exit` with appropriate codes.
   - Provide actionable error messages (e.g., “npm is required for run-npm”).

5. **Testing Expectations**
   - After modifying wctl, run:
     ```bash
     ./wctl/install.sh dev
     wctl --help
     wctl docker compose ps
     ```
   - For container commands, ensure the `weppcloud` service is up before testing.
   - Host commands should be exercised once (e.g., `wctl run-npm --version`) to validate binary detection.
   - Exercise the markdown-doc wrappers when binaries are available:
     ```bash
     wctl doc-lint
     wctl doc-catalog --path docs --format json
     wctl doc-toc README.md --update
     wctl doc-refs README.md --path docs
     wctl doc-bench --path docs --warmup 0 --iterations 1
     ```
     For `doc-mv`, the repository currently blocks traversal of `.docker-data/redis`; use a docs subdirectory (for example files under `tests/tmp/`) or temporarily prepend a mock `markdown-doc` binary to `PATH` to validate the dry-run/prompt behaviour.

6. **Backward compatibility**
   - When removing or renaming a command, note the change in `wctl/README.md` or release notes and provide Typer-friendly migration guidance (`wctl <command> --help`).

7. **Documentation style**
   - README bullet list stays short and example-driven.
   - No man page is generated; rely on Typer help text. If a command needs longer guidance, update both the README and the command docstring/help string.

## Release Checklist for wctl Changes

- [ ] Update `install.sh`, regenerate `wctl.sh`.
- [ ] Update `wctl/README.md`.
- [ ] Reflect expectations here (`wctl/AGENTS.md`).
- [ ] Re-run `./wctl/install.sh dev`.
- [ ] Smoke-test new command(s) with `wctl …`.
- [ ] Communicate changes if workflows shift (CLI release notes, PR summary).

## markdown-doc Wrapper Notes

- `doc-lint` injects `--staged --format json` when no arguments are provided and prints the effective command to stderr so stdout stays JSON-only.
- `doc-catalog`, `doc-refs`, and `doc-bench` forward flags directly to the underlying binaries; prefer adding `--path docs` during local smoke tests until `.docker-data/redis` ignores land.
- `doc-toc` converts positional Markdown paths to repeated `--path` flags before invoking `markdown-doc toc`, ensuring at least one target is supplied.
- `doc-mv` always performs a dry-run first, prompts on `/dev/tty`, then applies the move unless `--dry-run-only` (skip apply) or `--force` (skip prompt) is used. The confirmation helper lives in `doc_mv_confirm()`.
- To exercise the prompt flow in non-interactive harnesses, temporarily prepend a mock `markdown-doc` binary (for example under `/tmp/mock-md`) so the command can complete without scanning the full repository.

Keep this guide accurate. It’s the authoritative checklist agents should follow to keep the user experience consistent whenever wctl evolves.
