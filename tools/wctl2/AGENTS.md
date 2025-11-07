# wctl2 Agent Playbook

Welcome aboard the Typer-based `wctl2` CLI. This guide keeps agents productive by summarizing the command surface, required docs, and validation gates.

## Directory Map
```
tools/wctl2/
├── AGENTS.md                  # (this doc)
├── __main__.py                # Typer entrypoint
├── context.py                 # env resolution + CLIContext helper
├── docker.py                  # docker compose helpers
├── util.py                    # shared helpers (quoting, logging, etc.)
├── commands/                  # Typer subcommand modules
│   ├── __init__.py            # registration
│   ├── doc.py                 # doc-* commands
│   ├── maintenance.py         # build-static-assets, restore perms
│   ├── npm.py                 # run-npm wrapper
│   ├── playback.py            # run-test/fork/archive profile commands
│   ├── passthrough.py         # docker compose fallback
│   ├── python_tasks.py        # run-pytest, run-stubtest, etc.
│   └── playwright.py          # run-playwright command
├── docs/                      # Specs, prompts, acceptance reports
└── tests/                     # pytest coverage for CLI modules
```

## Core References
- `tools/wctl2/docs/SPEC.md` – overarching architecture and migration plan.
- `tools/wctl2/docs/PROMPT.md` – original scaffolding brief for the CLI.
- `tools/wctl2/docs/playwright.*` – spec/prompt/review for `run-playwright`.
- `wctl/README.md` – user-facing instructions for installing/running `wctl`.

Always cross-check requirements here before coding; the docs move along with the implementation.

## Common Tasks

### Adding/Updating Commands
1. Define logic in `tools/wctl2/commands/<command>.py`.
2. Register the command inside `commands/__init__.py`.
3. Wire shared helpers via `CLIContext` (don’t rebuild env logic locally).
4. Add or extend tests under `tools/wctl2/tests/` using `CliRunner` + monkeypatches.

### Working with run-playwright
- Implementation lives in `commands/playwright.py`.
- Specs, prompt, and acceptance report live under `docs/`.
- Tests in `tests/test_playwright_command.py` cover overrides, env handling, and report behavior.

### Testing Checklist
From repo root:
```bash
PYTHONPATH=/workdir/wepppy pytest tools/wctl2
```
Add targeted cases instead of skipping coverage—CLI modules are expected to be fully unit tested.

## Best Practices
- **Environment resolution:** always use `CLIContext.environment` instead of `os.environ`.
- **Typer options:** prefer `typer.Option`/`Argument` with descriptive help text and default values matching the spec.
- **Subprocesses:** use `subprocess.run(..., env=context.environment)` so generated env files apply everywhere.
- **Error handling:** emit actionable messages via `typer.echo(..., err=True)` and exit with `typer.Exit`.
- **Docs:** when behavior changes, update the corresponding doc in `tools/wctl2/docs/` plus any external references (README, AGENTS, etc.).
- **Validation:** record commands executed (pytest, npm lint, acceptance runs) in handoff notes for downstream agents.

## Onboarding Flow
1. Read this AGENTS file and `docs/SPEC.md`.
2. Skim `__main__.py` to understand how context and passthrough work.
3. Review relevant module docs (e.g., `docs/playwright.SPEC.md`) before editing.
4. Implement changes + tests.
5. Run CLI unit suite; run any command-specific validation (e.g., `npm run lint` for Playwright edits).
6. Summarize commands executed in the final response.

Welcome to the wctl2 toolchain—keep the CLI sharp and well-documented!***
