# RFC: markdown-doc Adoption & Integration

**Date:** 2025-10-30  
**Author:** Codex (on behalf of tooling team)  
**Stakeholders:** Roger Lew, markdown-doc maintainers, wepppy platform team, CI owners

---

## 1. Summary

Phase 1–3 of the `markdown-doc` toolkit are complete inside `/workdir/markdown-extract`. The CLI now delivers catalog generation, comprehensive linting (with severity tuning), template validation, TOC maintenance, and refactor-safe commands (`mv`, `refs`) with structured outputs. Binaries are installed at `/usr/local/bin`. This RFC proposes the adoption path inside `/workdir/wepppy`, outlines integration work, and records remaining decisions before scheduling Phase 4 (`search`, `watch`).

## 2. Background

- Initial work package targeted automation for documentation hygiene across ~388 Markdown files.  
- MVP (catalog + broken-link lint) landed with config precedence, selective scanning, and JSON/SARIF output.  
- Phase 2 extended lint coverage (anchors, hierarchy, required sections), added template validation, TOC regeneration, and severity tuning/ignore lists.  
- Phase 3 delivered refactor capability via the markdown-doc link graph core, `mv`, and `refs`, along with complex fixtures (`tests/markdown-doc/refactor/complex/`).  
- Documentation now includes architecture notes, agent workflows, safety guarantees, and CI examples.

## 3. Current State Snapshot

- All commands ship as release binaries (`markdown-doc`, `markdown-edit`, `markdown-extract`) under `/usr/local/bin`.  
- README documents catalog, lint, validate, toc, mv, refs, JSON/SARIF output formats, selective scanning, and concurrency guarantees.  
- `cargo test --all` and targeted benchmarks pass locally; CI in `/workdir/markdown-extract` is green.  
- `.markdown-doc-ignore` and severity tuning are active; defaults avoid false positives across legacy docs.

## 4. Integration Plan for /workdir/wepppy

1. **CI Alignment**  
   - Add `markdown-doc lint --staged --format json` to `wctl` wrappers.  
   - Extend GitHub Actions (or equivalent) to run `fmt`, `clippy`, `cargo test --all`, and lint/benchmark smoke (`markdown-doc-bench`).  
   - ✅ `docs-quality.yml` workflow (self-hosted runner) now runs `wctl doc-lint` (SARIF + JSON) on documentation paths, uploads SARIF directly (formatter emits camelCase fields), executes `wctl doc-bench`, and conditionally runs `cargo fmt/clippy/test` when a markdown-doc workspace is available (`MARKDOWN_DOC_WORKSPACE` env or common install paths). Action item: set the env var on homelab runners so Rust checks always enforce.  

2. **Developer Experience**  
   - Provide `wctl doc-{lint,catalog,toc,mv,refs}` aliases.  
   - Check in sample pre-commit hook using JSON output (mirroring README).  
   - Publish release notes in `docs/work-packages/20251025_markdown_doc_toolkit/changelog.md` (new) or parent repo release process.

3. **Documentation & Training**  
   - Add command × exit-code quick reference and short adoption guide to the work package README or `tools/README.markdown-tools.md`.  
   - Announce availability to agent maintainers; highlight `.markdown-doc-ignore` usage and dry-run flows for `mv`.

## 5. Decisions Required

| Decision | Owner | Options | Due |
|----------|-------|---------|-----|
| Link graph caching + directory move roadmap | Tooling + Docs leads | (a) keep in-memory only (status quo); (b) add persisted cache keyed by git hash; (c) schedule incremental watch service | 2025-11-05 |
| Phase 4 scope (`search`, `watch`, `stats`) | Product + Docs leads | Define acceptance metrics (latency, ranking, snippet quality) or defer to later quarter | 2025-11-08 |
| CI surface area | Platform team | Decide whether markdown-doc benches run per PR or nightly | 2025-11-03 |
| Release comms | Docs + Enablement | Determine channel (release notes, docs newsletter) and target audience | 2025-11-02 |
| SARIF schema compliance | markdown-doc maintainers | ✅ Formatter emits camelCase fields (e.g., `ruleId`, `physicalLocation`, `fullDescription`); docs-quality workflow no longer performs normalization | ✅ |
| `.docker-data` permission strategy | Platform + Tooling | **Resolved 2025-10-31:** Adopt option (a); repository ships `.markdown-doc-ignore` with `.docker-data/**` so catalog/lint skip docker volumes. Retain `sudo wctl restore-docker-data-permissions` in troubleshooting docs. | ✅ |

## 6. Risks & Mitigations

- **CI noise from legacy edge cases** – Leverage severity tuning + `.markdown-doc-ignore`; add targeted fixtures for known exceptions.  
- **Concurrent adoption friction** – Command wrappers and documentation updates scheduled before enabling CI failure gates.  
- **Scope creep into Phase 4 during integration** – Capture future enhancements in tracker; only land caching/indexing once telemetry justifies it.
- **SARIF uploads** – Formatter now outputs CodeQL-compliant camelCase fields; docs-quality ships SARIF without extra normalization.  
- **Permission failures when scanning `/workdir/wepppy/.docker-data/*`** – Mitigated by `.markdown-doc-ignore` entry that excludes docker volumes; keep restore command in troubleshooting for existing environments.

## 7. Rollout Checklist

- [ ] Land CI updates (`fmt`, `clippy`, `test`, `markdown-doc lint`, `markdown-doc-bench`).
- [ ] Publish `wctl` wrappers and developer quick start.  
- [x] Resolve `.docker-data` permission workaround (commit `.markdown-doc-ignore` with `.docker-data/**`).
- [ ] Document exit codes + automation patterns in tools README.  
- [ ] Issue release notes / announce to agent maintainers.  
- [ ] Confirm telemetry plan for Phase 4 decision gate.  
- [ ] Update work package tracker (`tracker.md`) once integration merges.

## 8. Timeline & Next Steps

- Integration work targeted for week of 2025-11-03 (post-CI alignment).  
- Decision reviews scheduled via async comments on this RFC; final approval by 2025-11-08.  
- After buy-in, we promote markdown-doc usage across doc workflows and revisit Phase 4 scope in Q1 2026 planning.

## 9. References

- `docs/work-packages/20251025_markdown_doc_toolkit/package.md` (work package tracker)  
- `/workdir/markdown-extract/README.md` (canonical feature documentation)  
- `tests/markdown-doc/refactor/complex/` (refactor regression fixtures)  
- `/usr/local/bin/markdown-doc` (installed binary)
