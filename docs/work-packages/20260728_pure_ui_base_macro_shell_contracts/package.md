# SHR-04A Pure UI Base and Macro Shell Contracts

**Status**: Closed 2026-07-28 UTC
**Package ID**: SHR-04A
**Security impact**: `none` for test/documentation-only audit; re-triage any
production repair

## Purpose

Verify that `base_pure.htm` and `controls/_pure_macros.html` render stable,
accessible identities and state for every Pure UI consumer. The completed DOM
packages provide real consumer evidence, including DOM-12's prior
`checked`/`selected` mismatch.

## Scope

- base document metadata, body state, extension blocks, and script ordering;
- control/card shells and standard status, summary, stacktrace, and job-hint
  regions;
- field, choice, tab, table, slot, and color-scale macros;
- exact `id`, submitted `name`, value, selected/checked, disabled, required,
  nullable, hidden, ARIA, and absent-state rendering; and
- representative completed-DOM consumers.

## Exclusions

Transport/session behavior is SHR-02, job lifecycle is SHR-03A, modal/theme/
console behavior is SHR-04B, and unit conversion is SHR-05. This package does
not redesign the macros, introduce a registry/generator, or change defaults
without an operator-approved contract decision.

## Acceptance

Direct Jinja tests cover the producer matrix and representative real consumers.
Any mismatch receives a failing regression and the smallest compatible repair.
Focused render tests, frontend lint/test, documentation lint, and
`git diff --check` pass.

## Outcome

Direct producer coverage now proves the base document, control lifecycle
regions, field/choice state, cards, tabs, tables, dynamic slots, and color-scale
targets. The complete real-consumer render suite remains green. No production
mismatch or repair was required.
