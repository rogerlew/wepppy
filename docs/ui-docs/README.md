# UI Documentation

The `ui-docs/` folder centralizes documentation for the web UI. Use these references when you need to understand controller behavior, styling expectations, or front-end workflows.

## Contents
- `control-ui-styling/` — Behavioral notes and styling guides for individual controls (for example, SBS controls, map panels).
- `ui-style-guide.md` — Core styling conventions and reusable snippets for controls, summary panes, and typography.
- `theme-system.md` — Complete VS Code theme integration reference: architecture, implementation, configurable mapping, and contribution guidelines.
- `cap-js-captcha-auth.md` — Cap.js CAPTCHA service wiring, floating prompt UX, and verification flow.
- Additional markdown files — Design decisions, migration plans, or retrospectives for UI modernization work.

## Usage Guidelines
- Keep control-specific walkthroughs near their subject under `control-ui-styling/`.
- Record reusable patterns in `ui-style-guide.md` so other controls can follow the same conventions.
- When a change spans multiple controls or requires coordination with back-end work, link to the relevant work package or mini package in `docs/`.
