# SURF-12 Pure UI Report Shell and Readonly Contract

**Status**: Closed
**Package ID**: SURF-12
**Security impact**: `low` for presentation-only audit; re-triage any repair

## Purpose

Verify the two generic WEPPcloud report-shell producers and their finite report
consumers. The audit proves report titles/content, run identity, persisted
readonly/public state, navigation, shared modals, command bar, unit hooks, and
script ordering render consistently without taking ownership of domain output
logic.

## Scope

- `templates/reports/_base_report.htm`;
- legacy `templates/reports/_page_container.htm`;
- exact title/content, run/config/name/scenario, projection, modified time,
  readonly/public checked state, and editable-target hooks;
- report navigation, PUP-sensitive links/interception, command bar, shared
  modals, unit hooks, CSV/copy/sort helpers, and stale-bundle metadata;
- all direct consumers in Ash, Debris Flow, Geneva, RHEM, Storm Event Analyzer,
  Observed, and WEPP reports; and
- route context evidence for those finite consumers.

## Concise Intent Contract

The report shell presents current run state and delegates mutations to the
existing Project controller. It must render stable `data-project-*` hooks,
reflect `current_ron.readonly` and `current_ron.public`, and mark name/scenario
inputs with `disable-readonly` so Project applies persisted readonly state.
It must not introduce a second mutation implementation.

`_base_report.htm` is the Pure full-width shell. `_page_container.htm` remains
a supported legacy shell for its five current consumers; SURF-12 verifies it
but does not migrate or redesign it. Both shells preserve report content,
shared unit/modals, command-bar access, and stale-controller detection.

## Exclusions

Domain report calculations, tables, maps, queries, and CSV payloads remain with
their DOM/SURF owners. Project mutation parsing/persistence remains DOM-02,
unit preference round trips remain SHR-05, Geneva interaction remains SURF-11,
and authentication/authorization changes are outside this presentation-only
package.

## Acceptance

Direct Jinja tests cover both shell producers, readonly and absent-state
rendering, PUP behavior, scripts/modals, and every direct consumer's inheritance
and content block. Existing route tests establish finite context wiring.
Confirmed mismatches receive a failing regression and the smallest compatible
repair. Focused render/route tests, frontend lint/test, documentation lint, and
`git diff --check` pass.

## Outcome

The two producers conform to the ratified contract. Direct regressions cover
run and absent-run headers, persisted readonly/public state, Project hooks,
PUP request scoping, shared runtime/modal targets, and the complete
14-Pure/5-legacy direct-consumer inventory. No production repair was required.
