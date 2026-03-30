# Vulture Dead-Code Gate Standard

## Purpose

Define a low-noise dead-code gate for refactor work in Python modules.

## Applies When

- Agent or reviewer is evaluating dead-code risk during refactor.
- A package introduces or updates Vulture findings.
- A PR modifies files inside Vulture-scanned paths.

## Canonical Configuration

- Source of truth: `pyproject.toml` under `[tool.vulture]`.
- Current gate threshold: `min_confidence = 100`.
- Current whitelist file: `wepppy/vulture_whitelist.py`.

## Gate Policy

1. Treat `--min-confidence 100` as the blocking gate.
2. Treat lower-confidence findings as triage input, not blockers.
3. Prefer explicit whitelist references over broad ignore patterns.
4. Do not use `ignore_names` or `ignore_decorators` unless an approved exception is documented.

## Agent Workflow

1. Run `cd /home/workdir/wepppy && .venv/bin/vulture`.
2. If findings appear, classify each item as:
   - confirmed dead code (remove with test coverage), or
   - false positive (add an explicit whitelist reference).
3. Re-run `.venv/bin/vulture` until exit code `0`.
4. Optionally run `.venv/bin/vulture --min-confidence 60` to review non-blocking drift.

## Whitelist Rules

1. Keep whitelist entries minimal and symbol-specific.
2. Prefer attribute/function/class references over wildcard suppressions.
3. Add a short comment only when the usage path is non-obvious (reflection, dynamic attributes, framework hooks).
4. Remove stale whitelist entries when the referenced symbol no longer exists.

## References

- Root agent map: `AGENTS.md`
- Dependency policy context: `docs/standards/dependency-evaluation-standard.md`
