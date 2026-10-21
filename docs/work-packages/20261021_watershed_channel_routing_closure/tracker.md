# Watershed channel routing closure tracker

**Started / closed**: 2026-10-21
**Phase**: Closed; investigation complete, model defect open
**Security impact**: none; dedicated security review not required

## Progress

- [x] M1: Source/provenance, workbook, boundaries and controlled/project inputs.
- [x] M2: Gated native observations and exact three-way scientific parity.
- [x] M3: Native PASS readback, publication ledger and diagnostic controls.
- [x] M4: Independent correctness and source QA; findings and retained evidence.

## Decisions and outcome

Roger authorized observation only. The confirmed first failing boundary is
schema-2 PASS calendar selection: a synthetic day 366 is consumed as the following
year's first day. See [findings](artifacts/findings.md#confirmed-defect-schema-2-calendar-selection).
Nine full-period cases pass exact parity, including the 28-hillslope real project.
The 160,345-record channel ledger validates publication arithmetic, not physical
domain conservation. COR-01 remains open for separate authorization; no simulation
correction, release, vendoring, deployment or live-run mutation occurred.

Ayush did not supply the original decks. Workbook accounting is a screen only.
The fixture, first real project and impoundment failures remain unresolved;
positive tile, variable width, schema 1, centurial calendars and full-domain
storage are outside demonstrated coverage. Failed attempts remain retained.

## Validation and evidence

- [Case matrix](artifacts/case_matrix.csv), [parity](artifacts/parity.json),
  [provenance](artifacts/provenance.json), [commands](artifacts/commands.md).
- [Residual summary](artifacts/residual_summary.csv),
  [controls](artifacts/diagnostic_controls.json),
  [large-ledger receipts](artifacts/retained_ledgers.json).
- [Independent correctness review](artifacts/correctness_review.md): pass for
  investigation closure; source QA and Fortitude pass.
- Native targeted pytest: 13 passed; FPM router contract passed.
- Package documentation lint, spelling preview, root size and scoped diff checks.

## Handoff

The [completed ExecPlan](prompts/completed/watershed_channel_routing_closure_execplan.md)
records decisions and limitations. The separately proposed next task is calendar-key
reader selection plus non-leap/final-day/schema compatibility validation; this
package does not authorize or implement that correction.
