# RFC: Phase 4 — markdown-doc Search & Indexing MVP

**Date:** 2025-10-31  
**Author:** GPT‑5 Codex  
**Stakeholders / Approvers:** Roger Lew, GPT‑5 Codex, Claude Sonnet 4.5  
**Status:** Draft (pending telemetry gating + stakeholder sign-off)

---

## 1. Summary

Phase 4 delivers the first “intelligence” slice for `markdown-doc`: fast repository search backed by a reusable index. The goal is to make the Markdown corpus queryable without regressing existing lint/catalog workflows and to gather the telemetry required to justify future caching/watch efforts. Kickoff is blocked on Phase 0 (telemetry logging for lint runtime/error count) so we have baseline data before expanding the toolchain.

---

## 2. Objectives

1. **Fast repository search** — `markdown-doc search` returns ranked matches (file, heading, snippet) across ~400–1 000 Markdown files in \<500 ms steady state (using a cached index when available).
2. **Reusable index artifact** — Incremental index builder (JSON/SQLite) that skips unchanged files (mtime/hash), rebuilds in \<5 s when necessary, and surfaces size/runtime telemetry.
3. **Programmatic output** — Plain-text and JSON outputs so agents/automation can consume search results.
4. **Telemetry hooks** — Extend docs-quality log with index/search metrics (duration, size, results) alongside existing lint telemetry.

---

## 3. Scope & Non-Goals

### In Scope
- New CLI command: `markdown-doc search` with ranking (token search + TF‑IDF or term frequency fallback) and snippet generation.
- Index builder library + CLI integration (default location `.markdown-doc/index.json`, configurable via `.markdown-doc.toml`).
- Incremental refresh (skip unchanged files via hash/mtime) with optional `--no-index-refresh` hint.
- `wctl doc-search` wrapper and documentation updates (`README.md`, `tools/README.markdown-tools.md`).
- Optional docs-quality step (behind `DOC_SEARCH_INDEX=1`) to pre-build and log index metrics.

### Out of Scope
- Lint caching / partial re-run infrastructure.
- Real-time watch mode (requirements captured, implementation deferred).
- Semantic search / embeddings.
- Cross-repo or non-Markdown search federation.

---

## 4. Dependencies & Gating Tasks

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 0 telemetry (lint runtime/error JSON log in docs-quality) | ❌ | Must ship & collect ≥2 weeks before Phase 4 kickoff |
| `.markdown-doc-ignore` for docker volumes | ✅ | Already committed (`.docker-data/**`) |
| SARIF camelCase formatter | ✅ | Phase 3.5 change removes CodeQL shim |
| MARKDOWN_DOC_WORKSPACE secret | ✅ | Points to `/workdir/markdown-extract` |

---

## 5. Deliverables

1. **CLI & Index**
   - `markdown-doc search --query/-q` with `--path`, `--limit`, `--format {text,json}`, `--index <path>`, `--no-index-refresh`.
   - Ranking via token-based search + TF‑IDF (fall back to term frequency when IDF missing).
   - Snippet (3 lines by default) with matched tokens highlighted.

2. **Index Builder API**
   - Library functions to build/update index (stored under `.markdown-doc/index.json` or configured path).
   - Incremental refresh (skip files when hash/mtime unchanged).
   - CLI output reporting index stats (files indexed, duration, bytes).

3. **Telemetry**
   - Extend JSONL log to include index/search metrics:
     ```json
     {
       "timestamp": "...",
       "commit": "abc1234",
       "lint": {"duration_ms": 4120, "errors": 0},
       "index": {"duration_ms": 2735, "files_indexed": 126, "index_bytes": 482304},
       "search": {"duration_ms": 120, "query": "climate", "results": 12}
     }
     ```
   - Upload telemetry file as workflow artifact (reusing Phase 0 logging path).

4. **Docs & Developer Experience**
   - `wctl doc-search` wrapper referencing new CLI.
  - README + architecture updates (index format, search usage, best practices).
   - Developer quick start + exit-code table update (tools README).

5. **Tests & Benchmarks**
   - Unit tests for tokenizer/indexer/snippet logic.
   - CLI integration tests (JSON output, ranking, incremental behavior).
   - Benchmark harness covering index build \<5 s and search \<0.5 s (current corpus).

---

## 6. Milestones & Timeline

> Tentative dates assume telemetry gate clears by **2025‑11‑18**. Adjust as needed once Phase 0 merges.

| Milestone | Target | Description |
|-----------|--------|-------------|
| **Phase 0 – Telemetry Gate** | ✅ due 2025‑11‑18 | Ship & collect lint runtime/error telemetry (≥2 weeks of data) |
| **M1 – Index Foundations** | 2025‑12‑06 | Basic index builder + `markdown-doc search` (full rebuild only), text/JSON output, initial tests |
| **M2 – Incremental Refresh** | 2025‑12‑20 | Hash/mtime skip, index stats telemetry, `wctl doc-search` wrapper |
| **M3 – Integration & Docs** | 2026‑01‑10 | Optional CI index build behind env flag, documentation updates, snippet quality validation |

Exit criteria:
- Search results return in \<500 ms (steady state, cached index).
- Index rebuild \<5 s on current corpus.
- Telemetry log includes lint + index metrics.
- Documentation (README, tools) updated; open questions resolved or scheduled.

---

## 7. Work Package Breakdown

1. **Phase 0 Task** (blocking): implement telemetry logging in docs-quality (duration/errors) → run for ≥2 weeks.
2. **Agent tasks** (Phase 4):
   - *Agent 11*: Index builder + CLI skeleton (M1).
   - *Agent 12*: Incremental refresh + telemetry integration + wctl wrapper (M2).
   - *Agent 13*: Docs-quality integration, documentation, benchmarks (M3).

Prompts/work items will mirror Phase 3 structure (to be added after RFC approval).

---

## 8. Open Questions & Decisions

1. **Index artifact storage** — repo artifact vs. runner cache. Proposal: treat as generated artifacts (no git commit). *Decision by 2025‑11‑10.*
2. **Watch mode preview** — capture requirements in RFC (Phase 4 output), implementation deferred. *Decision by 2025‑11‑15.*
3. **UI integration** — CLI only for MVP; document future portal integration ideas. *Decision by 2025‑11‑15.*
4. **Search ignore patterns** — rely on existing `.markdown-doc-ignore`, optionally add search-specific overrides if telemetry reveals noise. *Decision by 2025‑11‑10.*

---

## 9. Approval Checklist

- [ ] Stakeholders review & sign-off (Roger Lew, GPT‑5 Codex, Claude Sonnet 4.5).
- [ ] Phase 0 telemetry shipped and collecting data.
- [ ] Prompts/work package created for Phase 4 agents.

Once approved, we’ll create the Phase 4 work package directory entries (prompts, tracker updates) and schedule agent assignments aligned with the milestone dates above.
