# Disturbed lookup live runbook refactor

## Scope and acceptance

Faithfully extract the workflow in `tests/nodb/mods/disturbed/live_e2e/runbook.py`. Keep the public entry point, request sequence, comparison rules, failure phases, and JSON and Markdown evidence. Exercise the entry point with scoped pytest and compare generated evidence to the baseline. Integrate into local master and hold publication.

## Complexity budget

Use existing Python and pytest dependencies. Keep changes inside the test harness and work package. Security impact is low because the existing authentication and client contracts carry over without modification.

See the [tracker](tracker.md) for validation.
