# Preimplementation independent reviews

Reviewed 2026-09-16 03:30–03:35 UTC, before implementation or checkpoint commit.
Root authored amendments; three independent agents read without editing.

## Correctness / contract

Reviewer: `/root/report_contract_review` (reviewer role). Findings addressed:

- COR-I01: exact JSON shapes ambiguous. Specified all-duration design/inverse
  arrays, predictor array, nullable typed coverage/frequency/newer-attempt.
- COR-I02: zero-write/source-read wording exceeded currentness behavior.
  Preserved existing session/Redis read-through handling and bounded local
  provenance checks, while retaining no scientific/project file mutation.
  Explicit shared Unitizer preference actions remain supported.
- COR-I03: RedisPrep may create redisprep.dump if absent. Require existing
  dump before currentness; otherwise retain saved values with unknown
  currentness. Real-file absent-dump regression is mandatory.

Final post-fix confirmation: pass, COR-I01–COR-I03 resolved; no remaining
medium/high findings. Standalone ancestor commit may proceed.

## Security

Reviewer: `/root/report_security_review` (security_reviewer role).
Checkpoint pass, no medium/high findings. Two low refinements incorporated:
PFR-I-SEC-01 uses existing authorize with a local sanitized unexpected-error
boundary and no-store error tests. PFR-I-SEC-02 specifies hex32 attempt IDs,
open_local descriptor confinement, size/nonregular/symlink and cleanup tests.
Runtime review remains required and is not satisfied by this contract review.

## Dedicated intuitive UX

Reviewer: `/root/report_ux_review`, explicit dedicated end-user advocate brief.
Checkpoint pass, no medium/high findings. Optional UX-I01 replaces technical
currentness wording with “Could not check whether these results match the
current inputs.” UX-I02 explains current-page/displayed-unit CSV retains full
numeric precision. Both incorporated without new controls. Real browser,
keyboard/narrow and final implementation review remain required; no user-study
or accessibility certification is claimed.
