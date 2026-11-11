# Bootstrap Git input contract

Status: approved pickle restriction, 2026-11-10 Pacific; implementation
conformance and deployment pending.

## Pickle artifact admission

Bootstrap MUST reject added or modified paths whose final suffix is `.pkl` or
`.pickle`, case-insensitively, in every introduced commit and every allowed
Bootstrap directory. Existing rejection of renames and copies remains unchanged.
Reject at shared path admission before blob loading, parser work, or push-log
append. The rejection must identify the path and explain that pickle files are
not allowed. Existing deletion, ref, size, NUL, symlink, submodule, WEPP parser,
and allowed-input behavior remains unchanged.

This is a suffix restriction, not a content scanner or a general ban on internal
serialization. NUL-free pickle bytes receive the same rejection as binary
pickle. No converter, fallback parser, feature flag, or data migration is part
of this contract. Restoring interactive pickle loading requires a new approved
security decision.

Existing project pickle files remain visible and downloadable as original bytes
under the [browse filesystem contract](browse-filesystem-contract.md#pickle-artifacts).
Bootstrap admission does not authorize deleting or hiding legacy artifacts.

## Rationale and compatibility

Python pickle loading can execute code. A Git blob's lack of NUL bytes does not
establish safety for deserialization. Rejecting these suffixes and removing
their interactive readers closes the confirmed artifact path while preserving
authorized access to legacy bytes. Internal application-owned serialization is
outside this rule; evidence of a project-controlled consumer requires separate
assessment.

## Required regression evidence

Exercise the real pre-receive hook with temporary Git pushes containing NUL-free
inert bytes under both allowed directory prefixes, both suffixes, and mixed-case
variants. Rejected commits must not enter the push log or advance the receiving
ref. Retain an allowed text/WEPP input control. Do not execute pickle payloads to
prove rejection.

The 2026-11-10 restriction uses focused Bootstrap, browse/files, D-Tale, stub,
documentation and source-search checks plus a separately authorized scoped
deployment smoke. The operator explicitly waived full Python and frontend
suites for this bounded change; focused local evidence is not deployment proof.
