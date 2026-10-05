# CLIGEN Binary Provenance and Runner Identity Tracker

Timezone: UTC. Started: 2026-10-05 16:29 UTC.

Current phase: assessment and work-package scaffold complete; implementation
has not started. No binary or sidecar has been vendored and no runner behavior
has changed.

## Progress

- [x] (2026-10-05 16:29 UTC) Read repository planning and binary-vendoring
  guidance and inventoried all CLIGEN subprocess launch paths.
- [x] (2026-10-05 16:29 UTC) Recorded current WEPPpy and upstream release
  binary hashes and confirmed that no clean candidate sidecar pair exists yet.
- [x] (2026-10-05 16:29 UTC) Assessed positive-seed compatibility impact:
  `prism_mod` defaults to positive seed `12345` and will intentionally receive
  new time-to-peak values from the corrected binary.
- [x] (2026-10-05 16:29 UTC) Scaffolded package, tracker, correctness-review
  gate, and active ExecPlan.
- [ ] Build and validate the clean CLIGEN release pair from source commit
  `f7f337b026dc2eee18e098a3c5de72cd0c601a2e` or record an explicitly reviewed
  successor commit.
- [ ] Implement the WEPPpy validate-and-install automation.
- [ ] Vendor the exact optimized binary and sidecar pair.
- [ ] Implement shared runtime verification and identity logging across every
  5.3.2 launch path while preserving legacy binary behavior.
- [ ] Add and pass focused unit, tamper, launcher-log, real-binary, and semantic
  compatibility tests.
- [ ] Complete correctness review and documentation updates.

## Decisions

- **2026-10-05 16:29 UTC** - Treat `cligen532` and `cligen532.json` as one
  release unit. A missing or invalid sidecar is a pre-execution error for
  CLIGEN 5.3.2.
- **2026-10-05 16:29 UTC** - Preserve older executable selections without
  retroactively fabricating sidecars. Log their direct file hash with
  `legacy_unverified` status.
- **2026-10-05 16:29 UTC** - Log the sidecar-declared CLIGEN version together
  with release, binary, sidecar, and source identities; never use the version
  string alone as provenance.
- **2026-10-05 16:29 UTC** - Keep sidecar generation in the CLIGEN source
  repository and automate validation plus staged, fail-closed pair installation
  in WEPPpy.
- **2026-10-05 16:29 UTC** - Do not claim publisher authentication without a
  verified signature. The initial package uses SHA-256 integrity plus Git
  history and leaves signing policy out of scope.

## Risks

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Binary and sidecar copied from different builds | High | One validate-and-install command; digest and size checks before staged fail-closed replacement | Open |
| A launch path omits identity logging | High | Inventory five launcher families and add path-level tests | Open |
| Positive `-r12345` output drift is mistaken for regression | High | Parse fields and compare against upstream retained contract evidence | Open |
| Sidecar integrity is described as publisher authenticity | Medium | Explicit unsigned-boundary wording in logs/docs/review | Open |
| Runtime hash cache becomes stale after in-place replacement | Medium | Key any cache by inode/size/mtime or hash per invocation; test replacement | Open |
| Legacy CLIGEN versions are accidentally blocked | Medium | Strict policy only for basename `cligen532`; legacy status tests | Open |

## Verification Checklist

- [ ] Upstream clean-source release build and sidecar validation.
- [ ] Candidate source commit and remote-default branch recorded.
- [ ] Candidate and vendored SHA-256/size equality.
- [ ] ELF interpreter and runtime dependency checks.
- [ ] Valid-sidecar runtime unit test.
- [ ] Missing/malformed/dirty/wrong-role/manifest-tampered/binary-tampered
      rejection tests.
- [ ] Synthetic, observed, PRISM-modified, GHCN, and single-storm identity-log
      coverage.
- [ ] Default and `-r0` generated-output compatibility evidence.
- [ ] Positive `-r12345` time-to-peak-only compatibility evidence for the
      corrected binary relative to the prior binary.
- [ ] `wctl run-pytest` focused tests and real smoke.
- [ ] `wctl doc-lint --path docs/work-packages/20261005_cligen_binary_provenance`.
- [ ] `git diff --check` and documentation link checks.
- [ ] Correctness review passed with no unresolved High/Medium findings.

## Blocked

None. The next action is to create a clean release pair; the existing upstream
release binary is not the candidate and has no sidecar.

## Notes - 2026-10-05 16:29 UTC

Assessment found direct process launches in `build_ghcn_daily_climate`,
`Cligen.run_multiple_year`, `Cligen.run_observed`, `_run_cligen_posix` as used
by `prism_mod`, and `single_storm._run_cligen`. The implementation should
centralize verification and log formatting rather than duplicate JSON parsing
at each call site.

The upstream checkout has modified object files
`cligen532/cligen.o` and `cligen532/cligen.debug.o`; they are generated objects,
not scoped source inputs. The release script builds in a disposable directory
and rejects dirty `.f`, `.inc`, and `makefile` inputs by default. Do not vendor
any preexisting release artifact merely because the source-input scope is
clean; run the release script after the provenance commit and validate the
result.
