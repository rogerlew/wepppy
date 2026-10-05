# CLIGEN Binary Provenance and Runner Identity

**Status**: Closed - implemented and locally validated (2026-10-05)
**Timezone**: UTC

## Overview

Vendor the corrected CLIGEN 5.3.2 Linux executable together with its generated
provenance sidecar, then make every WEPPpy CLIGEN 5.3.2 execution verify and
record that identity before starting the process. The result must let an
operator connect a generated climate to the exact executable, CLIGEN source
commit, source-file manifest, compiler, and release label.

The upstream source checkout is `/home/workdir/jimf-cligen532`. Source commit
`f7f337b026dc2eee18e098a3c5de72cd0c601a2e` contains the positive-`-rN` `k10`
correction and automated sidecar build. Release `5.323-k10.1` was built from
that commit, published in source-repository commit `6d872f25`, and vendored in
WEPPpy implementation commit `a1747a6e1`. Its executable SHA-256 is
`119ba1de5bc48757901224c8d6e91022a91bf255a45043a98579199e681aaddc`.

## Objectives

- Produce a clean Linux release pair from the committed CLIGEN source using
  its canonical release script.
- Vendor `cligen532` and `cligen532.json` as one inseparable unit in
  `wepppy/climates/cligen/bin/`.
- Verify the sidecar schema, binary digest, size, role, clean-source claim, and
  source-manifest digest before WEPPpy executes `cligen532`.
- Write one stable identity line to each run-local CLIGEN log, including the
  CLIGEN version, release label, binary SHA-256, sidecar SHA-256, source commit,
  and verification status.
- Automate the validate-and-install operation so future releases cannot copy a
  binary without its matching sidecar.

## Scope

### Included

- The optimized Linux `cligen532` release only; the source build may validate
  the backtrace artifact, but WEPPpy does not vendor it under this package.
- A WEPPpy provenance helper shared by all CLIGEN launch paths in
  `wepppy/climates/cligen/cligen.py` and
  `wepppy/climates/cligen/single_storm.py`.
- Strict sidecar enforcement for the packaged Linux `cligen532` binary.
- Hash-only identity logging with a legacy/unverified status for existing
  `cligen43`, `cligen52`, and `cligen53` paths so their current behavior is not
  broken by the new 5.3.2 contract.
- A repository tool that validates and stages a source release pair, installs
  both files with executable/data modes, and fails closed during replacement.
- Focused unit, runner-log, tamper, and real-binary smoke tests.
- Compatibility evidence for the upstream positive-seed behavior change.

### Explicitly Out of Scope

- Windows, macOS, Intel OneAPI, or `cligen-rs` artifacts.
- Vendoring the debug/backtrace executable.
- Redesigning CLIGEN random-number generation or changing WEPPpy's seed
  defaults.
- GPG key creation, key distribution, or a new release-signing trust policy.
- Container deployment, Forest rollout, production deployment, or historical
  climate regeneration.
- Refactoring unrelated CLIGEN station, localization, or timeout behavior.

## Compatibility and Scientific Impact

The upstream correction preserves byte-for-byte output when `-r` is omitted or
when `-r0` is supplied. Positive `-rN` invocations intentionally produce new
time-to-peak values because all ten random streams now advance together.
WEPPpy's `prism_mod` path defaults `randseed` to `12345`, so this vendor update
can change its generated climate output. That change is expected, must be
demonstrated with semantic field comparison, and must not be described as a
provenance-only change.

## Complexity Budget

Reuse Python's standard `hashlib`, `json`, `dataclasses`, and file APIs. Reuse
the upstream `tools/build_cligen_release.sh` and
`tools/validate_release_sidecar.py`; do not introduce a service, database,
queue, package dependency, or general binary-signing framework. Keep the
runtime verifier specific to the `cligen-binary-provenance-v1` contract while
making its log format reusable across the existing CLIGEN launch functions.

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: The package strengthens integrity checks for a
  repository-controlled executable and adjacent metadata. It adds no public
  route, credential, external fetch, or user-selected executable path.
- **Cryptographic boundary**: SHA-256 binds the sidecar claims to the binary
  and source manifest, while the WEPPpy Git commit pins the vendored pair. An
  unsigned sidecar does not authenticate the publisher; authenticated
  provenance requires a separately governed signature.

## Generated Artifact Validation Gate

Applicable. CLIGEN produces `.cli` files consumed by WEPP. Acceptance must
trace the selected binary and sidecar through the exact runner command, the
run-local identity log, a freshly generated climate, and parsed climate fields.
Mocked subprocess tests alone are insufficient. The highest permitted claim
before deployment is `locally validated`.

## Success Criteria

- [x] The source build is made from committed source inputs at the recorded
      default-branch commit and produces adjacent optimized/backtrace sidecars.
- [x] The upstream validator passes for the optimized candidate with clean
      source, `/usr/bin/gfortran`, role `optimized`, and ELF interpreter
      `/lib64/ld-linux-x86-64.so.2`.
- [x] WEPPpy contains matching `cligen532` and `cligen532.json` artifacts; the
      vendored hash and size exactly match the sidecar and upstream release.
- [x] Every 5.3.2 launch path verifies the sidecar before process start and
      emits the same parseable identity fields to its durable run log.
- [x] Missing, malformed, dirty-source, wrong-role, source-manifest-tampered,
      and binary-tampered 5.3.2 states fail before CLIGEN execution with an
      actionable error.
- [x] Existing 4.3, 5.2, and 5.3 selections continue to run without sidecars
      and log a clearly marked legacy identity rather than a false verified
      claim.
- [x] Real default/`-r0` compatibility and positive-`-r12345` intentional
      change are demonstrated at the consumed `.cli` field boundary.
- [x] Focused tests, documentation lint, link checks, and patch hygiene pass.
- [x] The correctness review has no unresolved High or Medium findings.

## Closure

The verified binary and sidecar are now an enforced runtime pair. All five
launcher families write the same stable identity record before starting
CLIGEN. The vendoring tool validates the recorded source commit and committed
manifest bytes, stages both artifacts, and restores the prior pair after a
caught replacement failure. The exact binary produced a parsed one-year
climate, compatibility evidence bounds the positive-seed change to time to
peak, and the full WEPPpy suite passed with `10288 passed, 126 skipped`.

This closure is repository-local. Deployment and publisher signing remain
outside this package.

## Risks and Stop Conditions

Stop before vendoring if the candidate sidecar records dirty source inputs,
does not name the expected source commit, fails its source manifest or binary
digest, uses a non-system ELF interpreter, or was not built from the remote
default branch without explicit owner authorization. Stop before runner
integration if any 5.3.2 launch path cannot write a durable identity line or if
the default/`-r0` compatibility result conflicts with upstream retained
evidence. Do not silently downgrade a 5.3.2 verification failure to a warning.

## Dependencies and References

- `/home/workdir/jimf-cligen532/docs/work-packages/20261002-k10-seed-stream-contract/package.md`
- `/home/workdir/jimf-cligen532/docs/work-packages/20261002-k10-seed-stream-contract/validation.md`
- `/home/workdir/jimf-cligen532/docs/binary-release-provenance.md`
- `/home/workdir/jimf-cligen532/tools/build_cligen_release.sh`
- `/home/workdir/jimf-cligen532/tools/validate_release_sidecar.py`
- `wepppy/climates/cligen/cligen.py`
- `wepppy/climates/cligen/single_storm.py`
- `docs/binary-lifecycle.md`

## Deliverables

- Vendored `wepppy/climates/cligen/bin/cligen532` and
  `wepppy/climates/cligen/bin/cligen532.json`.
- Shared runtime verifier and identity logger.
- Automated validate-and-install tool for future CLIGEN releases.
- Focused tests and real generated-climate evidence.
- Completed correctness review, tracker, and ExecPlan.

## Rollback

Revert the binary, sidecar, runner helper, tests, and lifecycle documentation
as one commit set, then rerun the preexisting CLIGEN smoke path. Do not retain a
new binary with an old/missing sidecar or a sidecar whose digest does not match
the restored binary.
