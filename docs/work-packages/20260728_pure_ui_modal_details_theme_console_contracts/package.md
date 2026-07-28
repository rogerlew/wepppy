# SHR-04B Pure UI Modal, Details, Theme, and Console Contracts

**Status**: Closed 2026-07-28 UTC
**Package ID**: SHR-04B
**Security impact**: `none` for tests/docs; re-triage any production repair

## Purpose

Verify the shared Pure UI behavior that opens and closes modals, dismisses
details menus, persists interface themes, reads console configuration, and
renders shared console structure. The package proves these producers remain
safe when scripts are loaded more than once and retain accessible, stable
consumer hooks.

## Scope

- `controllers_js/modal.js`, including open/close/toggle, focus, Escape, focus
  trapping, dismiss targets, body state, and duplicate loading;
- `controllers_js/details_menu.js`, including outside-click, Escape, retained
  menu interaction, public close, and duplicate loading;
- `controllers_js/theme.js` and generated `static/js/theme.js`, including
  storage, root/select synchronization, invalid/default values, events, storage
  errors, and duplicate loading;
- `static/js/console_utils.js`, including hidden-node precedence, container
  fallback, boolean normalization, absent nodes, and duplicate loading;
- `templates/shared/console_macros.htm`, modal producers, theme selector, and
  representative console consumers.

## Exclusions

Unit conversion and preference persistence remain SHR-05. Console-specific
transport, queue lifecycle, authorization, and mutations remain with their
SURF packages. This package does not redesign shared APIs or infer new behavior
from existing code.

## Acceptance

Direct Jest tests cover each shared behavior and duplicate-load boundary.
Direct Jinja tests cover console macros and representative modal/theme
producers. Confirmed mismatches receive the smallest contract-compatible
repair. Focused and full frontend tests, generated-bundle verification,
rendered-template tests, documentation lint, and `git diff --check` pass.

## Outcome

Direct tests confirmed and repaired duplicate initialization in the modal,
details-menu, and theme producers. A rendered regression also confirmed and
repaired dropped caller content in `table_page`. Console configuration and the
remaining console/modal/theme markup conformed without repair.
