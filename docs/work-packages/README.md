# Work Packages

This directory groups long-running initiatives into self-contained "work packages". Each package bundles the brief, tracker, prompts, and supporting notes so agents can jump in without hunting across the repository.

## Naming convention
- Folder name: `YYYYMMDD_slug`
- Use the date the package started (or was formally scoped).
- Keep the slug short and descriptive (e.g., `statusstream_cleanup`, `nodb_docs_refresh`).

## Standard layout
```
YYYYMMDD_slug/
├── package.md          # High-level brief: scope, goals, contacts, success criteria
├── tracker.md          # Living status log: tasks, decisions, risks, next steps
├── prompts/
│   ├── active/         # Prompts/checklists/scripts still in use
│   └── completed/      # Retired prompts with outcomes or notes
├── notes/              # Optional scratch docs, meeting minutes, research spikes
└── artifacts/          # Optional exports, diagrams, screenshots
```

Feel free to omit `notes/` or `artifacts/` if the package stays simple.

## Workflow guidelines
1. Create a new package when a feature, migration, or documentation effort will span multiple PRs or agents.
2. Fill in `package.md` with the problem statement, scope, stakeholders, and exit criteria.
3. Track day-to-day work in `tracker.md` (Kanban list, decision log, verification checklist, etc.).
4. Drop prompts or automation scripts in `prompts/active/`; when they finish, move them to `prompts/completed/` with a brief outcome summary.
5. When the initiative ends, update `package.md` with the closure date and highlight deliverables or follow-ups.

Keeping everything inside one folder makes handoffs easier and lets us archive the package without losing the history.
