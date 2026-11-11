# Correctness review - Safe traceback sanitization

**Status**: Pending implementation and independent review
**Reviewer**: Unassigned
**Date opened**: 2026-11-11 UTC

## User Outcome

Users/operators retain the existing traceback fields and useful diagnostic
frames, absolute paths, types, lines and correlation IDs. Secret filtering must
not convert an expected error into a different status/schema or remove recovery
context unrelated to credentials.

## Required Checks

- [ ] Redis prerequisite checkpoint is recorded.
- [ ] Existing endpoints neither gain nor lose traceback fields incidentally.
- [ ] One representation is used regardless of account/run role while existing
      endpoint authorization remains unchanged.
- [ ] Frames, paths, line/function, type, safe message and chains remain useful.
- [ ] Configured absent/readable/unreadable and legacy-env states match contract.
- [ ] Each application/worker adapter selects only locally consumed source
      metadata; downstream-only and stale Kubernetes paths are not opened.
- [ ] The comma-delimited authorization key ring contributes every constituent
      key without changing the authentication parser or secret lifecycle.
- [ ] ExceptionGroup/notes/causes are bounded without silently dropping the
      primary exception.
- [ ] Error/status codes, `error_id`, RQ state and frontend panels remain compatible.
- [ ] No normal successful path opens secret files.
- [ ] Production-equivalent `0444` mounted-file tests run as the non-root
      container identity, observe replacement on the next exception and retain
      useful output in captured container stdout/stderr.
- [ ] Focused and exact full-suite receipts correspond to the reviewed revision.

## Findings and Verdict

Populate severity, exact state/sink, evidence, required action and disposition.
**Gate status: PENDING/FAIL** until implementation, direct sink readback and full
regression evidence pass.
