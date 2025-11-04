# Prompt: Implement `wctl2`

## Anchor Documents
- [`tools/wctl2/SPEC.md`](../wctl2/SPEC.md) — architecture, module plan, testing expectations
- [`wctl/README.md`](../../wctl/README.md) — current CLI behaviour and user expectations
- [`wctl/install.sh`](../../wctl/install.sh) — installer that generates the `wctl` shim

## Working Set
- **Create:**  
  - `tools/wctl2/__init__.py`  
  - `tools/wctl2/__main__.py`  
  - `tools/wctl2/context.py`  
  - `tools/wctl2/docker.py`  
  - `tools/wctl2/util.py`  
  - `tools/wctl2/commands/__init__.py`  
  - `tools/wctl2/commands/doc.py`  
  - `tools/wctl2/commands/maintenance.py`  
  - `tools/wctl2/commands/npm.py`  
  - `tools/wctl2/commands/python_tasks.py`  
  - `tools/wctl2/commands/playback.py`  
  - `tools/wctl2/commands/passthrough.py`  
  - Tests under `tools/wctl2/tests/` (at minimum smoke coverage for playback and passthrough).
- **Modify:**  
  - `wctl/install.sh` (ensure shim delegates to Typer CLI)  
  - `wctl/README.md` (document the Typer-based workflow)  
- **Avoid:** Do not delete or destabilise existing `wctl.sh` until final rollout; we need both CLIs available.

## Deliverables
1. **Core CLI package (`tools/wctl2/…`)** structured per SPEC:
   - Typer app in `__main__.py`.
   - `CLIContext` in `context.py` for env handling.
   - Compose helper functions in `docker.py`.
   - Shared utilities (argument quoting, cookie loader) in `util.py`.
   - Subcommand modules implementing:
     - doc commands (`doc.py`)
     - maintenance commands (`maintenance.py`)
     - `run-npm` wrapper (`npm.py`)
     - Python task wrappers (`python_tasks.py`)
     - Playback commands (`playback.py`), reusing the logic currently in `tools/profile_playback_cli.py`
     - Fallback passthrough (`passthrough.py`) for unknown invocations.
2. **Refreshed installer** to generate the `wctl` shim that delegates to the Typer app.
3. **Documentation updates** explaining how to install and validate the Typer CLI.
4. **Smoke tests**:
   - Unit coverage for playback command (mocked requests).
   - CLI smoke invoking Typer runner for `run-npm --help`, playback commands (with `backed-globule` profile), and passthrough (e.g., `docker compose ps` dry run).

## Validation Gates
Run from project root unless noted:
1. `python tools/wctl2/tests/run_smoke.py` (or equivalent test harness you introduce) — must pass.
2. `pytest tools/wctl2/tests` — ensure new unit tests succeed.
3. `./wctl/install.sh dev` — verify the shim points at the Typer CLI.
4. Manual smoke:
   - `wctl run-test-profile backed-globule --dry-run`
   - `wctl run-fork-profile backed-globule --undisturbify --timeout 120`
   - `wctl run-archive-profile backed-globule --archive-comment "smoke test" --timeout 120`
   - `wctl run-npm --help`
   - `wctl doc-toc --help`
   - `wctl docker compose config --help` (ensure passthrough works)

## Observable Outputs
- Example CLI usage outputs documenting new command behaviour (include in README updates).
- Code snippets in response showing how `CLIContext` encapsulates env handling.
- Mention how the playback commands use the canonical `backed-globule` profile during smoke testing.

## Positive Framing / Notes
- The goal is to land a clean, testable Python CLI while keeping legacy shim untouched for now.
- Keep the initial MVP aligned with SPEC; you can leave TODO notes for future enhancements, but core commands must work.
- Explicitly log when commands call out to docker compose to aid debugging.
- Keep interface parity: same flags, same defaults, same outputs where feasible.

Thanks! This should be a fun refactor—let’s give downstream agents a breeze to work with. :)
