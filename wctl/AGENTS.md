# wctl/AGENTS.md
> Agent guide for maintaining the wctl wrapper and associated tooling.

## Authorship
**This file is owned by the AI agents. Update it whenever you add, modify, or remove commands or implementation details in the `wctl` directory.**

## Scope
The `wctl` toolset is composed of:
- `wctl/install.sh` — installer that generates `wctl.sh` and writes the man page.
- `wctl/wctl.sh` — runtime wrapper script that users execute.
- `wctl/wctl.1` — manual page.
- `wctl/README.md` — human-facing quick reference.

Changes to any of these pieces must be reflected in this document.

## Requirements When Adding or Removing Commands

1. **Update all touch points**
   - `install.sh`: generator logic must emit the new command branch.
   - `wctl.sh`: ensure the generated script includes the same command implementation.
   - `wctl.1`: document the command in the “COMMANDS” section with synopsis and description.
   - `wctl/README.md`: add/remove bullet(s) describing the command with example usage.

2. **Prefer host vs container clarity**
   - Host commands (e.g., `run-npm`) should check for required binaries (`npm`, etc.) and exit with a clear message if missing.
   - Container commands must go through `docker compose … exec` (use `compose_exec_weppcloud` helper).

3. **Environment handling**
   - Any command that writes to the temporary env file must respect the existing merge order: `docker/.env` → optional host override (`.env` or `WCTL_HOST_ENV`) → exported shell variables → command-specific tweaks.
   - Avoid leaking secrets to stdout/stderr. Mask or omit sensitive values.

4. **Error handling & exit codes**
   - Fail fast (`set -euo pipefail` already enabled).
   - Provide actionable error messages (e.g., “npm is required for run-npm”).
   - Return zero on success, non-zero on failure.

5. **Testing Expectations**
   - After modifying wctl, run:
     ```bash
     ./wctl/install.sh dev
     wctl --version 2>/dev/null || true
     wctl man --no-pager >/dev/null
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
   - When removing a command, note the change in `wctl/README.md` or release notes.
   - Provide migration guidance if the workflow changes (e.g., new flags or renamed commands).

7. **Documentation style**
   - README bullet list stays short and example-driven.
   - Man page entries follow existing groff formatting (use `.TP`, `.B`, `.BR` patterns).

## Release Checklist for wctl Changes

- [ ] Update `install.sh`, regenerate `wctl.sh`.
- [ ] Update manual (`wctl.1`).
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
