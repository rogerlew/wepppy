# wctl2 Migration Plan

## Goals
- Preserve the existing `wctl` CLI interface while making the implementation easier to maintain and extend.
- Provide a Python-based command dispatcher with modular structure, unit-test coverage, and clear separation between command logic and Docker Compose passthrough.
- Allow dual operation (`wctl` and `wctl2`) during the transition so agents can validate parity before flipping the default.

## High-Level Architecture
- **Language**: Python 3.11+ using Typer (Click-based) for structured CLI commands.
- **Entry point**: `python -m wctl2` with a thin shell shim that sets up the environment and delegates to Python.
- **Context object**: Central context (`CLIContext`) carrying project root, compose file, temp env path, logger, and resolved defaults. Passed to every command handler.
- **Modules**:
  ```
  tools/wctl2/
    __init__.py
    __main__.py              # Typer app definition
    context.py               # CLIContext + env loading
    docker.py                # Compose helpers (exec, passthrough)
    util.py                  # shared helpers (quote args, cookie loading, etc.)
    commands/
      __init__.py
      doc.py                 # doc-* commands (lint, catalog, toc, mv, refs, bench)
      maintenance.py         # build-static-assets, restore-docker-data-permissions
      npm.py                 # run-npm wrapper
      python_tasks.py        # run-pytest, run-stubtest, run-stubgen, check-* scripts
      playback.py            # run-test-profile, run-fork-profile, run-archive-profile
      passthrough.py         # fallback docker compose passthrough
  ```
- **Environment resolution**: `context.py` merges `docker/.env`, optional host overrides, and runtime overrides to a temporary env file. Commands fetch defaults through the context (e.g., playback base URL).
- **Passthrough**: Unknown commands fall back to `docker compose` with the generated `--env-file` and `-f` flags to preserve existing behaviour.

## Command Mapping
| Existing Command           | Module / Function               | Notes |
|---------------------------|----------------------------------|-------|
| `doc-lint`, `doc-*`       | `commands/doc.py`                | Wrap `markdown-doc` helpers. |
| `build-static-assets`     | `commands/maintenance.py`        | Executes existing script with context flags. |
| `restore-docker-data-permissions` | `commands/maintenance.py` | Moves current shell logic into Python. |
| `run-npm`                 | `commands/npm.py`                | Validates `npm` availability, forwards args. |
| `run-pytest`, `run-stubtest`, `run-stubgen`, `check-test-*` | `commands/python_tasks.py` | Compose exec wrappers with shared quoting helper. |
| `run-test-profile`, `run-fork-profile`, `run-archive-profile` | `commands/playback.py` | Reuse logic from `tools/profile_playback_cli.py`; module becomes the new home. |
| Docker Compose passthrough | `commands/passthrough.py`        | Called when no Typer command matches. |

## Implementation Phases
1. **Bootstrap skeleton**
   - Create package structure (`__main__`, context, docker helpers).
   - Implement CLI context that loads env and determines project paths.
   - Add Typer app with placeholder passthrough.
2. **Port existing logic**
   - Move playback commands into `commands/playback.py`, removing the temporary helper once parity is confirmed.
   - Port doc commands (`doc.py`) and maintenance tasks (`maintenance.py`).
   - Implement Python task wrappers and `run-npm`.
3. **Passthrough fallback**
   - Add catch-all command that invokes `docker compose` with context-managed env.
   - Ensure unknown options go straight to Docker Compose exactly as before.
4. **Testing & validation**
   - Unit tests for command modules (using Typer testing utilities and mocking subprocess calls).
   - Integration smoke invoking Typer runner to ensure help/usage parity.
   - Update CI to run both old and new CLI for a subset of commands during the migration window.
5. **Rollout**
   - Update `install.sh` to optionally install `wctl2`.
   - Document dual usage in `wctl/README.md`.
   - After validation, switch default `wctl` symlink to the Typer-based implementation and retire the legacy shell script.

## Testing Strategy
- **Unit tests**: Each command module has tests covering argument parsing and subprocess invocation (mocked).
- **End-to-end smoke**: Script comparing output of `wctl` vs `wctl2` for critical commands (`run-test-profile --dry-run`, `doc-toc --help`, `docker compose ps` passthrough).
- **Profile playback regression**: Use the promoted `backed-globule` profile as the canonical smoke target for `run-test-profile`, `run-fork-profile`, and `run-archive-profile` to ensure fork/archive flows continue to operate against a known dataset.
- **CI integration**: Add workflow job executing new CLI to catch regressions.

## Documentation
- `tools/wctl2/docs/SPEC.md` (this document) – maintained for architectural reference.
- Update `wctl/README.md` with migration instructions once ready.
- Document how to enable `WCTL_MAN_PATH` replacement if running with limited permissions during installation.

## Next Steps
- Implement phase 1 skeleton and add initial smoke tests.
- Share spec with agents and begin staged migration.
