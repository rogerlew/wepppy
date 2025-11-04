# Agent Prompt – Implement wctl markdown-doc Integration

## Mission
Expose the markdown-doc CLI suite through `wctl`, keeping the generated tooling in sync with `install.sh`, and document the workflow so developers and automation can lint, catalog, refactor, and benchmark Markdown safely.

## Background
- Phases 1–3 of the markdown-doc toolkit are complete; binaries (`markdown-doc`, `markdown-doc-bench`) are installed in `/usr/local/bin` and ready for adoption.
- `wctl` scripts are generated via `wctl/install.sh`; manual edits to `wctl/wctl.sh` will be overwritten, so updates must land in the template logic.
- Work package context lives in `docs/work-packages/20251025_markdown_doc_toolkit/` (package, tracker, RFC). The integration spec (`wctl_integration_spec.md`) defines wrapper behaviour, defaults, and smoke-test expectations.

## Reference Material
- `docs/work-packages/20251025_markdown_doc_toolkit/wctl_integration_spec.md`
- `wctl/AGENTS.md`
- Existing `wctl/install.sh` template and generated `wctl/wctl.sh`
- Documentation surfaces: `wctl/README.md`

## Preconditions
- `markdown-doc`, `markdown-doc-bench`, and companion binaries are installed at `/usr/local/bin`.
- No containers need to be running; all helper commands operate on the host.
- Respect repo policies (`AGENTS.md` at repo root and `wctl/AGENTS.md`).

## Primary Tasks
1. **Review the spec and guidelines**
   - Read `wctl_integration_spec.md` end-to-end; reconcile expectations with `wctl/AGENTS.md` (command dispatch order, quoting helpers, logging style).
2. **Update generator/runtime logic**
   - Extend `wctl/install.sh` so generated scripts surface the `doc-*` commands and any shared helpers (e.g., prompt routines that read from `/dev/tty`).
   - After edits, execute `./wctl/install.sh dev` to regenerate `wctl/wctl.sh` (do not hand-edit the output file; keep it staged for review).
3. **Implement command wrappers**
   - Add case branches for `doc-lint`, `doc-catalog`, `doc-toc`, `doc-mv`, `doc-refs`, and `doc-bench` with the defaults specified in the spec.
   - Inject binary availability checks (`command -v`) with actionable guidance when missing; propagate exit codes from the underlying tool.
   - `doc-lint`: when invoked without arguments, run `markdown-doc lint --staged --format json`, print a short notice describing the default before execution, and stream stdout unmodified. Any user-supplied args replace the defaults entirely.
   - `doc-catalog`, `doc-toc`, `doc-refs`: pass through additional flags; enforce at least one target file for `doc-toc` and surface a clear error otherwise.
   - `doc-mv`: perform a dry-run (`--dry-run`) before applying changes, prompting via `/dev/tty` (`read -r -p "Proceed with move? [y/N] "`). Honour `--dry-run-only` (skip prompt, exit after dry-run) and `--force` (skip prompt, run live move immediately). Forward extra flags to both invocations.
   - `doc-bench`: wrap `markdown-doc-bench`, providing a helpful error if the binary is unavailable and defaulting to the standard benchmark suite.
4. **Documentation updates**
   - Expand `wctl/README.md` with concise entries and usage snippets for each new command (defaults, sample invocations, prompt behaviour).
   - Update `wctl/AGENTS.md` with maintenance notes: binary checks, regeneration workflow, prompt expectations, lint defaults, and how to validate changes.
5. **Validation & smoke tests**
   - Run `./wctl/install.sh dev` after changes.
   - Execute the commands listed in spec §4.6, substituting disposable files for `doc-mv` (e.g., files under `tmp/` or `tests/tmp`). Capture outputs/errors and adjust implementations until they succeed.
   - Ensure shell scripts remain POSIX-compliant and lint-friendly (quote variables, use existing helpers).
6. **Finalisation & hand-off**
   - Stage regenerated `wctl/wctl.sh` together with source changes; double-check diff noise (no unintended whitespace).
   - Prepare a concise review summary covering command behaviour, documentation updates, and smoke-test results (include the exact commands executed).
   - Note outstanding follow-ups (e.g., CI wiring referenced in the RFC) in the handoff summary or tracker.

## Validation Checklist
Run the regenerated `wctl` against safe targets (temp files / staged changes):
- `wctl doc-lint`
- `wctl doc-lint --help`
- `wctl doc-catalog --format json > /tmp/doc_catalog.json`
- `wctl doc-toc README.md --dry-run`
- `wctl doc-refs README.md`
- `wctl doc-bench --list`
- `wctl doc-mv --dry-run-only path/to/src.md path/to/dest.md`
- `wctl doc-mv path/to/src.md path/to/dest.md` (respond `y` at prompt using temp files)

## Deliverables
- Updated `wctl` generator/runtime source (`install.sh`, generated `wctl.sh`) featuring the six `doc-*` wrappers.
- Documentation refresh for `wctl/README.md` and `wctl/AGENTS.md` aligned with new behaviour.
- Smoke-test confirmation with commands executed and outcomes recorded in the handoff summary.

## Out of Scope
- CI workflow modifications (tracked in the adoption RFC).
- Changes to markdown-doc binaries or configuration files.
- Phase 4 features (`search`, `watch`, `extended indexing`).

## Notes
- Follow repository editing conventions (use `apply_patch` when practical, avoid destructive git commands, keep comments succinct).
- Maintain American English spelling (run `uk2us` if prose edits introduce UK variants).
- If unexpected repo state appears during work, pause and request guidance before proceeding.
