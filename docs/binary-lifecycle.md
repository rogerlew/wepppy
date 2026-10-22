# WEPP and CLIGEN Binary Lifecycle

## Scope

Release-sidecar MOFE and uploaded-input compatibility declarations follow
[CBEXEC-01](schemas/wepp-executable-selection-contract.md). Metadata-only remints
verify binary identity and preserve original build provenance; they are not
new executable builds. Sidecar capability changes must participate in Builder
registry freshness. The release generator on wepp-forest's default branch is
the source of vendored declarations.

Lifecycle policy for vendored watershed/hillslope binaries in `wepp_runner/bin`
and the Linux CLIGEN 5.3.2 executable in
`wepppy/climates/cligen/bin/cligen532`.

## Canonical Build Environment

- Canonical build host compiler: `/usr/bin/gfortran`
- Disallowed toolchains for vendored builds: Homebrew, Conda, or user-local compiler/runtime stacks
- Required ELF interpreter: `/lib64/ld-linux-x86-64.so.2`
- Required `libgfortran` source: system package libraries (`/lib*` or `/usr/lib*`), not vendored runtime blobs

## Provenance Rejection Criteria

Automatic reject if interpreter, `RPATH/RUNPATH`, or resolved library paths include any of:
- `/home/linuxbrew/.linuxbrew/lib/ld.so`
- `/opt/homebrew/...`
- `/home/*/miniconda*/...`
- `/home/*/miniforge*/...`

Automatic reject if:
- interpreter differs from `/lib64/ld-linux-x86-64.so.2`
- `libgfortran` resolves outside system library prefixes
- non-system dynamic dependency paths are present

## Required Gate

All required release/vendoring gates must be reproducible using committed
resources, or generated outputs from committed inputs. Private run directories,
untracked holdouts and host-local datasets cannot be prerequisites. Record the
source commit for cross-repository fixtures. Preserve external scientific
studies as supplementary evidence, without making their storage locations
mandatory. The reconciled-condenser replay is retired. New defect gates require
a committed bounded reproduction or deterministic generator first.

Run for every candidate vendoring operation:

`tools/check_wepp_binary_provenance.sh <binary> [<binary> ...]`

The gate validates interpreter, compiler/runtime fingerprints, `RPATH/RUNPATH`, and `ldd` resolution paths.
Nonzero exit means the binary is not eligible for vendoring.

## Vendoring Enforcement

`tools/rebuild_vendor_wepp_260319.sh` enforces provenance twice:
1. on `wepp-forest/release` build outputs before install into `wepp_runner/bin`
2. again on vendored targets after install

This prevents non-compliant binaries from passing the vendoring path.

Finalize and validate sidecar JSON before exposing a new release to discovery.
When updating installed metadata, write a complete temporary file in the same
directory and atomically replace the sidecar; never truncate it in place. Hold
release files fixed while running discovery/Builder validation.

## Runtime Enforcement

`wepp_runner` now enforces this provenance contract at runtime before launching any
hillslope, flowpath, or watershed WEPP executable. The runtime guard checks:

- ELF interpreter equals `/lib64/ld-linux-x86-64.so.2`
- no Homebrew/Conda path fingerprints in interpreter or resolved dependencies
- `RPATH/RUNPATH` entries remain in system library prefixes only
- dynamic binaries resolve `libgfortran` from system library prefixes

The guard intentionally fails fast with an explicit remediation error if a selected
binary violates policy. For emergency triage only, operators can bypass the guard by
setting `WEPP_RUNNER_SKIP_BINARY_PROVENANCE_CHECK=1`.

Legacy static binaries (`ldd` reports `not a dynamic executable`) are permitted for
backward compatibility, but all dynamically linked binaries are enforced against the
full provenance policy.

## CLIGEN 5.3.2 Release Pair

CLIGEN source releases are built in `/home/workdir/jimf-cligen532` with:

    RELEASE_LABEL=<reviewed-label> \
      COMPILER=/usr/bin/gfortran \
      tools/build_cligen_release.sh

That command builds in a disposable directory and creates
`release/linux/gfortran/cligen532` plus the adjacent `cligen532.json`. The
`cligen-binary-provenance-v1` sidecar records the binary SHA-256 and size,
CLIGEN version, source commit and tree, canonical source-file manifest,
compiler identity, flags, build time, and ELF metadata. The source build
rejects dirty `.f`, `.inc`, and makefile inputs.

From `/workdir/wepppy`, validate and install the pair with:

    python3 tools/vendor_cligen_release.py \
      --source-root /home/workdir/jimf-cligen532 \
      --expect-source-commit <full-commit> \
      --expect-release-label <reviewed-label>

The vendor tool requires the source checkout to match its remote-default
branch, validates every source-manifest entry, checks the system compiler and
ELF interpreter, stages both files, and installs modes `0755` and `0644`.
Separate files cannot be replaced in one atomic filesystem operation. The tool
therefore validates before replacement, restores both prior files after a
caught failure, and relies on strict runtime verification to reject any mixed
pair left by an external interruption.

Every packaged `cligen532` launch requires the adjacent sidecar and verifies
the binary digest, size, optimized role, clean-source claim, source identities,
and canonical manifest digest before process creation. The run-local CLIGEN log
records the CLIGEN version, release label, binary and sidecar digests, source
commit/tree/manifest digest, and `binary_identity_status=verified`. Historical
`cligen43`, `cligen52`, and `cligen53` executables remain runnable without
sidecars but are explicitly logged as `legacy_unverified`.

The JSON hashes provide integrity and connect the binary to claimed source
bytes. They do not authenticate the publisher. Publisher authentication needs
a separately governed and verified signature over the sidecar.

## Vendored WEPP Release Log

WEPP 261010 pairs the model with the existing component-v3 native reader.
See [the v3 compatibility contract](schemas/pass-components-v3-contract.md).
Regenerate every contributing PASS file with the same selected build; do not
mix legacy and v3 files during Roads or AgFields integration. Existing binary
defaults remain unchanged. Mutation, disturbed rankings and Cedar water
verification are complete for the promoted candidate; vendoring alone is
not deployment approval. See [ADR-0084](adrs/ADR-0084-chrqin-source-normalization-release.md).

| Date | Release | Source | Binary SHA-256 | Notes |
| --- | --- | --- | --- | --- |
| 2026-10-21 | `wepp_261021`, `wepp_261021_hill`, artifact revision 2 | default-branch source `d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b` | watershed `e2c83b1a691fad3ffe29acf1588dadbecfeec9b027391df8b7fddcf4908d2971`; hillslope `81591bf0301604aa25002d641e3c8e5d22e15c747b179f1613e7c329233f4965` | Authorized same-name reissue of the undeployed edition below. Adds groundwater/hourly allocation, channel source, retained state/reference, publication and working-flux repairs; preserves Gregorian fixes and ASCII PASS v3. Regenerate all hillslope and watershed outputs with the matched pair. MC storage authority is unchanged; signed exchange/clipping remain open. Exact code equivalence to the Cedar-tested candidate. [Reissue gates](work-packages/20261021_wepp_261021_rerelease/package.md) and [approved illustrated report (PDF)](/weppcloud/static/reports/wepp/release-notes/wepp_261021/wepp_261021_release-notes-r1.pdf). No default switch or deployment. |
| 2026-10-21 | `wepp_261021`, `wepp_261021_hill`, original edition (superseded) | default-branch Forest source `a87925df9ffe6ebb928e126395dd159d484285fa` | watershed `fe7a8d7b93deb2329536b9cc937b9f51a5c747b19fd3b95584347639046fa385`; hillslope `6e4ec397551175ffd71337eeea04f5b3150a544f247382c863956fb50d7e59d1` | Gregorian century-year execution and PASS/EBE date alignment; strict climate EOF and daily PASS validation. Retains 261010 ASCII PASS v3 and existing interchange. Native 232 tests and 12 watchlist cases pass; host/container smokes and post-vendor checks pass. Fresh 400-year replay has 146,097 aligned days. WEPPpy segmented coverage: 11,052 passed/122 skipped; test-order/browser-path limits retained in release evidence. Regenerate all contributing hillslope and watershed outputs with the paired release. No default switch or deployment. [Release evidence](work-packages/20261021_wepp_261021_release/package.md). |
| 2026-10-12 | 260803 and261010 paired sidecar refresh | Native default-branch metadata commit `917265bb5`; WEPPpy selection implementation `3c114719b` | Executable hashes unchanged; see [remint receipt](work-packages/20261012_wepp_executable_capabilities/artifacts/sidecar-remint.json) | Add explicit MOFE and single-input-reader capability flags. Preserve source/build provenance and PASS declarations. Native 30-case format/OFE matrix and live selected-release worker execution pass. [Validation](work-packages/20261012_wepp_executable_capabilities/artifacts/validation.md). |
| 2026-10-10 | `wepp_261010`, `wepp_261010_hill` | default-branch Forest source `7471bb5e981d14d0b8c1cdb88a16af305aed1b67`; existing paired v3 interchange unchanged | watershed `1dd1ca75cf53f9a0606cf5a598312d4e680e161df631156360d4a20dbcb6f17e`; hillslope `d8ea3a07a29ef1e754c5362bd7931cc3a93486d75faa32df5c5f2e821c22d698` | Promotes validated CHRQIN first-sample normalization fix, retaining hourly MIXPEAK, PASS v3 and channel-state continuation. Replaces never-deployed 261009; historical studies remain unchanged. Forest tests 163 pass; watchlist 12/12; candidate executable equivalence is exact excluding debug/build ID. Fresh 96-case release rankings pass. Detailed post-vendor evidence and limitations are recorded in the Topanga investigation's release handoff. No general default switch or production deployment. |
| 2026-10-09 | `wepp_261009`, `wepp_261009_hill` | default-branch model source `5a01758b7b998d54cccc47d7eea01847b04d866b`; paired wepppyo3 source `c3d8481d1c7dcaf59dceb37d9ea2e860b89f4307`, artifact commit `bd63094` | watershed `e1b1c244107216ca9edf4ccbaeb8d390e98440418d87beac2d5153b98191c7cc`; hillslope `37d8deaf7a4c78e83104db4d896db3ee10b77a5f5d3f3abe5ad718390e2cc228` | Hourly MIXPEAK, PASS v3 return-support assembly and channel-profile continuation, superseding the experimental 261007 patch bundle. Matching reader and Roads/AgFields composition are required. Forest tests 155 passed; watchlist 12/12; both vendored host/container smokes and provenance pass using committed fixtures. External fresh watershed studies are supplementary, not required gates. Broad WEPPpy sweep was interrupted after 2,375 passes; targeted workflows passed. No default switch or deployment; mutation and disturbed studies remain pre-deployment checks. |
| 2026-10-07 | `wepp_261007`, `wepp_261007_hill` | `wepp-forest` source commit `669ff4106a4158e49dc79e038026e4d63a489923`, recut and merged to default branch `wepp_260430_negmeltfix_comparator` by `7e49614c` | watershed `ad5ef3e31be7e6da2517567fb211fe350cb7ff0ea9320282368182cb6157127b`; hillslope `cba2927f489a324774180164f1b8065118fb3a1fa6b64737710b46b0f96036df` | Combined channel hydrograph volume repair and surface-return peak estimator release. Vendored sidecars: `7596787c0eafd75cec2c1287d3ac1b8c9ae21d3a696ff049947c851078e5a214` and `678242f7ab030f5b08e8be49945235dafbb95c8de8888db654141cbe24d6b60b`. Source-side evidence: focused tests 7/7, full pytest 92/92, source and release host smoke, hillslope watchlist 12/12, artifact policy, JSON/hash checks, `surpeak_` symbol checks, and system ELF interpreter checks. WEPPpy evidence: provenance, host smoke, and runner/output regressions passed. |

## Withdrawn Releases

- `wepp_261009` and `wepp_261009_hill`, including their sidecars, were
  replaced by `wepp_261010` on 2026-10-10 at Roger's explicit request.
  They were never deployed. No silent alias or production migration is added;
  local projects selecting 261009 must select 261010 and regenerate matching
  hillslope passes. Historical provenance and the release-log row are retained.
- `wepp_261007` and `wepp_261007_hill`, including their provenance sidecars,
  were removed from the WEPPpy vendor set on 2026-10-09 at operator request.
  The release had not been deployed to wepp.cloud, so direct removal requires
  no production migration. Existing binary defaults remain unchanged; the
  release log and completed study artifacts are retained as historical evidence.
- `wepp_260727` and `wepp_260727_hill` were removed from the WEPPpy vendor set
  on 2026-08-05. Their sidecars select the HBP pass family exclusively, so the
  generated `H*.hbp` files cannot participate in workflows that merge them with
  legacy flat-file `H*.pass.dat` inputs, including AgFields integrated-watershed
  assembly when another required source remains legacy-pass.
- Do not mix pass families or silently substitute another executable. A project
  that persisted `wepp_260727` must explicitly select an installed compatible
  binary and regenerate the dependent hillslope/pass artifacts before watershed
  integration.
