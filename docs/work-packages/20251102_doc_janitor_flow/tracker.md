# Work Package Tracker: Documentation Janitor Flow

**Status:** Draft — Planning & Pilot Prep  
**Last Updated:** 2025-11-02 (by Codex)

**Related Systems:**  
- `cao/` (CLI Agent Orchestrator) — flow automation & agent orchestration  
- `wctl doc-*` wrappers — markdown-doc toolkit entry points  
- `docs-quality` CI workflow — existing lint/telemetry pipeline

---

## Goals

- Stand up a nightly “Doc Janitor” agent flow that keeps Markdown hygiene tasks under control without relying on ad-hoc human sweeps.
- Validate CAO’s scheduled-flow machinery against a low-risk maintenance workload.
- Maintain a clear approval loop so automated doc edits land via reviewable PRs, not direct pushes.

### Success Criteria

1. Nightly cron-triggered flow generates zero-error lint reports for staged docs or opens actionable issues.
2. Catalog / TOC regeneration diffs stay < 200 modified lines per run (guardrail).
3. Automation submits PRs on a dedicated branch (`automation/doc-janitor/*`) within 15 minutes of the scheduled window.
4. Telemetry logged to `telemetry/docs-quality.jsonl` for each run; dashboards can show trend lines after two weeks.

---

## Scope

- **Included**
  - Run `wctl doc-lint --path docs --format json` (read-only) and record results.
  - Regenerate `DOC_CATALOG.md` via `wctl doc-catalog --path docs --output DOC_CATALOG.md`.
  - Update TOC markers for targeted files (initial set: `docs/**/*.md`, `README.md`) using `wctl doc-toc … --update`.
  - Commit diffs to temporary workspace; if safe, ask MCP agent to open PR using `gh pr create`.
  - Append telemetry entry summarizing runtime, lint status, diff stats.
- **Excluded (Phase 1)**
  - Free-form rewriting or style fixes.
  - Auto-merging PRs.
  - Changes outside `docs/**`, `README.md`, or `.markdown-doc-*`.

---

## Task Board

### Backlog

- [ ] Decide pilot cadence (nightly vs. twice-weekly) and cron expression.
- [ ] Define list of TOC targets & store in repo (`docs/tooling/doc_toc_targets.txt`?).
- [ ] Add `.markdown-doc-ignore` guidance to onboarding (ties into existing TODO).
- [ ] Draft runbook for pausing/resuming the janitor flow.

### In Progress

- [ ] Work Package authoring (this doc) — outlines scope/guardrails for janitor.
- [ ] CAO flow + script scaffold (`cao/flows/doc_janitor.yaml`, `cao/scripts/doc_janitor.sh`).

### Done

- [x] Stakeholder alignment (human sign-off to proceed).
- [x] Identify tooling dependencies (markdown-doc toolkit, gh CLI, CAO).

---

## Implementation Sketch

1. **Script (`cao/scripts/doc_janitor.sh`)**
   - Runs inside CAO terminal.
   - Steps:
     1. `set -euo pipefail`.
     2. Run lint (`wctl doc-lint …`) capturing JSON output; on failure, exit non-zero but upload artifact.
     3. Run catalog + TOC updates.
     4. Compute diff (`git status --short`); if empty, exit success with message.
     5. If diff too large (`git diff --stat` > guardrail), abort and notify.
     6. Otherwise create branch, commit, and invoke helper to open PR (or attach summary to inbox).
   - Emits telemetry JSON line regardless of outcome.
2. **Flow Definition (`cao/flows/doc_janitor.yaml`)**
   - Cron schedule (placeholder `0 9 * * *` UTC).
   - Agent profile: dedicated maintenance persona (clone of reviewer with doc focus).
   - Payload instructs agent to run the script via `bash`.
3. **Telemetry Hook**
   - Reuse docs-quality JSONL; ensure script appends with `jq -n`.
4. **Pilot Process**
   - Week 1: manual invocation via `cao flow run doc-janitor --once`, confirm diffs sensible.
   - Week 2: enable cron, require human review of PRs.
   - After stabilization: document escalation path & add monitors (failures ping Slack/email).

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Large diffs from TOC regeneration | PR noise, merge conflicts | Guardrail threshold, allow per-file allowlist, human review |
| Lint failures block other actions | Missed hygiene tasks | Continue workflow but label PR `needs-doc-fix` |
| Script runs during heavy doc churn | Merge conflicts | Cron off-hours + skip if repo has uncommitted changes / conflicting branch present |
| Credentials for `gh` not available | PR creation fails | Detect missing auth, fall back to opening issue with attached patch |

---

## Next Steps

1. Flesh out script & flow skeletons; commit behind feature flag.
2. Document manual trigger procedure in `docs/dev-notes/docs-maintenance.md` (new doc).
3. Coordinate with infra to provision service account for `gh`.
4. After pilot, update this tracker with metrics & decision to graduate to “Active”.

---

## Notes

- Aligns with markdown-doc Phase 4 roadmap (search/index). Clean doc tree is prerequisite.
- Provides an end-to-end CAO pilot touching tmux sessions, MCP, and external tooling.
- Keep logs under `~/.aws/cli-agent-orchestrator/logs/doc-janitor/*.log` for troubleshooting.

