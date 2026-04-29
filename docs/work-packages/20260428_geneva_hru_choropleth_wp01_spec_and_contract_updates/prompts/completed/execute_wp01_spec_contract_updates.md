# Execute WP01 - Geneva Spec and Contract Updates

Execute WP01 end-to-end before WP02/WP03 implementation.

Required outcomes:
1. Update `wepppy/nodb/mods/geneva/specification.md` with HRU choropleth measure contracts.
2. Keep and document `peak_discharge` as watershed-level only.
3. Define canonical event/measure/HRU join keys and units for query/report usage.
4. Document additive/backward-compatible behavior for legacy runs.

Validation commands:
- `wctl doc-lint --path wepppy/nodb/mods/geneva/specification.md --path docs/work-packages/20260428_geneva_hru_choropleth_wp01_spec_and_contract_updates`
- `git diff --check`

Lifecycle updates required:
- Update WP01 `tracker.md` with UTC progress/decision notes.
- Mark WP01 completion on series orchestration board.
