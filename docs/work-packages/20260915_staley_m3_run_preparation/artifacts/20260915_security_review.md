# Security review — M3 Run preparation

## Metadata and triage

Date: 2026-09-15. Independent reviewer: source_boundary_review. Starting code
e8edf2030; contract ancestor e8c40adda precedes implementation. Scope:
run_preparation.py, production_soils.py callback, production.py hook/fingerprint
and accompanying tests. Impact high: explicit Run now invokes the existing
bounded reader, but introduces no URL/payload, privilege, service or queue.

## Findings and disposition

No medium/high implementation findings. Reviewer requested direct proof of
automatic promotion followed by calculation failure and retry. The expanded
fresh-basin test now preserves a genuine prior accepted result, retains the
promoted pointer and proves retry does not acquire again.

## Surface checks

- Auth/session/CSRF/endpoints remain unchanged; live normal browser mutation
  returned the existing job receipt and used normal authorization.
- No new secret handling or credential values. Prior owner risk acceptance is
  unchanged; this task neither requires nor performs credential rotation.
- Strict local metadata parsing distinguishes absent, valid empty/legacy,
  populated and hostile/dangling-link states. Hostile state cannot invoke egress.
- Only the existing fixed-endpoint, byte/time/process-bounded reader is invoked;
  no redirects, broad retries, full-object downloads or soil/cache rebuilding.
- Original absent-pointer/attempt/project authority is checked before delivery
  and inside real locked promotion; competing pointer and source changes fail.
- Rebase excludes only module pointer/receipt assets; preserves raw cache/WAL,
  spatial keys, owner settings, source files and all unrelated inputs. Actual
  promoted pointer bytes must match the receipt candidate hash.
- Network stays outside NoDb locks. Later failure retains committed pointer;
  it does not roll back concurrent work or replace accepted results.
- Receipts, transcripts, intermediates and failure evidence use existing visible
  module paths and normal archive/browse coverage; no hidden artifact exception.
- No new exception swallowing, executable serialization or dependency introduced.

## Validation and verdict

Independent code review approved; unit and real filesystem/NoDb activation tests
exercise both valid and rejected states. See [live evidence](20260915_live_acceptance.md)
for ordinary worker execution, independent arithmetic and 2,648 unchanged
protected files. Full repository regression result is recorded in the tracker.

Gate: pass for this bounded development fix, zero unresolved medium/high
findings. Not production rollout authority. Primary agent retains responsibility
for final regression and closeout evidence; correctness review is separate.
