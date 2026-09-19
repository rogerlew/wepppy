# Tracker

Completed on Forest, 2026-09-19 UTC. Starting revision: `1b4f9af72`.
Scope: cover-default propagation and
omitted kslast preservation. WEPP executable work deferred by operator.

- Contract ancestor `acc192323`; both independent reviewers approved before code edits.
- Both pre-fix regressions failed as expected: omitted 0.0001 became None;
  configured canopy 0.0 remained 0.4 in the emitted file.
- Bounded implementation: 10 landuse lines plus presence-gated existing parser block.
- Final focused suite: 286 passed; broad suite: 9,079 passed, 99 skipped.
- Independent source correctness review (`defaults_correctness`): pass, no findings;
  independent final acceptance and post-restore rerun pass; no unresolved findings.
- Forest fork `cover-defaults-validation-20260919`, job
  `763a90ea-0357-4f5c-8f4b-1e9578b0f6d2`: finished 2026-09-19 16:04:10 UTC.
- Candidate `b1e857765`; focused suite includes seven JSON/form transport cases.
- Normal Modify Landuse default propagation and complete prepared-input checks pass:
  455 hillslopes/1,065 OFEs, kslast0.0001 preserved after `{}` run submission.
- WEPP parent `56d90c88-bca6-4f2f-9f3c-074bcf1f003f`: all 15 jobs finished.
- Browser/download and canonical archive/restore pass; 2,734 model/state records
  retained exactly. See [evidence](artifacts/20260919_validation.md).
- Production deployment and source-project repair excluded.
