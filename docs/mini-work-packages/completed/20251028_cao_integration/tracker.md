# Mini Work Package: CAO Integration & Documentation

**Status:** Completed  
**Completed:** 2025-10-28  
**Last Updated:** 2025-10-28 (by GitHub Copilot)

**Related Systems:**  
- `services/cao/` — CLI Agent Orchestrator (Codex-only fork)  
- `docs/` — wepppy documentation standards  

---

## Objective

Integrate awslabs/cli-agent-orchestrator into wepppy's service tree with comprehensive documentation aligned to wepppy standards. Replace Amazon Q CLI with Codex CLI provider, validate end-to-end agent orchestration, and document potential applications for future work packages.

## Deliverables

### Infrastructure
- ✅ CAO service relocated to `services/cao/` with full source tree
- ✅ Codex CLI provider implementation (`providers/codex.py`)
- ✅ Flow definitions scaffolded (`flows/doc_janitor.yaml`)
- ✅ Installation via `uv pip install -e services/cao`
- ✅ End-to-end validation (tmux sessions, API, agent launching)

### Documentation
- ✅ **README.md** — Comprehensive rewrite (~850 lines)
  - Architecture diagrams and component breakdown
  - Command-by-command walkthroughs (`cao-server`, `cao launch`, `cao flow add`)
  - Orchestration patterns (handoff, assign, send_message) with diagrams
  - Tmux workflow integration
  - Apache-2.0 license compliance and attribution
  - Removed all Amazon Q CLI references
- ✅ **AGENTS.md** — Development guide authored by Codex
- ✅ **cao-potential-applications.md** — 22 cataloged use cases for future work

### Legal Compliance
- ✅ Proper Apache-2.0 attribution to awslabs/cli-agent-orchestrator
- ✅ Derivative work copyright notice (University of Idaho)
- ✅ LICENSE and NOTICE file preservation

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

## What Worked Well

**Codex integration:**
- Provider heuristics (regex-based status detection) validated in live runs
- Profile mirroring to `~/.codex/prompts/` seamless
- `codex --full-auto` flag enables headless agent operation

**Documentation approach:**
- Starting from scratch allowed comprehensive architecture coverage
- Audience-specific sections (visitors, developers, operators) improved clarity
- Command walkthroughs with "What happens" sections highly effective
- Visual diagrams (ASCII architecture, workflow patterns) aid understanding

**Collaboration:**
- Codex authored AGENTS.md and application catalog
- GitHub Copilot rewrote README.md to wepppy standards
- Clear division of labor accelerated delivery

## Lessons Learned

**Apache-2.0 derivative works:**
- Proper attribution requires copyright notice updates (original + derivative)
- LICENSE and NOTICE files must be preserved verbatim
- README must clearly state origin, modifications, and license terms

**Agent orchestration patterns:**
- Handoff (synchronous) vs. Assign (asynchronous) vs. Send Message (communication) distinction critical
- Inbox watcher (PollingObserver) requires provider-specific idle patterns
- Terminal status detection fragility (regex-based) is a known risk

**Service tree integration:**
- `~/.wepppy/cao/` path convention aligns with wepppy infrastructure
- Editable install (`uv pip install -e`) essential for development workflow
- tmux ≥ 3.3 requirement must be documented clearly

## Future Work

**Immediate (doc janitor pilot):**
- Complete `scripts/doc_janitor.sh` implementation
- Define `docs/tooling/doc_toc_targets.txt`
- Manual testing before enabling cron

**Short-term enhancements:**
- Add test suite for Codex provider
- Refine status detection heuristics after live usage
- Create developer/reviewer/analyst agent profiles

**Long-term applications:**
- See `services/cao/cao-potential-applications.md` for 22 catalogued use cases
- Priority candidates: WEPP Run QA, Multi-Location Batch Processing, Service Health Monitoring

---

## Retrospective

**Duration:** ~4 hours (Codex initial integration) + ~2 hours (documentation rewrite) = 6 hours total

**Team:** Codex (infrastructure, initial docs) + GitHub Copilot (README rewrite, application catalog expansion)

**Outcome:** Production-ready CAO service integrated into wepppy with comprehensive documentation. Foundation established for future automation work packages.

**Files modified:**
- `services/cao/README.md` (created, ~850 lines)
- `services/cao/README.old.md` (backup)
- `services/cao/AGENTS.md` (Codex)
- `services/cao/cao-potential-applications.md` (expanded to 22 use cases)
- `services/cao/src/cli_agent_orchestrator/providers/codex.py` (Codex)
- `services/cao/src/cli_agent_orchestrator/flows/doc_janitor.yaml` (Codex)
- `services/cao/src/cli_agent_orchestrator/constants.py` (updated paths)

**Next work package:** Documentation Janitor pilot (script implementation and testing)
