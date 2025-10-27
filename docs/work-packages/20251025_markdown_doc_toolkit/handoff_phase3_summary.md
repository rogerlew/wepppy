# Phase 3 Adoption Handoff Summary — 2025-10-31

## Current State
- Phase 1–3 markdown-doc features (catalog, lint with severity tuning, toc, validate, mv/refs) are merged and shipping from `/workdir/markdown-extract`.
- docs-quality workflow on the self-hosted runner now:
  - Runs `wctl doc-lint --format sarif/json` against documentation paths.
  - Uploads SARIF directly; formatter emits camelCase fields (no post-processing shim).
  - Executes `wctl doc-bench`.
  - Runs `cargo fmt/clippy/test` via `MARKDOWN_DOC_WORKSPACE` GitHub secret pointing to `/workdir/markdown-extract`.
- `.markdown-doc-ignore` excludes `.docker-data/**`; lint is clean (0 open errors).
- wctl quick-start + exit code table documented in `tools/README.markdown-tools.md`.

## Outstanding Items Before Phase 4 Planning
1. **Telemetry approach** — capture lint runtime + error count per docs-quality run (simple JSON log or weekly summary). Decision still pending.
2. **CI surface** — decide if `wctl doc-bench` remains per-PR or moves to nightly (tracked in RFC decisions table).
3. **Comms/enablement** — publish internal release note (new wctl commands, `.markdown-doc-ignore` expectations) and verify secret/documentation remain in sync.
4. **Phase 4 scope** — gather lint telemetry + link-graph behaviour to inform caching/watch vs. search prioritisation.
5. **Telemetry wiring** — implement lightweight JSON logging (timestamp, lint runtime, error count) inside docs-quality so we have concrete data ahead of Phase 4 discussions.

## Handoff Notes for markdown-doc Team
- Formatter now emits camelCase SARIF keys (`ruleId`, `physicalLocation`, etc.) — no additional workflow changes required.
- Keep `MARKDOWN_DOC_WORKSPACE` secret updated if workspace location changes.
- Monitor `.markdown-doc-ignore` alongside major doc reorganisations.
- Lint backlog cleared; future chores involve routine doc maintenance and the open decisions above.

## Suggested Next Actions
1. Agree on minimal telemetry format and wire it into docs-quality (once per run log with timestamp, runtime, error count).
2. Finalize CI surface decision for benchmarks.
3. Publish short adoption note/release summary for internal users.
4. Schedule Phase 4 planning after a few weeks of telemetry (search/watch/caching).
