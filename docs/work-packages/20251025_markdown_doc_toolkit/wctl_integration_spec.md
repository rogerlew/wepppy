# wctl Integration Specification — markdown-doc Toolkit

**Last updated:** 2025-10-30  
**Owner:** Tooling team (Codex)  
**Consumers:** wctl maintainers, infrastructure agents, CI owners

---

## 1. Purpose

Define the changes required to expose the `markdown-doc` CLI suite through `wctl`, align developer ergonomics, and unblock CI adoption in the `/workdir/wepppy` repository. This specification converts the shipped Phase 1–3 functionality (catalog, lint, toc, validate, mv, refs) into first-class wctl workflows while preserving existing install/dispatch patterns.

## 2. Goals & Non-Goals

### Goals
- Provide host-side helpers (`wctl doc-*`) that wrap `markdown-doc` commands with sensible defaults and pass-through flags.
- Ensure wrappers integrate with generated `wctl.sh` via `install.sh`, include binary availability checks, and return actionable exit codes.
- Update `wctl` documentation surfaces (README, man page, AGENTS guide) to reflect new commands and usage.
- Capture testing requirements so future changes can be validated consistently.

### Non-Goals
- No changes to the underlying `markdown-doc` binaries or configuration format.
- No Docker/container orchestration updates (wrappers run on the host).
- Phase 4 features (`search`, `watch`, indexing) remain out of scope.

## 3. Deliverables

| Command | Invocation | Default Behaviour | Notes |
|---------|------------|-------------------|-------|
| `wctl doc-lint` | `markdown-doc lint [ARGS…]` | Without args, runs `markdown-doc lint --staged --format json` and streams JSON to stdout. Additional args replace defaults. | Use `jq`-friendly JSON by default for automation. Provide helpful message if `markdown-doc` missing. |
| `wctl doc-catalog` | `markdown-doc catalog [ARGS…]` | No args ⇒ full repo catalog. Flags pass-through unchanged. | Preserve exit code & stdout from underlying command. |
| `wctl doc-toc` | `markdown-doc toc [ARGS…]` | Requires at least one file argument. Pass optional `--update`. | Surface error when no file provided. |
| `wctl doc-mv` | Two-step workflow: dry-run then optional apply. | Default: execute `markdown-doc mv --dry-run SRC DEST`; on success prompt `Proceed with move? [y/N]`. If user confirms, run real command. Flags `--dry-run-only` and `--force` bypass prompt. | Ensure prompts go to `/dev/tty` to avoid piping issues. |
| `wctl doc-refs` | `markdown-doc refs [ARGS…]` | Pass-through wrapper. | Intended for locating references pre-refactor. |
| `wctl doc-bench` | `markdown-doc-bench [ARGS…]` | No args ⇒ run default benchmark suite. | Used by CI to spot regressions; ensure binary exists before call. |

## 4. Implementation Notes

1. **Binary detection**  
   - Each wrapper must verify that the corresponding binary (`markdown-doc`, `markdown-doc-bench`) is available (`command -v …`) and fail with guidance if not installed.

2. **`install.sh` template updates**  
   - Add the new case branches to the script template so regenerated `wctl.sh` matches manual edits. Keep ordering consistent with existing helper commands.
   - New helper functions may be declared above the dispatch `case` if necessary (e.g., prompt helper for `doc-mv`).

3. **Argument handling**  
   - Use existing `quote_args` helper to safely forward user-supplied parameters where needed.
   - For `doc-lint`, treat any user input as a full override of default args (i.e., only inject `--staged --format json` when no args provided). Print a one-line status message describing the effective command before execution when defaults kick in.
   - For `doc-mv`, support:
     - `--dry-run-only`: skip prompt, run dry-run and exit.
     - `--force`: skip prompt and run live move immediately.
     - Additional flags should be forwarded to both dry-run and live calls.

4. **Prompting (doc-mv)**  
   - Use `read -r -p "Proceed with move? [y/N] " answer` bound to `/dev/tty`. Only accept `y`/`Y` to continue; anything else aborts.
   - When aborting, exit 1 so automation can detect no move occurred.

5. **Documentation updates**  
   - `wctl/README.md`: Add succinct bullets for each `doc-*` command with example usage (staged lint, catalog regen, mv dry-run, etc.).
   - `wctl/AGENTS.md`: Record checklist items specific to these wrappers (binary checks, prompt behaviour, default JSON output).

6. **Testing expectations**  
   - After running `./wctl/install.sh dev`, verify:
     ```bash
     wctl doc-lint              # runs staged JSON lint
     wctl doc-lint --help       # passes through to markdown-doc
     wctl doc-catalog --format json >/tmp/catalog.json
     wctl doc-toc README.md --dry-run
     wctl doc-refs README.md    # ensures pass-through works
     wctl doc-bench --list      # optional benchmark flag
     wctl doc-mv --dry-run-only docs/README.md docs/README2.md
     ```
   - For `doc-mv`, simulate confirmation flow (e.g., using temporary files in `tests/tmp`). Do **not** run against repo docs in automated tests.

7. **CI integration follow-up**  
   - Expose `wctl doc-bench` for pipelines but do not modify CI scripts within this change. Future work will wire the command into workflows per RFC.

## 5. Acceptance Criteria

- `wctl` offers the wrappers described above, respecting defaults and pass-through semantics.
- Documentation (README, man page, AGENTS guide) accurately reflects new commands.
- `./wctl/install.sh dev` regenerates `wctl.sh` without manual edits afterward.
- Smoke tests recorded in section 4.6 succeed on a clean checkout with the markdown-doc binaries installed at `/usr/local/bin`.

## 6. Open Questions

- Should `wctl doc-lint` support a `--human` toggle to emit plain text instead of JSON? (Pending feedback.)
- Should benchmark runs live in CI per-PR or nightly? (Tracked in adoption RFC.)

Document owners should update this spec if behaviour deviates or additional helpers are introduced.
