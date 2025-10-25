# Work Packages

This directory groups long-running initiatives into self-contained "work packages". Each package bundles the brief, tracker, prompts, and supporting notes so agents can jump in without hunting across the repository.

**When to create a work package:** Multi-step features, high-risk migrations, cross-cutting concerns, or any initiative requiring coordination across multiple PRs or agents. See `AGENTS.md` ("Creating a Work Package") for detailed criteria.

**Quick links:**
- [`PROJECT_TRACKER.md`](../../PROJECT_TRACKER.md) (root) — Kanban board showing active/backlog/completed packages
- [`docs/prompt_templates/`](../prompt_templates/) — Templates for package.md, tracker.md, and prompts
- [`docs/god-tier-prompting-strategy.md`](../god-tier-prompting-strategy.md) — Guide to writing effective prompts for work packages

## Naming convention
- Folder name: `YYYYMMDD_slug` using **Pacific timezone** (e.g., `20251024_nodb_validation`)
- Use the date the package started (or was formally scoped)
- Keep the slug short and descriptive (e.g., `statusstream_cleanup`, `nodb_docs_refresh`)
- If multiple packages start the same day, append a letter: `20251024_slug_a`, `20251024_slug_b`

## Standard layout
```
YYYYMMDD_slug/
├── package.md          # High-level brief: scope, goals, contacts, success criteria
├── tracker.md          # Living status log: tasks, decisions, risks, next steps, communication between agents
├── prompts/
│   ├── active/         # Prompts/checklists/scripts still in use
│   └── completed/      # Retired prompts with outcomes or notes
├── notes/              # Optional scratch docs, meeting minutes, research spikes
└── artifacts/          # Optional exports, diagrams, screenshots
```

Feel free to omit `notes/` or `artifacts/` if the package stays simple.

## Workflow guidelines
1. Create a new package when a feature, migration, or documentation effort will span multiple PRs or agents or is high risk.
2. Fill in `package.md` with the problem statement, scope, stakeholders, and exit criteria (use template from `docs/prompt_templates/package_template.md`).
3. Track all actions in `tracker.md` (Kanban list, decision log, verification checklist, etc.) — use template from `docs/prompt_templates/tracker_template.md`.
4. Drop prompts or automation scripts in `prompts/active/`; when they finish, move them to `prompts/completed/` with a brief outcome summary (inline at top of file or as `<prompt>_outcome.md`).
5. **Update `PROJECT_TRACKER.md`** (root) when starting, progressing, or closing packages so other agents can discover active work.
6. When the initiative ends, update `package.md` with the closure date and highlight deliverables or follow-ups.

Keeping everything inside one folder makes handoffs easier and lets us archive the package without losing the history.

## Agent Communication Protocol

When handing off work between agents or sessions, follow these conventions in `tracker.md`:

**Decision Log:**
```markdown
## Decisions
- **YYYY-MM-DD** – Brief decision summary with rationale
```

**Progress Notes:**
```markdown
## Notes – YYYY-MM-DD
- What was completed this session
- What's blocked and why
- Next steps for the following agent
```

**Task Board Updates:**
- Move tasks to "In Progress" when starting work
- Mark `[x]` immediately upon completion
- Add blocking issues to "Blocked" section with context

Agents should timestamp all entries so others can reconstruct the narrative chronologically.

## Prompt Lifecycle

**Active Prompts** (`prompts/active/`):
- Reusable instructions, checklists, or automation scripts still in use
- Keep these while the work package is open

**Completed Prompts** (`prompts/completed/`):
- Prompts that have served their purpose
- **Must include outcome:** Add a brief summary at the top of the file or create `<prompt_name>_outcome.md` explaining:
  - What was accomplished
  - Any deviations from the original plan
  - Lessons learned or issues encountered
  - Links to relevant commits/PRs

**When to archive:** Move prompts when the subtask is complete, not at package closure. This keeps `active/` focused on current work.

## Closing and Archiving Packages

When a work package is complete:

1. **Update package.md:**
   - Change status to "Closed YYYY-MM-DD"
   - Summarize deliverables (what was shipped)
   - Note any follow-up work or spin-off packages
   - Link to key commits/PRs if applicable

2. **Clean up prompts:**
   - Move all prompts from `active/` to `completed/` with outcomes
   - Remove any temporary or redundant files

3. **Update PROJECT_TRACKER.md:**
   - Move package from "In Progress" to "Done"
   - Update any related packages if this was a dependency

4. **Artifacts and notes:**
   - Keep essential artifacts (diagrams, screenshots, test results)
   - Remove temporary files (traces, large debugging dumps)
   - Consolidate notes if valuable, or remove if redundant

**Do not delete closed packages.** They serve as historical reference for similar future work. If the directory grows unwieldy (>50 packages), consider moving packages older than 1 year to `docs/work-packages/archive/YYYY/`.

## Referencing Work Packages

When linking to a work package from other documentation:

```markdown
See [Work Package: StatusStream Cleanup](docs/work-packages/20251023_statusstream_cleanup/package.md)
```

When one package depends on or relates to another:

```markdown
## Related Packages
- **Depends on:** [20251023_statusstream_cleanup](../20251023_statusstream_cleanup/package.md)
- **Related:** [20251023_frontend_integration](../20251023_frontend_integration/package.md)
```

## CI and Testing Context

Work packages should align with the standard development workflow:

**Development cycle:**
1. Implement on host with `docker-compose.dev.yml`
2. Write and run comprehensive tests as part of development (`wctl run-pytest`, `wctl run-npm test`)
3. Deploy to forest1 (test production server on homelab) for select user testing
4. Address bugs found in test production
5. Deploy to production when stable

**Testing requirements:**
- All code changes must include tests
- Run full test suite before marking package as complete: `wctl run-pytest tests --maxfail=1`
- Frontend changes require lint + test: `wctl run-npm lint && wctl run-npm test`
- Document any new test fixtures or patterns in package artifacts

## Size and Scope Guidelines

**Ideal package characteristics:**
- **Small and focused:** Aim for completion within 1-4 weeks
- **Atomic deliverables:** Each task should be independently verifiable
- **Clear boundaries:** Well-defined scope that doesn't creep into unrelated areas

**When to split a package:**
- Initiative will take >6 weeks
- Natural breakpoints emerge (e.g., backend vs. frontend work)
- Multiple independent features that could ship separately

**When to merge packages:**
- Significant overlap in affected code
- Strong coupling between two initiatives
- One package is blocked waiting for the other

**Too small for a package:**
- Single-file bug fixes
- Straightforward feature additions (<100 LOC)
- Documentation typos or minor updates
- Changes that complete in a single focused session

When in doubt, create the package — the overhead is minimal and the structure helps with handoffs.

## Agent Collaboration Principles

**Stumbling is a system failure, not an agent failure.** When you encounter:
- Unclear documentation
- Missing context
- Ambiguous requirements
- Outdated guidance

**Take initiative:**
1. Fix the documentation immediately (you have authority to edit all .md files)
2. Note the fix in `tracker.md` so others know what was unclear
3. If uncertain, ask for human guidance before proceeding
4. Update templates if the gap is structural

**Feedback loops:**
- Agents are encouraged to suggest improvements to processes, tooling, or documentation
- Use tracker.md decision logs to capture "why" behind non-obvious choices
- Reference `docs/god-tier-prompting-strategy.md` when crafting prompts for complex work
- When a work package uncovers systemic issues, create a follow-up package to address them

The goal is continuous improvement through collaborative evolution. Every agent interaction should leave the system slightly better than they found it.
