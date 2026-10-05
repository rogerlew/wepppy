# Vendor a Verified CLIGEN Release and Log Its Execution Identity

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and is the
completed plan for `docs/work-packages/20261005_cligen_binary_provenance/`.

Completion outcome: implemented and locally validated in WEPPpy commit
`a1747a6e1`; upstream release artifacts were published in source-repository
commit `6d872f25`. Deployment remains outside this plan.

## Purpose / Big Picture

After this work, every WEPPpy run that uses the packaged Linux CLIGEN 5.3.2
executable will first prove that the file matches its adjacent provenance
sidecar. Its durable run log will identify the CLIGEN version, release label,
binary digest, sidecar digest, and exact source commit. A maintainer will be
able to prepare the next update with one validation-and-install command that
cannot intentionally install only half of the pair.

This is faithful runtime wiring, not a scaffold or surrogate. Acceptance
requires a freshly generated `.cli` from the vendored executable, direct
readback of the identity log, and semantic parsing of output affected by the
upstream positive-seed correction.

## Progress

- [x] (2026-10-05 16:29Z) Assessed source release tooling, WEPPpy binary state,
  runner call sites, compatibility impact, and repository governance.
- [x] (2026-10-05 16:29Z) Created the package scaffold and recorded the initial
  design decisions.
- [x] (2026-10-05 16:48Z) Produced a clean, validated candidate binary and
  sidecar.
- [x] (2026-10-05 17:02Z) Added automated, staged and fail-closed pair
  vendoring to WEPPpy.
- [x] (2026-10-05 17:02Z) Vendored the optimized pair and recorded exact
  identities.
- [x] (2026-10-05 17:20Z) Implemented strict 5.3.2 runtime verification and
  shared identity logging.
- [x] (2026-10-05 18:09Z) Added focused and real-boundary validation, completed
  reviews, and updated
  all living package records.

## Surprises & Discoveries

- Observation: The upstream provenance implementation is committed, but its
  current `release/linux/gfortran/cligen532` predates that workflow and has no
  JSON sidecar.
  Evidence: upstream HEAD is
  `f7f337b026dc2eee18e098a3c5de72cd0c601a2e`; the release binary hash is
  `3eda6d5d327977bcf677d6b399b6083487391c9c8637cc4ce31bb8bb435ce211`,
  and no `release/linux/**/*.json` files exist.

- Observation: WEPPpy launches `cligen532` through several independent paths,
  so changing only `Cligen.run_observed` would leave incomplete provenance.
  Evidence: process launches occur in `build_ghcn_daily_climate`,
  `Cligen.run_multiple_year`, `Cligen.run_observed`, `_run_cligen_posix` for
  `prism_mod`, and `single_storm._run_cligen`.

- Observation: The vendor refresh has a real scientific reproducibility effect
  in WEPPpy because `prism_mod` turns an omitted seed into positive seed
  `12345`.
  Evidence: `wepppy/climates/cligen/cligen.py` assigns `randseed = 12345` and
  appends `-r<seed>`; the upstream validation shows positive seeds intentionally
  change only time to peak relative to the prior binary.

- Observation: Importing the provenance helper through the CLIGEN package made
  the host vendoring command depend on NumPy.
  Evidence: the first real host invocation failed before validation; loading
  the standalone module directly removed that unrelated dependency.

- Observation: Publishing generated release artifacts advances repository HEAD
  beyond the source commit recorded by the sidecar.
  Evidence: post-publication source commit `6d872f25` follows recorded source
  commit `f7f337b0`. The final tool verifies the recorded commit and tree
  directly, hashes committed manifest bytes, and requires the recorded commit
  to be an ancestor of both HEAD and the remote default branch.

## Decision Log

- Decision: Require a valid sidecar for Linux `cligen532` and fail before
  process launch on any verification error.
  Rationale: A warning would allow an untraceable executable to produce a
  climate despite the package's provenance goal.
  Date/Author: 2026-10-05 / Codex.

- Decision: Preserve legacy `cligen43`, `cligen52`, and `cligen53` without
  sidecars, but label their computed identities `legacy_unverified`.
  Rationale: The requested release is 5.3.2, and blocking historical selectors
  would be an unrelated compatibility break.
  Date/Author: 2026-10-05 / Codex.

- Decision: Generate sidecars only in the source repository and add a WEPPpy
  tool that validates and stages the pair before fail-closed replacement.
  Rationale: Build metadata belongs at the build boundary; WEPPpy must consume,
  not reconstruct, that claim.
  Date/Author: 2026-10-05 / Codex.

- Decision: Treat the sidecar as integrity evidence, not publisher
  authentication.
  Rationale: SHA-256 detects mismatch, while identity of the publisher requires
  a trusted signature not authorized in this package.
  Date/Author: 2026-10-05 / Codex.

## Outcomes & Retrospective

Release `5.323-k10.1` was built from clean source commit `f7f337b0` and vendored
with binary SHA-256
`119ba1de5bc48757901224c8d6e91022a91bf255a45043a98579199e681aaddc` and
sidecar SHA-256
`c2ce9caa4d4a82f368eea66bb3ea5b6ae2b833920b893d9d6deef974e2f6cf06`.
All five launcher families now verify and log the pair before execution;
legacy selectors retain an explicit `legacy_unverified` path.

A real vendored-binary run generated and parsed a one-year climate. Default and
`-r0` outputs remained byte-identical to the prior WEPPpy binary, while
`-r12345` changed only time-to-peak fields as intended. Focused climate tests
passed (`167 passed, 18 skipped`), the final provenance/retry slice passed
(`32 passed`), isolation checks passed, and the full suite passed (`10288
passed, 126 skipped`). The correctness review closed with no unresolved
findings. No deployment or publisher-authentication claim is made.

## Context and Orientation

The CLIGEN source repository is `/home/workdir/jimf-cligen532`; although the
user referred to `/workdir`, this is the available checkout. Its default remote
branch is `origin/master`, and current head
`f7f337b026dc2eee18e098a3c5de72cd0c601a2e` contains the `k10` correction at
commit `147b2c12` and sidecar automation at `f7f337b0`. Generated object files
are locally modified, but the release script copies only `.f`, `.inc`, and the
makefile to a temporary build directory and rejects dirty source inputs.

`tools/build_cligen_release.sh` builds optimized and backtrace executables,
creates `cligen-binary-provenance-v1` JSON sidecars, and validates their binary,
source, compiler, and ELF metadata. The optimized source artifact is
`release/linux/gfortran/cligen532` with adjacent `.json`.

WEPPpy stores executable variants in `wepppy/climates/cligen/bin/`. The current
5.3.2 binary hash is
`ca5d850a2e7ed8285969186b49fc495953a6aad67d10cd44eb84b447897c2c75`.
There is no current sidecar. `wepppy/climates/cligen/cligen.py` owns most
launchers; `wepppy/climates/cligen/single_storm.py` owns the direct single-storm
launcher. Each launcher writes a run-local log that must receive the identity
line before any child output.

A sidecar cryptographically binds claims by storing the executable SHA-256 and
a canonical SHA-256 over the source-file manifest. Runtime verification can
prove the vendored binary matches those claims and that the manifest itself was
not altered. It cannot prove who created an unsigned sidecar; the Git commit
that vendors both files supplies repository history, not external publisher
authentication.

## Plan of Work

Milestone 1 creates the release candidate in the source repository. Verify the
remote default branch and source-input status, run the canonical release script
with `/usr/bin/gfortran` and an explicit reviewed release label, then run its
validator with the source root, clean-source requirement, optimized role, and
system ELF interpreter. Record candidate binary and sidecar hashes in this plan
and tracker. Do not use the preexisting release binary.

Milestone 2 adds `tools/vendor_cligen_release.py` in WEPPpy. The tool accepts a
source root and optional destination, invokes or faithfully applies the
`cligen-binary-provenance-v1` validation contract, requires role `optimized`
and clean source, verifies the expected commit when supplied, and stages both
files in the destination directory before replacing the final pair. Install the
binary with mode `0755` and JSON with mode `0644`. Two files cannot be replaced
in one filesystem operation, so replace them in a documented order that makes
any interrupted mixed state fail verification, and restore the prior pair on a
caught error. Unit tests use temporary files and prove that
binary-only, mismatched, dirty, wrong-role, and malformed installs fail.

Milestone 3 vendors the candidate into
`wepppy/climates/cligen/bin/cligen532` and `.json` through that tool. Verify the
vendored pair independently, inspect `file` and `readelf`, and ensure Git sees
exactly the intended binary and sidecar changes. Record all four identities:
source commit, source-manifest digest, binary digest, and sidecar digest.

Milestone 4 adds
`wepppy/climates/cligen/binary_provenance.py`. Define an immutable
`CligenBinaryIdentity` data class and these interfaces:

    def collect_cligen_binary_identity(binary_path: str | os.PathLike[str]) -> CligenBinaryIdentity
    def write_cligen_binary_identity(log_fp: TextIO, *, runner: str, binary_path: str | os.PathLike[str]) -> CligenBinaryIdentity

For `cligen532`, load the adjacent `<binary>.json`, require schema
`cligen-binary-provenance-v1`, validate its required object and scalar types,
binary name, optimized role, SHA-256, size, clean-source claim, non-empty source
commit and tree, non-empty CLIGEN version, and canonical source-manifest digest.
Compute and include the sidecar's own SHA-256. Reject invalid state with a
specific exception before process creation. For legacy binary names, compute
path, digest, size, and mtime and return `legacy_unverified` without requiring a
sidecar. Do not cache solely by path; either hash per logical invocation or key
the cache by stable file metadata and test in-place replacement.

The log formatter emits one newline-terminated, safely quoted line with stable
keys: `runner`, `binary_path`, `binary_sha256`, `binary_size_bytes`,
`sidecar_path`, `sidecar_sha256`, `cligen_version`, `release_label`,
`source_commit`, `source_git_tree`, `source_manifest_sha256`, and
`binary_identity_status`. No compiler path or host path from the sidecar is
needed in routine logs.

Milestone 5 wires the helper into all launch families before `Popen` or
`subprocess.run`. A logical retry in `run_observed` logs identity once before
the attempt loop. `_run_cligen_posix` receives or derives the binary path from
`cmd[0]` and writes to its supplied log. The GHCN, synthetic multi-year,
observed, PRISM-modified, and single-storm log files must each contain the same
identity contract. Also emit the verified line through `_LOGGER.info` only if
that adds operational visibility without duplicating sensitive or unbounded
sidecar content; the durable run-local file is authoritative.

Milestone 6 validates behavior. Unit tests prove valid parsing and every
specified failure state. Launcher tests substitute a valid temporary executable
and sidecar and assert identity appears before child output. A real optimized
binary smoke generates and parses `.cli` output. Compare the prior and candidate
binaries for no option, `-r0`, and `-r12345`: no-option and zero must remain
byte-identical, while the positive-seed difference must agree with the upstream
contract and be isolated semantically to time to peak when input mode permits
that comparison. Complete the correctness review, update
`docs/binary-lifecycle.md` with the CLIGEN pair workflow, and run repository
documentation and patch gates.

## Concrete Steps

Run source release commands from `/home/workdir/jimf-cligen532`:

    git symbolic-ref refs/remotes/origin/HEAD
    git status --short -- cligen532/*.f cligen532/*.inc cligen532/makefile
    RELEASE_LABEL=<reviewed-label> COMPILER=/usr/bin/gfortran tools/build_cligen_release.sh
    python3 tools/validate_release_sidecar.py \
      --sidecar release/linux/gfortran/cligen532.json \
      --binary release/linux/gfortran/cligen532 \
      --source-root . --compiler /usr/bin/gfortran \
      --expect-release-label <reviewed-label> \
      --expect-binary-role optimized \
      --expect-elf-interpreter /lib64/ld-linux-x86-64.so.2 \
      --require-clean-source

Expected validator output begins with `sidecar_ok=`. Any validation failure is
a stop condition, not a reason to pass `ALLOW_DIRTY_SOURCES=1`.

Run vendoring and validation from `/workdir/wepppy`:

    python3 tools/vendor_cligen_release.py \
      --source-root /home/workdir/jimf-cligen532 \
      --expect-source-commit f7f337b026dc2eee18e098a3c5de72cd0c601a2e
    sha256sum wepppy/climates/cligen/bin/cligen532 \
      wepppy/climates/cligen/bin/cligen532.json
    file wepppy/climates/cligen/bin/cligen532
    readelf -l wepppy/climates/cligen/bin/cligen532

The source checkout may contain a later release-publication commit. The
expected commit always pins the sidecar's recorded source revision; the tool
requires that revision to be an ancestor of both checkout HEAD and the remote
default branch.

Use canonical test wrappers from `/workdir/wepppy`:

    wctl run-pytest tests/climate/test_cligen_binary_provenance.py \
      tests/climate/test_cligen_run_observed_retries.py --maxfail=1
    wctl run-pytest tests/climates --maxfail=1
    wctl doc-lint --path docs/work-packages/20261005_cligen_binary_provenance
    wctl doc-lint --path docs/binary-lifecycle.md
    git diff --check

Update the exact focused test paths if repository naming conventions require a
different location, and record the final commands and counts in the tracker.

## Validation and Acceptance

Acceptance is observable when a real CLIGEN 5.3.2 invocation succeeds and its
run-local log contains `binary_identity_status=verified` plus values matching
the vendored sidecar and recomputed file hashes. Changing one byte in a
temporary copy of the executable must prevent the subprocess from starting.
Changing the source manifest without updating its canonical digest must also
fail. Deleting the sidecar must fail for `cligen532` but not for an explicitly
selected legacy executable, whose log must say `legacy_unverified`.

Generated-output acceptance must use the exact vendored candidate. Parse the
fresh `.cli`; file existence, process exit zero, and a log line are not enough.
Retain compact hashes and field-difference summaries rather than generated
climate files. The correctness review must cover valid, absent, malformed,
tampered, legacy, and in-place-replaced artifact states and close every High or
Medium finding.

No deployment claim is authorized by this plan. Completion means implemented
and locally validated in the WEPPpy checkout.

## Idempotence and Recovery

The source build uses a disposable directory and can be rerun. The vendor tool
must stage and validate both files before final replacement, so rerunning with
the same pair is safe. Because separate files do not have a single atomic rename,
an interruption may leave a mixed pair; strict runtime verification must reject
that state. Restore the last Git version of both destination files together and
rerun validation. Never restore only the executable or only the sidecar.
Temporary tamper tests must operate on copies outside the vendored directory.

## Artifacts and Notes

Record the final release label, build time, compiler digest, source manifest
digest, binary digest, sidecar digest, `file` summary, ELF interpreter, test
counts, and semantic output comparison in the tracker or a compact artifact
under `docs/work-packages/20261005_cligen_binary_provenance/artifacts/`.
Complete `artifacts/2026-10-05_correctness_review.md` against the exact
candidate revision before closeout.

## Interfaces and Dependencies

Use only the Python standard library at runtime. `CligenBinaryIdentity` is the
typed result shared by validation and formatting. The source repository remains
the authority for sidecar generation; WEPPpy's vendor tool and runtime module
are independent consumers of schema `cligen-binary-provenance-v1`. The runtime
module must not import a script from the neighboring checkout because deployed
WEPPpy installations do not contain that repository.

The durable log contract is additive. Existing CLIGEN stdout/stderr and timeout
messages remain present after the identity line, and existing `.cli`, `.par`,
and `.inp` formats do not change.

---

Revision note (2026-10-05 16:29Z): Initial self-contained ExecPlan authored
after source-tooling, artifact, runner-path, and compatibility assessment.

Revision note (2026-10-05 18:09Z): Recorded completed implementation, exact
release identities, post-publication source validation semantics, and all test
and review outcomes before archiving the plan.
