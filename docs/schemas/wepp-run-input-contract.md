# WEPP run input contract

## kslast omission

Accepted and Forest conformance validated 2026-09-19; production rollout is
separate. This bounded contract
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

## Single User-Defined Builder exception (2026-09-25)

SUDI-01, [Single User-Defined inputs](single-user-defined-inputs-contract.md), defines the bounded creation-time exception to ordinary
Builder Disturbed support and adds independent mode5 landuse/soil uploads.
Checked projects exclude Disturbed/SBS and their dependent features across UI,
activation and direct execution, and disable buffer geometry and management
overrides. Unchecked/legacy behavior remains unchanged. The checkbox does not
select an input mode. Preserve the option through capability refresh and preserve
accepted sources across rebuilds/mode switches. Compatible cover/soil modifiers
retain their existing precedence on generated copies; all non-buffer OFEs receive
the selected single source on a mode5 build. Subsequent explicit class edits
and global mappings retain existing modification contracts and may replace
assignments; rebuilding mode5 restores uniform source assignments. These edits
do not initialize Disturbed or apply its lookup transforms. Existing authorization, response, persistence and
controller invariants remain in force. This explicit exception governs where
earlier unconditional Disturbed statements conflict; no other defaults change.
Implementation conformance is pending the SUDI-01 checkpoint and validation.
