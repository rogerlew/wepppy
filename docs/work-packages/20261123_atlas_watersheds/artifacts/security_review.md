# Run Atlas security review

Independent security reviewer, 2026-11-23. Reviewed the implementation on
`atlas/watershed-snapshot` against the [contract decision](20261123_contract_decision.md).

## Scope and disposition

High impact because the public landing and four JSON aliases serve exact
watershed locations for private as well as public projects. The operator
authorized that location scope. Project authorization remains in force.

The compiler and readers validate coordinates and project each record onto
the same five public fields. Older snapshots go through the projection before
either HTML or JSON serialization. ID-derived names, map labels, and activity
fields are absent. The aliases send no-store responses. The security reviewer
identified relative access order in legacy snapshots during contract review.
Sorting by the projected fields resolves that finding even at shared coordinates.

## Verdict

Passed independent implementation review with no unresolved findings.
Compiler and route tests cover populated, empty, malformed, polar and older
snapshots, including malformed fields and extra private data. The tests read
the generated JSON and the rendered page and exercise all four aliases.
