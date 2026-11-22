# Pure controls render test refactor

**Status** Closed on 2026-11-22 UTC  
**Started** 2026-11-22 04:57 UTC

## Scope and objectives

Isolate cases that modify Jinja state in `tests/weppcloud/routes/test_pure_controls_render.py`. Consolidate repeated setup while preserving the existing test entry point, cases, markers, and rendered HTML assertions. Validation is scoped to this module.

## Complexity budget

Reuse pytest, Jinja, and the existing Docker-backed test wrapper. Use fresh environments for mutation cases and small local helpers. Compare collection and runtime with the baseline. The package requires no infrastructure, dependency, or production changes.

## Review gates

Security impact is none because the package changes test setup only. A dedicated security review and parameterization ADR are unnecessary. Existing assertions continue to inspect rendered HTML and checked-in sources. The refactor introduces no generated artifact workflow.

## Success criteria

- Cases that modify Jinja state receive fresh settings and context data.
- The focused pytest command collects the same node IDs and passes.
- Keep the execution plan and validation results with the package.

All 299 focused cases passed with matching node IDs. The seven reordered cases
passed. [Tracker](tracker.md)
