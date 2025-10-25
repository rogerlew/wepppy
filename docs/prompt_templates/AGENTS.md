# Prompt Templates Agent Guide

## Overview
- This directory stores reusable prompt scaffolds that codify repeatable workflows (module documentation, README authoring, migration plans, work packages).
- Treat templates as shared tooling: changes ripple across multiple repos and agents. Review the target workflow end-to-end before editing.

## Available Templates

### Documentation Templates
- `readme_authoring_template.md` — Standard structure for module/service README files
- `agents_authoring_template.md` — Guide for creating AGENTS.md files in subdirectories

### Workflow Templates
- `module_documentation_workflow.prompt.md` — Process for improving docstrings, type hints, and `.pyi` coverage

### Work Package Templates
- `package_template.md` — Structure for work package brief (scope, objectives, success criteria)
- `tracker_template.md` — Living document for tracking progress, decisions, and handoffs
- `prompt_template.md` — Standardized format for work package prompts with validation gates

See `docs/work-packages/README.md` for guidance on when and how to use work package templates.

## Using Templates
- Reference templates when a task aligns with the documented workflow. Example: use `module_documentation_workflow.prompt.md` whenever improving docstrings, type hints, and `.pyi` coverage together.
- Copy relevant sections into working notes or the active prompt; adapt details (paths, module names) while preserving required validation steps.
- If the existing templates do not fit, note gaps in your summary so maintainers can expand the catalog.

## Editing Guidelines
- Read the entire template plus related documentation (for example, `docs/prompt_templates/readme_authoring_template.md`) to confirm assumptions still hold.
- Keep instructions technology-agnostic when possible and avoid repository-specific jargon unless essential.
- Maintain ASCII characters only. Replace em dashes, smart quotes, and ellipses with ASCII equivalents to keep prompts portable.
- When guidance changes for a workflow, audit adjacent templates to ensure consistent messaging (for example, adjust README and module documentation prompts together if validation steps change).
- Cross-reference the root `AGENTS.md` when new conventions or tooling notes are introduced, rather than duplicating long explanations here.

## Validation
- After editing a template, sanity-check that any referenced commands exist (`wctl`, helper scripts, etc.).
- Preview diffs with `git diff` and ensure no unrelated prompts were modified.
- If templates instruct running tooling (stubgen, stubtest, pytest), confirm the commands are up to date with `wctl/README.md`.

## Getting Help
- Root guidance: `./AGENTS.md`
- Testing workflows: `tests/AGENTS.md`
- Front-end controllers: `wepppy/weppcloud/controllers_js/AGENTS.md`
- For new templates or large restructures, open a discussion in the repo before landing changes.
