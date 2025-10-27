# Phase 4 Scope Proposal — Search & Indexing MVP

## 1. Objective
Deliver the first "intelligence" slice of markdown-doc: performant search and index primitives that improve discoverability without regressing existing lint/catalog flows. Phase 4 should focus on making the doc corpus queryable, laying the groundwork for later watch-mode and caching enhancements. **Prerequisite:** the Phase 3 telemetry task (lint runtime/error logging) must be complete and running in CI before kickoff so we have baseline data.

## 2. Goals
1. **Fast repository search** — `markdown-doc search` returns ranked matches (file, heading, snippet) across ~400–1k Markdown files in <500 ms steady-state (using the cached index when present).
2. **Incremental indexing** — Build a reusable index artifact (JSON/SQLite) that search reuses between runs and can be warmed by CI; rebuilding on demand must remain <5 s so we can defer more complex caching unless telemetry warrants it.
3. **Programmatic output** — Support plain text and JSON outputs so agents and dashboards can consume search results without parsing prose.
4. **Telemetry hooks** — Emit index size, build time, and search latency into the same lightweight telemetry log gathered from docs-quality.

## 3. Non-Goals
- Lint caching or partial re-run infrastructure (revisit once telemetry justifies it).
- Real-time watch mode (capture requirements, but implementation deferred).
- NLP-style semantic search or embedding generation.
- Cross-repo search federation.

## 4. Deliverables
1. **`markdown-doc search` CLI**
   - Flags: `--query/-q`, `--path`, `--limit`, `--format (text|json)`, `--index <path>`, `--no-index-refresh` (use existing index).
   - Matching semantics: case-insensitive token search with Porter stemming; results ranked via TF-IDF (fallback to term frequency if IDF unavailable).
   - Output includes: file path, heading, score, context snippet (default 3 lines), anchor link.
2. **Index builder library**
   - Reads Markdown AST, stores headings + body tokens + update timestamps.
   - Incremental updates: skip files unchanged since last index (compare mtime/hash); full rebuild remains acceptable if telemetry shows <5 s runtime.
   - Stored under `.markdown-doc/index.json` by default; wiring to `.markdown-doc.toml` for overrides. Document optional use of runner cache (future enhancement) and note future opportunity to share scanning with `markdown-doc catalog`.
3. **Integration into docs-quality**
   - Optional step (behind `DOC_SEARCH_INDEX=1`) to build index nightly; collect index runtime & size in telemetry log once lint telemetry baseline is established.
4. **Documentation updates**
   - Quick-start section in `tools/README.markdown-tools.md` for `wctl doc-search` (new wrapper) and index maintenance.
   - README addition describing index file format & best practices.
5. **Tests**
   - Unit tests for tokenizer/indexer.
   - CLI integration tests covering incremental refresh, JSON output, match ordering, and snippet quality (complete sentence, highlight term, paragraph boundaries).
   - Bench baseline for index build/search (target <5s build, <0.5s query on current corpus).

## 5. Workflow Changes
- Add `wctl doc-search` wrapper: runs `markdown-doc search` with project-aware defaults (scoped to docs/ by default, exposes `--path`, `--format`, `--index`).
- Update docs-quality workflow (optional nightly job) to pre-build index and log metrics when `DOC_SEARCH_INDEX=1` env is set.

## 6. Telemetry Plan (MVP)
- Extend existing telemetry log (JSON) with search/index fields:
  ```json
  {
    "timestamp": "2025-11-05T18:42:31Z",
    "commit": "abc1234",
    "lint": {"duration_ms": 4120, "errors": 0},
    "index": {"duration_ms": 2735, "files_indexed": 126, "index_bytes": 482304},
    "search": {"duration_ms": 120, "query": "climate", "results": 12}
  }
  ```
- Append to `docs/work-packages/20251025_markdown_doc_toolkit/telemetry/log.jsonl` (one entry per CI run).
- Review telemetry weekly (or before Phase 4 exit) to confirm targets.

## 7. Dependencies & Prep
- Formatter/indexer lives in `markdown-extract` repo; ensure CI there covers new components.
- Confirm GitHub secret `MARKDOWN_DOC_WORKSPACE` remains aligned (already set).
- Telemetry logging for lint runtime/error count (Phase 3 action) must be merged and running for ≥2 weeks before Phase 4 kickoff.

## 8. Open Questions
1. Should index files be committed to the repo or cached per runner? (Default proposal: generated artifacts only, no git commit.) — *Decide by 2025-11-10.*
2. Do we need a `--watch` preview (file-system notifier) in this phase, or just log requirements for Phase 5? — *Decide by 2025-11-15.*
3. How do we surface search results in the UI? CLI only for now, but note future integration with docs portal. — *Decide by 2025-11-15.*
4. Are there doc subsets we should exclude from search by default (e.g., archived plans)? Rely on `.markdown-doc-ignore` or add search-specific patterns? — *Decide by 2025-11-10.*

## 9. Milestones
1. **Pre-M1 (Phase 3 wrap-up)**: Telemetry logging for lint runtime/error count merged and collecting data for ≥2 weeks; open RFC decisions (link-graph caching strategy, CI bench cadence) resolved.
2. **M1 – Index Foundations**: Library + CLI search with initial index (no incremental updates) + tests + documented matching semantics.
3. **M2 – Incremental Refresh**: Hash/mtime skipping, index stats recorded in telemetry, `wctl doc-search` wrapper.
4. **M3 – Integration**: Optional CI step, documentation, telemetry log consumption plan, snippet quality validation.
5. **Exit Criteria**: Search returns ranked results in <500 ms, index build <5 s, telemetry logging active (lint + index metrics), docs updated, open questions closed or scheduled.
