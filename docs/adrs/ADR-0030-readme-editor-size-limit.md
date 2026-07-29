# ADR-0030: README Editor 1 MiB Size Limit

Status: Accepted

Date: 2026-07-28

Review Date: 2026-10-28

## Context

The run README preview and save routes previously accepted Markdown up to the
proxy-wide request limit. JSON buffering, sandboxed Jinja rendering, Markdown
conversion, filesystem writes, and `fsync` made that generic limit
disproportionately expensive for short project notes.

## Decision

Limit a run `README.md`, expanded Markdown, and rendered HTML to 1,048,576
UTF-8 bytes. Limit the JSON request envelope to 1,052,672 bytes, allowing 4 KiB
for JSON keys and encoding around a maximum README. Reject oversized inputs
with HTTP 413 before JSON parsing, rendering, or writing.

## Decision Provenance

Decision Venue: Codex operator execution of SURF-09, 2026-07-28 UTC

Participants Present: WEPPcloud operator, Codex, independent security reviewer

Decision Owner(s): WEPPcloud operator

Implementer(s): Codex

## Change Summary

| Parameter | Previous | Accepted |
| --- | --- | --- |
| README-specific size limit | Proxy-wide request limit only | 1 MiB UTF-8 |
| README JSON envelope | Proxy-wide request limit only | 1 MiB + 4 KiB |

## Rationale

One MiB is ample for project notes while bounding per-request memory, Markdown
rendering, disk, and lock-hold time. Four KiB accommodates the small JSON
envelope without allowing the generic proxy cap. Limits are byte-based so
multibyte text has the same storage and processing ceiling.

## Alternatives Considered

1. Retain the proxy-wide limit - rejected because it permits expensive
   run-owner requests far beyond the intended project-note use.
2. Use 256 KiB - rejected as unnecessarily restrictive for detailed run notes.
3. Use character count - rejected because it does not bound UTF-8 storage.

## Consequences

Existing oversized run READMEs must be reduced outside the editor before the
viewer or editor can render them. Preview and save return HTTP 413 at the same
boundary.

## Evidence

- `docs/work-packages/20260728_pure_ui_readme_editor_contract/`
- Boundary and over-limit route/render regression tests in
  `tests/weppcloud/routes/test_readme_md.py`.

## Risk and Rollback Notes

Monitor legitimate HTTP 413 reports. If real project notes require more space,
revise this ADR with measured examples before increasing the threshold. A
rollback removes the README-specific checks but restores the documented
resource-exhaustion exposure.

## Implementation Notes

Validate the HTTP envelope before JSON parsing, existing files before reading,
in-memory Markdown before preview rendering or atomic writing, incrementally
generated Jinja output, and final HTML. README templates accept only literal
Markdown plus variable, attribute, or constant-key interpolation. Filters,
calls, control structures, and operators are rejected before evaluation so a
compact expression cannot allocate an unbounded intermediate value.
