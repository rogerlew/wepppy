# M0 qualification and baseline receipt

**Status**: M0 accepted for proceeding; production candidate validation remains open.  
**Environment**: forest, `/home/workdir/wepppy` (resolved `/workdir/wepppy`).  
**Source**: `2041fb8e267de3a1572d9fb4f4a62e725b75cc91`, dirty worktree.

## Source and runtime identity

The unrelated documentation, generated index, and management JSON changes
present at entry were preserved. This execution changes policy/package documents and one stale test assertion;
scanner downloads and qualification artifacts are private, non-runtime files.

| Input | SHA-256 |
| --- | --- |
| `docker/requirements-uv.txt` | `d15ff4fd344453b1d10f528178c90127c78e3748790a36768d38136ac7aacb80` |
| Primary frontend lock | `2ddc0117c0bf2c559d2509bded8964801092fe68e4046ec3c8fa3df9c6877a92` |

Installed wctl resolves development Compose and `wepppy-dev`, built through
`docker/Dockerfile.dev`. The running baseline container is
`36ef158e549528a6c46fe40b05e08e74c97e9619a9e0055370acd22890f83405`, started
`2026-11-11T02:34:12.145555344Z`, configured user `1000:993`, consuming image
`sha256:b32d1c74915c7f7235c4f1bd02ff8e25808be7c8bac665e925a01785bc9f9afa`.
This is development-baseline evidence, not wepp1 identity or a final candidate.
Rendered Compose was parsed in memory and only image/Dockerfile fields emitted;
no secret-bearing rendered configuration was retained.

Build-context preflight found approximately 852 GiB in local `out/`, which is
not excluded by `.dockerignore`; Docker stores images under `/var/lib/docker`
on the smaller root filesystem. M1 will use a clean detached checkpoint checkout
and canonical Compose/Dockerfile inputs, with verified LFS materialization.
The original branch, unrelated dirty files, and existing images remain intact.

## Required pre-change gates

The sequential runner started at approximately 2026-11-11 05:05 UTC. Complete
stdout/stderr and command/exit/duration receipts staged under
`/tmp/wepppy-security-m0/` and are now retained in private `baseline-initial/`
and `baseline-final/` directories. The initial runner records duration but
does not record an exact start timestamp, so this receipt does not invent one.

| Exact command | Current result |
| --- | --- |
| `wctl run-pytest tests --maxfail=1` | Initial exit 1; stale help-link assertion failed. Corrected full rerun exits 0: 13,502 passed, 435 skipped; 3,803.88 seconds. |
| `wctl run-npm lint` | Exit 0; 12.26 seconds. |
| `wctl run-npm test` | Exit 0; 124 suites and 1,069 tests passed; 8.8 seconds. |

These initial results preceded any dependency or test edits. The failure at
`tests/weppcloud/test_usersum_template_wiring.py:95` reproduced in isolation:
the assertion expected obsolete JavaScript variable `runsTtlDeletionHelpUrl`.
The existing authoritative `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md`
Presentation Contract instead requires one panel-level **How to keep your project**
anchor, using the usersum document URL. The production template already conforms.
The bounded test repair asserts that exact anchor and document ID appear once;
no production behavior or normative contract changed. All 11 tests in the module
pass after repair. A second unsegmented full pytest run passes: 13,502 passed, 435 skipped,
6,029 warnings. It ran from 06:14:22 to 07:17:46 UTC, with separate
`pytest-rerun.log` and `pytest-rerun.json` receipts. `wctl check-test-stubs`
also passes. Final requirements/lock hashes and container identity/start time
match their initial values. The final baseline manifest SHA-256 is
`321aa988535d4b05b2c3267b894adc28497ba1d41fbc641174992995323c2ba3`. M0 cannot accept a
partial count or substitute focused runs for the full commands.

## Tool qualification evidence

Owner-selected retained root:
`/workdir/weppcloud-deployments/.local/dependency-security/evidence/m0-20261111T0505/`.
The gitignored `out/security-audit-20261110/f6/m0-20261111T0505/` path is a
symlink to that directory.
Its `scanner-trial/` directory contains 136 files listed in
`qualification-evidence-manifest.json`, whose SHA-256 is
`63afc8c3704aa716b5234ecb777e84a4785c9fcf5d5bc849b0670ee3b24908e8`.
Directories are 0700; evidence files are 0600; executable tools are 0700.
The original `/tmp/wepppy-security-m0/scanner-trial` path is a symlink to this
retained directory, preserving the recorded command paths. Report bytes and
original receipts were not rewritten when moved.

The approved qualification boundary is a non-root, read-only container with all
capabilities dropped, no-new-privileges, no runtime/project mounts, no Docker
socket, and explicit archive/SBOM mounts. Scans use no network. Database download
is a separate operation using public CA certificates; no TLS bypass was used.
Trials use a 2 GiB memory and two-CPU limit. Completion under these limits is
observed; peak resource consumption and final common-image sizing are not proven.

| Trial | Result |
| --- | --- |
| Trivy 0.76.2 acquisition | Archive hash and exact GitHub attestation identity verified. |
| Trivy small-image inventory | All 89 Debian packages reconciled; malformed archive fails with no report. |
| Trivy development-image scan | Exits zero but omits a Python GDAL advisory after a range-parsing error; rejected for adoption. |
| Syft 1.57.1 development-image SBOM | Exit zero, 80.95 seconds; 324/324 Python and 475/475 Debian versions reconciled using PEP 503 name normalization. |
| Grype 0.121.3 native-SBOM scan | Exit zero, 60.87 seconds; detects GDAL advisory omitted by Trivy; no constraint-error diagnostics. |
| Grype with matcher suppressions included | Exit zero, 34.73 seconds; 3,006 matches and 330 ignored matches, all retained for future disposition. |
| Grype malformed SBOM / absent database | Both exit one and leave zero-byte output files; existence cannot imply success. |
| Syft negative-size `.deb` fixture | Default image catalogers exclude the affected parser. Forcing it triggers a recovered panic in native `files[].unknowns` despite exit zero. |

The development SBOM also records 1,969 executable ownership gaps and 38 binary
package records without PURLs. These require coverage reconciliation in M1;
complete Python/Debian version inventory does not resolve unmanaged components.
No development-image advisory count supersedes the original F6 signal or proves
production applicability.

The security review approves the pinned Syft-to-Grype image-only pipeline for
M1 evidence collection. See the scanner evaluation for hashes, signature
verification, tool self-advisories, parser exclusions, database identities,
ignored findings, verifier bootstrap limitations, and source references.
Acquisition-only Cosign findings remain explicit; it is not an application
dependency or a production-installed tool.

## Remaining gates

Roger ratified the concrete policy and selected the private deployment repository
for retention. Its `.local/dependency-security/` directories are 0700; the
approval record is 0600 and ignored by Git. The observed filesystem has about
23 TiB available. The approval record binds policy SHA-256
`57ea1bdefa0c8753701aa702806c7b936ea0d7684c9e6ad76213d25d5c17f01c`.
The later owner clarification selects manual transfer and reaffirms production
Docker Compose. The separate `policy-20261111-manual-transfer.json` approval
record links the original hash above to amended policy SHA-256
`2c381b5cf53b40278a1145d8bbf32e314647be8328010aaa9005ae414cd4e6be`.
This proves local storage access, not the manual CI handoff or deployed retention.
Initial baseline logs are retained in `baseline-initial/`, with manifest SHA-256
`8601c6bfbb9e48220b275810dbcd0c3e33ac898b3a29e5450d38790278c1c27c`.

The independent correctness design review passes with
qualification prerequisites; the operations review identifies direct error
propagation and activation-time image selection requirements. Neither authorizes
deployment. The reviewed M0 checkpoint accompanies this receipt. The unchanged
common-image preparatory build/scan is documented separately; M1 dispositions,
fresh database evidence, native coverage and M2-M5 remain open.
