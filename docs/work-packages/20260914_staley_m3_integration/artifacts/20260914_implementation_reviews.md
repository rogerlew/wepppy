# Isolated implementation review evidence

Scope: post-checkpoint `89d673c38` soil policy/snapshot/prepared-source adapter.
These reviews do not approve unfinished M3 runtime integration or deployment.

## Correctness review

Independent `source_contract_review` found three defects in the first adapter:
read-only SQLite created shared sidecars for clean WAL databases; JSON encoding
rejected nonfinite source values before scientific policy; inspection CSVs lost
SQL NULL/empty distinctions and could change replayed duplicate-ID validity.
Corrections use bounded retained main/WAL copies, tagged nonfinite logical
hashing and authoritative raw SQLite replay. Source inspection CSV keys are
canonicalized separately without changing original typed logical identities.
Final recheck closed all three findings; 72 production/offline soil tests passed
in the reviewer's run. No unresolved medium/high correctness findings remain
within that bounded review.

## Security and source-isolation review

Independent `source_boundary_review` closed all reported medium/high findings:

- Reject rollback journals: real uncommitted disk-spill data were otherwise
  admitted as a committed snapshot. Reviewer independently confirmed rejection
  and that the original writer could still roll back.
- Copy through no-follow descriptors with identity checks. Reviewer reproduced
  final-component and parent-directory symlink swaps and confirmed no outside
  bytes were retained in failed artifacts after correction.
- Parse and hash the same bounded metadata bytes; retain immutable original
  MUKEY/mask copies before decoding.
- Admit declared inches, reject meters for original THICK conversion.
- Enforce streaming hash/copy ceilings, not only initial stat limits.
- Recheck absent dependencies, original identities and raster companion sets.

No live project was accessed by the reviewers. Runtime finalization must consume
returned dependency/stat/logical identities. Full workflow/archive evidence and
final package security approval remain pending.

## Validation so far

Focused production soil suite: 37 passed, including real WAL/rollback writers,
source appearance, symlink swap, nonfinite values, NULL/empty replay and
primary/fallback/absent composition. Prior combined soil/integration gate:
120 passed. Local M1/rainfall gate: 79 passed with real WBT full, partial,
disjoint and raw/common-T-difference cases. Stub completeness passes.
The full Python sweep passed: 8,498 passed, 103 skipped. Latest combined focused
gate: 153 passed; final M1 reader correction: 55 passed. See
[validation](20260914_implementation_validation.md) for collection timing.

## M1 common-support reader review

The independent correctness reviewer found a counts-preserving basin-domain
swap that the new reader did not reject. Require exact mask-domain equality
with the raw WBT intersection domain, in addition to counts and common T.
The real-WBT partial-support test now swaps an excluded interior cell and an
exterior cell, repins hashes, and verifies rejection. Independent real-binary
readback confirmed rejection and closed the finding. A nonuniform independent
probe confirmed that common-support F/S are recomputed; the persisted partial
test now includes excluded outliers. No unresolved medium/high findings remain
in this bounded M1 review. Production wiring remains excluded.

Code-quality note: the existing M1 builder retains its v1 sequencing and adds
an explicit opt-in branch, while new policy/snapshot/reader concerns live in
separate modules. This modest builder growth preserves offline behavior during
the staged integration; it is not a speculative generalization of other models.

## Execution incident

A broad process diagnostic exposed a Redis credential in tool output. The
value is not retained here or repeated; the owner was notified to rotate it.
No credential rotation or service mutation was performed by this task.
Future process checks must select only PID, elapsed time and command name,
never unrestricted arguments.
