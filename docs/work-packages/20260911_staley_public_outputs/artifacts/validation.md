# Validation

Contract ancestor: f049a2c02. Correctness and security source reviews accepted.

- Initial publication + production suite: 53 passed.
- Final helper + unchanged fixed-file API suite: 27 passed.
- Additional same-stat/wrong-recorded-hash, staged-copy hash, and completion-hook
  failure tests: final publication suite 13 passed.
- Real filesystem tests cover absent/empty state, partial acceptance, new-run
  replacement, failed-run preservation, tamper/symlink rejection, manifest-last
  interruption before/after table installation, and explicit repair. Failed copy
  preserves accepted NoDb/originals; retry needs no model computation.
- [Live repair](live.log): addicted-reservist accepted result
  88d613bedab2464b84f752929b86d43c copied to the four top-level files. All hashes
  equal accepted originals; NoDb bytes and current scientific freshness unchanged.
- [Worker check](worker.log): normal rq-worker container, uid1000/gid993,
  umask022, resulting files0644. Actual mounted project publication succeeded.
- [Browser check](browser.log), [script](browser.cjs): all four names visible in
  the standard browser; standard /download/ responses match accepted SHA-256;
  listing remains visible after reload. The first probe incorrectly used the
  bearer-only /files/ API; corrected to the browser's established /download/ route.
- Engine modules and fingerprints unchanged. No model rerun, input mutation,
  queue wiring, browser/controller UI changes, or custom access route.
- Full suite remains on operator hold. No production fleet deployment.

Established pattern: ordinary module-local files, normal worker umask, and the
existing browser/download links, as used for RUSLE outputs. Four separate files
are not a transaction; interrupted installation is repaired by publish_outputs.
