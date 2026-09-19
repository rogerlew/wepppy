# WEPP run input contract

## kslast omission

Accepted 2026-09-19; implementation conformance pending. This bounded contract
covers the shared WEPP parser used by JSON/form run submissions and direct
`Wepp.parse_inputs` callers. Other fields retain their current contracts.

An absent `kslast` key must preserve the saved conductivity override, including
zero, None, or a legacy absent attribute (whose property reads None). Omission
must not synthesize a new value. Explicit null, empty string, or existing
case-insensitive none-prefixed strings clear the override. Existing numeric
conversion and list/tuple/set first-nonempty selection remain unchanged;
explicit empty collections retain their clearing behavior. Other unrecognized
values retain the existing parser behavior, not a new validation policy.

Rationale: partial API submissions must not silently change an unrelated soil
parameter. Clients clearing this parameter must submit it explicitly. Initial
saturation, compiler selection, pass families, units and defaults are unchanged.
The existing NoDb lock/persistence and rq-response contracts still apply.

Evidence must exercise the real parser through its locked facade, reload durable
state and read prepared soil files. Retained artifacts use existing `wepp.nodb`,
`soils/hill_*.mofe.sol`, `wepp/runs/p*.sol`, logs and output paths, normal project
browse/download and canonical archive/restore. Failure is not completion; no
new status mechanism or error translation is introduced.
