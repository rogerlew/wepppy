# Validation Evidence

## Incident reproduction

The tracked fixture
`/workdir/weppcloud-wbt/test_fixtures/topaz_condition_dem/dem.tif` has SHA-256
`b87f189bf3aa79b7f25542f0982378e193d11164fec55a68f7310e6256a8282a`,
identical to the incident DEM.

At the WEPPpy 1,000 m setting (33 cells):

- legacy no-fill returned success with 377 unresolved pits and wrote output;
- legacy fill raised terrain by a maximum of 379.16178369142 m;
- installed runtime commit
  `b4d8774e3375ffd86a487c172f84e0d3f8a6cc50` returned exit code 1 with
  `WBT_UNRESOLVED_DEPRESSIONS count=377 max_dist_cells=33`;
- fail-fast wrote no `relief.tif`; elapsed time was 0.21 seconds and peak RSS
  was 21,132 KiB.

## Gates

- WBT: `cargo check -p whitebox-tools-app` passed.
- WBT: `cargo test -p whitebox-tools-app` passed, 133 tests.
- WBT wrappers: compile and wrapper containment suite passed.
- WEPPpy targeted plus import-isolation predecessor: 83 tests passed.
- Frontend targeted: 11 tests passed.
- Frontend full: 105 suites and 750 tests passed.
- ESLint passed.
- Test-stub completeness passed.
- Generated `static/js/status_stream.js` rebuilt in the WEPPcloud container.
- `git diff --check` passed.

The changed-file broad-exception checker reported one apparent added broad
catch at a line shifted by the new narrow handler. Direct counts are unchanged
at 30 broad catches in both `origin/master` and the working file; no broad
catch was added by this package.

The first broad pytest run passed 4,134 tests before exposing a test-isolation
failure in the new string-based monkeypatch. After correction, the complete
repeat passed: 5,745 passed, 58 skipped, and 1,024 warnings in 639.07 seconds.
