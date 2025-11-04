> Module Documentation, Typing, and Stub Validation Workflow

Background references:
- `AGENTS.md` -> "Type Stub Management" section
- `docs/dev-notes/style-guide.md` -> Python conventions and docstring expectations
- `wctl/README.md` -> helper commands (`run-pytest`, `run-stubtest`, `run-stubgen`)
- Runtime source tree under `wepppy/...` (especially the target module)

When asked to document or modernize a module (or when planning the work yourself), follow this sequence:

When asked to document, limit code changes to those strictly necessary to clarify behavior, add type hints, and ensure stub consistency. Avoid refactoring or altering logic unless absolutely required for correctness or clarity.

The goal of documentation is to increase code understandability and maintainability without changing its external behavior. Focus on clear docstrings, accurate type hints, and consistent stubs to support developers and tooling.

1. **Survey & plan**
   - Read the existing `.py` module and any related tests or dev-notes.
   - Check `AGENTS.md` for project-wide expectations (type hints, docstrings, stubs).
   - Decide whether this is a module edit only, or if you must touch adjacent code (tests, consumers).
   - Identify companion modules that share a namespace (for example `__init__` aggregators, lazy loaders, or helper utilities) and make sure they receive the same documentation/typing attention.

2. **Bring the module up to standard**
   - Add/refresh Google-style docstrings. Keep them concise; document args/returns/raises and any side-effects or warnings. Preserve existing semantics.
   - Ensure comprehensive type hints: annotate all function/method parameters and returns, include `from __future__ import annotations` if needed, and prefer standard library types (e.g., `collections.abc` for callables/iterables).
   - If the module exposes dataclasses, enums, or constants, make sure their public shape is explicit.

3. **Update or create `.pyi` stubs**
   - Run `stubgen` as a starting point if the stubs are missing or stale:
     ```bash
     wctl run-stubgen
     ```
     (This regenerates `stubs/wepppy/...`; use it to diff but do not commit generated `stubs/` directly.)
   - Manually reconcile the `.pyi` sitting next to the runtime module (`wepppy/.../*.pyi`). Make enums use real values, mark class-level constants as `ClassVar[...]`, and match property signatures including setters.
   - If you add a new module, mirror its public API in a `.pyi` file alongside the `.py`.
   - When a package of related modules (mods, utilities, facades) achieves complete annotations, add `.pyi` coverage for each public entry point so optional consumers remain in sync.
   - After editing, run `python tools/sync_stubs.py` (or `wctl run-stubgen`) so the standalone `stubs/wepppy/` tree matches the source-of-truth `.pyi` files.

4. **Validate with stubtest**
   - Execute stubtest from inside the container using the helper:
     ```bash
     wctl run-stubtest wepppy.nodb.core.your_module
     ```
     (Substitute the module path as needed; add more modules if you touched multiple.)
   - Run stubtest **for every module whose `.py` or `.pyi` you touched** in the change.
     When several modules are involved, prefer individual invocations so failures map
     back to a single stub quickly. Capture the command(s) you executed so reviewers can
     reproduce the checks.
   - Resolve any errors: missing attributes, mismatched signatures, invalid enum definitions, etc.

5. **Run tests (and mypy if appropriate)**
   - `wctl run-pytest` for the relevant test suite (add extra args to focus).
   - If the work changes typing in meaningful ways, run `python -m mypy <target>` locally or `wctl run-pytest` followed by `wctl run-stubtest` to ensure consistency.

6. **Document what changed**
   - Update module-level comments or README snippets if behavior or public API changes.
   - Note new helper commands or workflows in `AGENTS.md` only if they didn't exist previously (avoid duplicate guidance).

7. **Final review**
   - Confirm `git status` shows the expected `.py` and `.pyi` edits plus any regenerated prompt/README changes.
   - Keep generated `stubs/` tree in sync by running `python tools/sync_stubs.py` before committing.
   - Normalize spellings with `uk2us` on the touched files:
     - **Always preview changes first** to avoid breaking code blocks or making nonsensical substitutions:
       ```bash
       diff -u path/to/file.py <(uk2us path/to/file.py)
       ```
     - Review the diff carefully--changes should only affect comments, docstrings, and documentation
     - Do not apply if changes would modify code identifiers, string literals, or technical terms
     - Apply after verification: `uk2us -i path/to/file.py`
     - Adjust `/workdir/uk2us/config/uk2us_rules.json` if the defaults misfire
   - Summarize the changes in PR/commit messages, referencing docstrings, typings, stubs, and validation commands used.

This prompt should be read as instructions to yourself (or to another contributor) whenever a task involves documenting or typing a module. Copy/paste it into your working notes or agent prompt to stay aligned with the project workflow.
