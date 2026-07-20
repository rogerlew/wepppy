# REM-01 Security Scope Review Disposition

**Date**: 2026-07-20
**Disposition owner**: Codex
**Final gate**: Pass for standalone docs-only ancestor

## Disposition

| Finding | Severity | Disposition | Evidence |
| --- | --- | --- | --- |
| Report run access absent | High | Accepted and fixed | Amendment/register/contract require retained CAP plus new canonical run access and Dev/Root before report data read. |
| Additive boundary evidence incomplete | Medium | Accepted and fixed | ExecPlan names RQ JWT scope/run-access and Flask CAP/run-access negative tests with domain non-entry. |
| Response-shape freeze conflict | Medium | Accepted and fixed | Only authorized-flow response shapes are frozen; canonical denial contracts are permitted. |
| Security/package status stale | Medium | Accepted and fixed | Package is partial/amendment-ratifying; security checklist remains pending. |
| Register exact boundary mismatch | Medium | Accepted and fixed | Register separates RQ role-only gates from report run-access-plus-role gates. |
| Feature-spec overbreadth | Medium | Accepted and fixed | Rule is limited to publication-embargo routes registered by accepted contracts and applicable additive boundaries. |
| Test files/matrix incomplete | Medium | Accepted and fixed | Both exact test files, focused command, role matrix, and additive negative cases are named. |
| Living docs contradicted amendment | Medium | Accepted and fixed | ExecPlan discovery, tracker, security metadata, package triage, and watch list now align. |
| Contract decision grouped report as role-only | Medium | Accepted and fixed | Decision separates existing RQ JWT/run access from retained report CAP and new report run access. |
| Authorized-flow wording | Low | Accepted and fixed | Contract decision now qualifies the RQ response-behavior freeze. |

No finding was rejected or deferred. Both independent reviewers issued fresh
approval after the final corrections, with zero unresolved high or medium
findings. Production route changes may begin only after this complete docs-only
set is committed as the second standalone ancestor.
