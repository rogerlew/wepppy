# Tracker

Starting revision: `1b4f9af72`. Active scope: cover-default propagation and
omitted kslast preservation. WEPP executable work deferred by operator.

- Contract ancestor `acc192323`; both independent reviewers approved before code edits.
- Both pre-fix regressions failed as expected: omitted 0.0001 became None;
  configured canopy 0.0 remained 0.4 in the emitted file.
- Bounded implementation: 10 landuse lines plus presence-gated existing parser block.
- First focused run: 230 passed; expanded direct build/modify and filesystem
  failure/retry checks: 3 passed. Broad and expanded focused runs in progress.
- Independent source correctness review (`defaults_correctness`): pass, no findings;
  environment acceptance remains pending.
- Forest fork `cover-defaults-validation-20260919`, job
  `763a90ea-0357-4f5c-8f4b-1e9578b0f6d2`: finished 2026-09-19 16:04:10 UTC.
- Production deployment and source-project repair excluded.
