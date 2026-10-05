# CLIGEN 5.323-k10.1 Release Validation

## Release identity

- Source repository: `/home/workdir/jimf-cligen532`
- Source branch: `master` (`origin/master`)
- Source commit: `f7f337b026dc2eee18e098a3c5de72cd0c601a2e`
- Source tree: `4c36befb5343d859c24dd7e1380a56f7d19e471d`
- Source manifest SHA-256:
  `aac223c11d84370a3ed0a9e473e48a30cfd97900dd6c30444d4199e2a2952916`
- Release label: `5.323-k10.1`
- CLIGEN version: `5.32300`
- Built UTC: `2026-10-05T16:48:23Z`
- Compiler: GNU Fortran 13.3.0 at `/usr/bin/gfortran`
- Compiler SHA-256:
  `142861efc95f49e33705852027dae8c2e5382fd1155fcec6116ef973f25d8f84`
- ELF interpreter: `/lib64/ld-linux-x86-64.so.2`
- ELF build ID: `4bf72391f216cff091d151700e711c97e7f0d1f4`
- Binary SHA-256:
  `119ba1de5bc48757901224c8d6e91022a91bf255a45043a98579199e681aaddc`
- Sidecar SHA-256:
  `c2ce9caa4d4a82f368eea66bb3ea5b6ae2b833920b893d9d6deef974e2f6cf06`
- Published source-release commit: `6d872f25`

The canonical source release build and explicit clean-source validator passed.
`readelf` reported no `RPATH` or `RUNPATH`; dynamic dependencies are the system
`libgfortran`, `libm`, `libc`, and `libgcc_s` names.

## Vendoring and runtime identity

`tools/vendor_cligen_release.py` validated the source checkout, release pair,
compiler, source manifest, remote-default revision, role, and ELF interpreter.
It installed the executable at mode `0755` and sidecar at mode `0644`.
Recomputed hashes in WEPPpy match the source release exactly.
Validation was repeated after source-release publication commit `6d872f25`;
the tool verified the recorded source commit directly and proved it remained an
ancestor of both the checkout tip and `origin/master`.

A real `Cligen.run_multiple_year` invocation generated and parsed a 365-day
climate. Its durable `cligen_verified.log` began with the verified identity and
contained the expected version, release label, binary digest, sidecar digest,
and source commit.

## Compatibility comparison

The baseline was extracted from WEPPpy scaffold commit `a2337a6eb`; the
candidate was the exact vendored executable. Both ran the same all-wet 1980
type-6 fixture, same station parameters, same command text, and same output
filename. Daily fields were parsed by the upstream
`test/cli_field_compare.py` comparator.

| Seed | Baseline SHA-256 | Candidate SHA-256 | Byte equal | Semantic changes |
| --- | --- | --- | --- | --- |
| omitted | `3c7bbd35e26e3ca48e8dba681150efa34bd5d1d723b97c968c41160e66c9f419` | `3c7bbd35e26e3ca48e8dba681150efa34bd5d1d723b97c968c41160e66c9f419` | yes | none |
| `-r0` | `15975a61ddfd695a1afd8f612f8846255853478129e7fbf4591555aecba66434` | `15975a61ddfd695a1afd8f612f8846255853478129e7fbf4591555aecba66434` | yes | none |
| `-r12345` | `133d09856df3da71275384cedab38704510aa8a21224da1cdef596635c7481d6` | `40f27faa500abc6f42b6b4ebc9fb07a22355540d8a0d8ea83e259f0b1060270a` | no | time to peak on 341 records; all other fields unchanged |

This directly confirms the upstream contract at the WEPPpy vendor boundary.
The positive-seed difference is intentional and relevant to `prism_mod`, whose
default seed is `12345`.

## Test evidence

- CLIGEN source: `5 passed, 4 subtests passed` for release-sidecar and `k10`
  contract tests.
- WEPPpy focused climate/provenance suite: `167 passed, 18 skipped`.
- Exact real-binary integration: `1 passed`; included in the focused total.
- Full WEPPpy suite: `10288 passed, 126 skipped` in 47 minutes 35 seconds.
- Final provenance/retry focus: `32 passed`.
- Focused isolation check: two randomized runs and both files in isolation
  passed.
- Test-stub gate: all stubs complete.
- Documentation lint and patch hygiene: passed at package closeout.
