# WP10 Validation Evidence

## Focused behavior

- Lifecycle/update/archive/fork/sanitization suite: `153 passed`.
- Recovery-before-archive produces a matching config/manifest pair and removes
  the journal before ZIP creation.
- Fork and archive/restore fixtures compare config and manifest bytes exactly.
- New and legacy transaction files are absent from restored project state.
- Composite run fixtures select the top-level authority lock.
- Legacy fallback and invalid/newer-manifest degraded reader fixtures pass.
- A concurrent update remains blocked until the lifecycle guard exits.

## Repository gates

- Stubtest and test-stub completeness: passed.
- Focused randomized and per-file isolation: passed.
- Documentation lint: passed.
- Changed-file broad-exception enforcement: passed; existing approved fork
  boundary line references were updated after source movement.
- RQ dependency graph: regenerated and passed; edge count remains `144`.
- `wctl run-pytest tests --maxfail=1`: `6935 passed`, `63 skipped` in
  `671.83s`.
