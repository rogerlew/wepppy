# Scanner evaluation - M0 source review

**Status**: Syft/Grype approved by security review for confined M1 collection; final gates open  
**Reviewed**: 2026-11-11 UTC by independent `security_reviewer`  
**Governing standard**: `docs/standards/dependency-evaluation-standard.md`

**Retained raw evidence**:
`out/security-audit-20261110/f6/m0-20261111T0505/scanner-trial/` (gitignored,
private). Original commands refer to `/tmp/wepppy-security-m0/scanner-trial/`;
that path now links to the retained directory. Receipt command strings and
artifact bytes/hashes were preserved during relocation; only permissions were
normalized. Relative raw-artifact filenames below use this retained directory.

## Decision and limits

The final M0 security recommendation is pinned Syft 1.57.1 followed by Grype
0.121.3 under the confined image-only commands and coverage requirements in
section 7. This approves tool choice for M1 evidence collection, not policy-owner
ratification, CI/deployment integration or a release. The following early Trivy
evaluation is retained to explain the evidenced escalation.

Trivy v0.76.2 was the initial single-tool candidate for image inventory,
CycloneDX SBOM, and Debian/Python advisory reports. npm's existing lock
audit remains a separate input. That initial source/documentation recommendation was not
approval to integrate the scanner or a claim that it is vulnerability free.

The Linux amd64 release archive SHA-256 is
`bc0fc726e017b8927a62b2d3531d7a84ee01769daf5c99ed866dced54089fdbf`.
The [release API](https://api.github.com/repos/aquasecurity/trivy/releases/tags/v0.76.2)
independently reported that digest, 52,714,130 bytes, publication at
2026-11-05 12:50:25 UTC, and an immutable release. The API digest identifies the
proposed download; it does not replace verification of downloaded bytes and
release provenance. Retain verification against the expected upstream workflow
identity and binary version/hash before first execution.

## 1. Precedent and overlap

A renewed search of `.github`, `tools`, `docs/standards`, and the July Dependabot
package found no existing Syft, Trivy, Grype, OSV Scanner, or pip-audit
integration. None resolved on `forest` during initial command discovery.
The dependency-standard precedent registry contains no scanner evaluation.

Docker supplies artifact identity/export; `dpkg-query` and Python metadata
supply direct inventory; npm supplies the frontend audit. None supplies a
complete installed Python/Debian advisory matcher or standard image SBOM.
The owned geospatial components do not overlap this build/security function.
No application dependency, daemon, database service, or scientific-path change
is warranted. Scientific benchmarking is inapplicable; scan time, memory, disk
and egress measurements remain required for deployment suitability.

## 2. Capability comparison

| Candidate | Evidence-backed capability | Decision |
| --- | --- | --- |
| Trivy 0.76.2 | Image tar input, CycloneDX, JSON reports; installed Python metadata and Debian support | Qualify first; one distribution and scanner schema |
| Syft 1.57.1 + Grype 0.121.3 | Archive/SBOM workflow, standard SBOM plus vulnerability JSON | Reserve alternative if qualification exposes a material gap; two distributions are unnecessary before that evidence |
| pip-audit | Python-focused audit | Insufficient alone for Debian/image coverage |
| OSV Scanner | No repository-approved exact-image implementation found | Not selected; no evidence here establishes a smaller complete replacement |

Trivy's [image documentation](https://trivy.dev/docs/latest/target/container_image/)
supports archive input and SBOM output. Its
[Python](https://trivy.dev/docs/latest/coverage/language/python/) and
[Debian](https://trivy.dev/docs/latest/coverage/os/debian/) descriptions are
capability claims to verify against this image, not coverage receipts.
The tagged [report type](https://github.com/aquasecurity/trivy/blob/v0.76.2/pkg/types/report.go)
contains `Metadata.ImageID`; its
[database implementation](https://github.com/aquasecurity/trivy/blob/v0.76.2/pkg/db/db.go)
uses separate metadata including `UpdatedAt`, `NextUpdate` and `DownloadedAt`.
Capture/hash the database bytes and metadata actually used. `DownloadedAt`
alone does not prove advisory freshness.

Vendored source without package metadata, the Python interpreter, downloaded
binaries and native extensions still need explicit inventory. Distinguish
installed packages from copied lockfiles, source fixtures and duplicate metadata.
Neither a zero count nor a recognized OS proves `/opt/venv` coverage.

## 3. Dependency tax and supply-chain history

All three tagged projects use Apache-2.0 and distribute Go executables; they need
no application Python install. These source `go.mod` counts cover listed modules,
not the executable's precise linked-module closure.

| Release | Archive bytes | Listed Go modules (indirect) | Tagged go.mod SHA-256 |
| --- | --- | --- | --- |
| Trivy 0.76.2 | 52,714,130 | 475 (350) | `fd931d9b670a0173e962fef43268ac8ff8b6bbf22bd600d9617e61abae8f1897` |
| Grype 0.121.3 | 32,643,999 | 352 (278) | `991ba8848e008fc175015f36db2e5d59d1e79bee432e0b2446e8f332b1241deb` |
| Syft 1.57.1 | 31,432,061 | 337 (239) | `d3d12da68a820beb7a372077ca24668930546c98842dd44c1d94ed62906839f7` |

Sources: tagged `go.mod`/`LICENSE` and release APIs for
[Trivy](https://github.com/aquasecurity/trivy/tree/v0.76.2),
[Grype](https://github.com/anchore/grype/tree/v0.121.3), and
[Syft](https://github.com/anchore/syft/tree/v1.57.1), read 2026-11-11.
Alternative archive hashes independently verified from the API:
Grype `e9da18cc1429e786722e32161288103600efffd8e483c90761f90485bd1bec85`;
Syft `bf52519eb57f675d47c07d43213cb6dff6449f3d6d1147ff6701ed91f44eef0c`.
Both releases were published 2026-11-09 and marked immutable.

Known upstream history informs the execution boundary:

- Trivy's March 2026 compromise affected executable 0.69.4 and historical Action
  tags. Proposed 0.76.2 is outside that executable range. Use no floating setup
  Action or installer.
  [GHSA-69fq-xp46-6x23](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23)
- Trivy database/archive traversal affected versions below 0.71.1; plugin
  traversal below 0.72.0; Helm allocation exhaustion below 0.71.0; registry
  credential leakage below 0.51.2. These ranges exclude 0.76.2 without proving
  its entire dependency closure clean.
  [Upstream advisories](https://github.com/aquasecurity/trivy/security/advisories/)
- Grype JSON credential disclosure affected versions below 0.104.1. Syft's
  allocation issue affected versions below 1.52.0, temporary-file cleanup below
  1.42.3, and attestation-password disclosure 0.69.x. Proposed alternatives are
  outside those ranges.
  [Grype advisories](https://github.com/anchore/grype/security/advisories/),
  [Syft advisories](https://github.com/anchore/syft/security/advisories/)

These maintained Aqua/Anchore projects have recent releases; corporate backing
does not establish bus factor or availability guarantees. Precise maintainer
concentration, annual breaking-change counts, and binary dependency CVE exposure
remain unmeasured. Pin the CLI and validate fixtures at each update. Keep the
application independent of scanner formats through the repository-owned evaluator.

## 4. Operational qualification

Separate database refresh from archive inspection. The trusted host exports one
explicit image ID. A non-root scanner receives that read-only archive and only
job-specific cache/output directories, with dropped capabilities, no privilege
escalation, no credentials, no Docker socket, and no project/runtime mounts.
Refresh uses documented [database sources](https://trivy.dev/docs/latest/configuration/db/);
inspection uses the exact refreshed database with network disabled. Do not
inherit ambient scanner configuration, plugins, ignore files or VEX files.

Qualification must retain actual commands and evidence for:

1. Release/hash/provenance verification and version readback; executable
   dependency inventory and advisories, including the bundled Go runtime.
2. Standard SBOM/full JSON from an exact disposable archive; installed
   Python/Debian sentinel reconciliation with direct inventory.
3. Report image-ID equality, database-byte identity/size/freshness, and cold/warm
   time, peak memory, temporary disk and egress measurements.
4. Missing/corrupt archive, failed refresh, stale/missing DB, malformed report and
   synthetic blocking finding. Each must prevent approval without touching the
   running stack. Scanner exit zero with findings is not policy success.
5. Resource bounds and cleanup restricted to job-owned files/container; prove
   the scanner cannot read a host-secret sentinel or control Docker.

The primary agent ran the private qualification trial at the original temporary
path above and retained it under `out/`. This reviewer independently parsed its
receipts, recomputed the archive/report/database hashes, and reconciled the
SBOM's Debian inventory. Verified boundaries:

- Release archive hash matches the pin. The retained `gh attestation verify`
  result binds that digest to
  `aquasecurity/trivy/.github/workflows/reusable-release.yaml@refs/tags/v0.76.2`,
  OIDC issuer `https://token.actions.githubusercontent.com`, GitHub-hosted runner,
  and source commit `3f6334d223b52188324af3b9923b4249cd206652`.
- The scanner operated as UID/GID 1000, network disabled, read-only root,
  capabilities dropped, no privilege escalation, 2 GiB memory/2 CPU limit,
  512 MiB temporary filesystem, and only the executable/archive/cache/reports
  mounted. No Docker socket or runtime mounts were supplied.
- Redis fixture image
  `sha256:9823645c452a9a994f575ed238e1a4f67365acbf8e842db769060820fab06449`
  produced schema-2 JSON in 1.31 seconds and CycloneDX 1.7 in 0.49 seconds,
  both exit zero. The JSON image ID matches. All 89 direct `dpkg-query`
  package/version pairs match 89 SBOM library components; the remaining
  component identifies the OS. Its 224 findings concern this fixture only.
- A refresh initially failed on untrusted TLS roots; mounting the public CA
  bundle allowed refresh without disabling verification. Database schema is 2,
  `UpdatedAt` is 2026-11-10 19:01:23 UTC, size 1,759,350,784 bytes, SHA-256
  `cf7fa3086682e8f77298ca8178419a530f97d7c4bd3ac203a64f2977f82e94a6`.
- SBOM SHA-256:
  `ba02c5777a018caa4b63cbfe07f30eb005b760ad60a5f60c88ffff670499c03d`;
  scan SHA-256:
  `ed0031ba72c7aa5c0deb804a92a4806de21d4b81e93780a05bf9ba59a04d925f`;
  attestation receipt SHA-256:
  `df1607aab205cdd4a49d07d6331333c9548e864c1bfb7d590615659c730ff385`.

Redis-image qualification is not common-image or Python coverage evidence.
Later trials covered Python inventory, malformed input and the scanner binary,
as recorded below. Peak-memory measurement remains open. The writable DB cache
also requires pre/post database hashes or a read-only DB mount before claiming
the database was unchanged during inspection. Exact common-image coverage belongs
to M1. The trial's runtime image is a fixture, not an approved scanner runtime.

Tooling rollback removes only its disposable files and pinned executable or
container. Never remove unrelated images/cache state. Operational fit and full
dependency-tax closure remain open, as does the owner policy decision.

## 5. Additional qualification and advisory triage

The development-image trial scanned
`sha256:b32d1c74915c7f7235c4f1bd02ff8e25808be7c8bac665e925a01785bc9f9afa`
in 21.43 seconds under the same 2 GiB/2 CPU limits. The primary agent's direct
`/opt/venv` inventory contains 324 unique normalized name/version pairs, all
present in the scan. The scan contains 363 image-wide Python name/version pairs
across 385 path records, including build-cache metadata. This establishes
inventory coverage for that development image; it is not a production build.
A malformed archive returned exit 1 and produced no report. Evidence-file modes
were normalized to 0600 beneath 0700 directories.

### Scanner self-advisory: GO-2026-5932

An initial filesystem-mode self-scan found no language files and is invalid as
binary audit evidence. The subsequent rootfs-mode scan identified the Go binary
and one advisory: `GO-2026-5932`, `golang.org/x/crypto v0.58.0`, severity UNKNOWN.
Build metadata names 380 dependency modules and Go 1.27.3. The report's
`Status: fixed` describes upstream fix availability, not this binary's status.

**Independent disposition: not affected for the exact executable below because
the affected OpenPGP package is absent from its linked-package evidence.** This
does not downgrade UNKNOWN or create a general exception for `x/crypto`.
The [official advisory](https://pkg.go.dev/vuln/GO-2026-5932) scopes affected
imports to `golang.org/x/crypto/openpgp` and its six child packages. Evidence:

- Executable SHA-256:
  `6a972c69606c7b3ea4c6bdcc6fc9332ea9ad38381624310c1e85cc77345909f3`.
- `go tool nm` cannot read this stripped executable. A retained Go standard-
  library `debug/elf` + `debug/gosym` reader instead parsed `.gopclntab` and
  recovered 208,314 function names. None names the affected path; 552 name
  `github.com/ProtonMail/go-crypto/openpgp`, and 579 name `x/crypto/ssh`.
  A complete byte search also finds zero affected-path occurrences, while
  finding 665 ProtonMail OpenPGP occurrences.
- All 1,636 `.go` files in tagged Trivy source contain no old OpenPGP import.
  Linked build metadata identifies `go-git/v5 v5.19.3` and
  `ProtonMail/go-crypto v1.5.2`. Tagged go-git
  [commit verification](https://github.com/go-git/go-git/blob/v5.19.3/plumbing/object/commit.go)
  and [tag verification](https://github.com/go-git/go-git/blob/v5.19.3/plumbing/object/tag.go)
  import the ProtonMail fork, consistent with the linked functions.

Reassess this disposition whenever the executable, advisory or build inputs
change. It makes no claim about other advisories in the ProtonMail fork or
scanner runtime image. Retained files under the trial directory:

| Artifact | SHA-256 |
| --- | --- |
| `reports/scanner-self-rootfs.json` | `b5eb007a6d708c564875b69fad23b27477c44019011474f5a3c8f5c9fca25209` |
| `GO-2026-5932.json` | `bde8769150ec1368d9a8dbd61fbbde52296de692c57147e02e3ae295e1981f11` |
| `linked-functions.txt` | `9a13cefe5713c7471f1187d924fdd1207c2c9ad334926c4614778d9edf474d6e` |
| `list_go_functions.go` | `8a5aeddbedd7a5051ec966175f75f1e7a3113b85403d533cae5bd6b0162c8fcc` |
| `source-openpgp-search.json` | `d45414083a23d1363d88731743330f59be146ac509588898b460530e4a053786` |
| `trivy-v0.76.2-source.tar.gz` | `ea2670e94696508b12687e1f8ac35a6fe529893e351b7e38362c4a385ff2db9a` |

### Confirmed matcher gap: GDAL CVE-2026-8212

The development scan exited zero while logging two Python constraint errors for
`<3.13.0RC1`. Its JSON inventories GDAL 3.10.2 at both installed metadata and a
build-cache metadata path, but contains no Python match for `CVE-2026-8212`.
The retained database contains that advisory with fixed version `3.13.0RC1`,
affected constraint `<3.13.0RC1`, and alias `GHSA-r5m4-5vww-w9f5` at byte offset
841219468. The [upstream advisory](https://github.com/advisories/GHSA-r5m4-5vww-w9f5)
identifies PyPI GDAL and the same constraint. Debian matches for that CVE do not
repair the missing Python result or establish complete Python matching.

This is a confirmed failure mechanism in tagged
[`compare.IsVulnerable`](https://github.com/aquasecurity/trivy/blob/v0.76.2/pkg/detector/library/compare/compare.go):
lines 30-34 log a matching error and return false. The
[PEP 440 matcher](https://github.com/aquasecurity/trivy/blob/v0.76.2/pkg/detector/library/compare/pep440/compare.go)
supplies the observed constraint error. Receipt `gdal-matcher-gap.json` has
SHA-256 `033b9b040b532992d7a7f1581d4d72d7df577aef362aa218d04a86bfd4e8bb96`;
extracted `trivy-compare.go` has SHA-256
`771aec23de1c298d3b47630aea3f68325699d2b0d012c844470d4f7789181f1f`.

**Adoption blocker:** do not accept exit zero as complete evidence. The future
wrapper must reject matching/analysis errors, and qualification requires a
corrected scanner/database or evaluated alternative that detects this retained
case. Do not edit the accepted database, suppress the warning, or treat the
not-affected self-advisory disposition as authorization to ignore this defect.
The simpler single-tool trial has now supplied concrete evidence justifying
evaluation of the reserved Syft/Grype alternative if an upstream repair is not
available.

## 6. Syft/Grype escalation review

F6-S5 is retained evidence that the simpler candidate misses an actual required
matching condition. Qualify Syft 1.57.1 plus Grype 0.121.3 against the same
development-image archive and GDAL advisory. This is a replacement candidate,
not approval to deploy two competing scanner stacks or accept whichever report
has fewer findings. Keep Syft's native JSON alongside a standard SBOM so Grype
can consume its full package/source metadata; verify both carry the same image.

### Distribution and verification evidence

GitHub artifact-attestation lookup returned 404 for these releases. Upstream
[documents signed-checksum verification](https://oss.anchore.com/docs/installation/verification/)
instead. Both checksum bundles verify with the exact corresponding signer
`https://github.com/anchore/<tool>/.github/workflows/release.yaml@refs/heads/main`
and OIDC issuer `https://token.actions.githubusercontent.com`. The tagged
release workflows use `workflow_dispatch` to create the requested version tag;
the main-branch signing identity is consistent with that process. An initial
guessed tag-specific signer failed verification and was retained. Verification
was not weakened to a wildcard identity.

This reviewer independently read the certificates and successful command
receipts and recomputed both downloaded archive hashes against their signed
checksum lines. The exact archive pins remain those in section 3. Extracted
executable hashes are Syft
`de3982edbbc250c4a40764c7b1f30bbf54b681f9b99391ee6b85bfdfa5d4dffe`
and Grype
`30f8f7de5dda71952a20d4955034d30a081a5d10e6bd00d67ce78b56fd0251dc`.
Successful command receipts have SHA-256:

- `syft-signature-receipt.json`:
  `71783b8001e9aaaf33f3c169a3c0c21bfae991dff8105a454e019a2380a1e51b`.
- `grype-signature-receipt.json`:
  `17ca281d10d9ba736765f488431ed4f0d7afe0411afea61d83f3d673c69e983f`.

Cosign 3.1.4 was downloaded solely as the confined verification tool. Its binary
SHA-256 is `424e2c97d0b45fd7a6b608a87f090f35633f4c23ece5f092d48bba11aaf4bbfa`;
the independent [release API](https://api.github.com/repos/sigstore/cosign/releases/tags/v3.1.4)
readback confirms 145,688,404 bytes, publication 2026-10-20, and immutable release.
No GitHub attestation was available for this verifier. Its bootstrap trusts the
GitHub HTTPS release/API hash, rather than an independently pretrusted signature
chain. Keep that limitation explicit when selecting a supported verifier for
CI/deployment. The trial uses no host-installed Cosign or runtime dependency.

### Additional tax and acceptance conditions

The alternative adds a second pinned executable and a separate native-SBOM
consumer boundary. Release verification also requires a temporary verifier.
`go version -m` inventories retained as `syft-buildinfo.txt`,
`grype-buildinfo.txt`, and `cosign-buildinfo.txt` identify respectively 295, 318,
and 253 embedded dependency modules; each binary reports Go 1.27.3. These are
per-binary counts with overlapping dependencies, not a disjoint sum. Fresh
binary self-scans and dispositions remain required. Section 3 records relevant
upstream security history; it is not a complete transitive CVE audit.

The extra database download/cache, report schemas, signatures, scan time and
temporary disk all need measured receipts. Pin the database schema and scanner
versions together; no automatic tool update belongs in the deploy path. Remove
only job-owned tools/cache on rollback. Production images and Python dependencies
remain untouched by qualification.

Source review does not establish that Grype fixes F6-S5. Both candidates depend
on `aquasecurity/go-pep440-version v0.0.1`, although Grype's
[`pep440Version`](https://github.com/anchore/grype/blob/v0.121.3/grype/version/pep440_version.go)
uses version parsing/comparison instead of Trivy's failing specifier parser.
Grype's [`VersionCriteria`](https://github.com/anchore/grype/blob/v0.121.3/grype/search/version_constraint.go)
also contains error-to-no-match behavior, including debug-level diagnostics.
Retain debug logs, reject relevant analysis/matcher errors, and prove that the
same GDAL package/path produces `GHSA-r5m4-5vww-w9f5` or its CVE alias. Do not
infer success from exit status or absence of warning-level output.

Retained source files `grype-pep440_version.go` and
`grype-version_constraint.go` have SHA-256
`88461a514063d5fc7c1c6fb8b8ab57851787d163a0a7c8787d25fea748ff85be`
and `2aa4ca8c609ad192fbbc52c3c10072ed348bea8b4db4bf75000f0715154eaf84`.
Signed distribution identity is evidenced. Subsequent operational results and
remaining adoption conditions follow.

## 7. Alternative qualification result and remaining risks

**M0 security decision:** use Syft 1.57.1 plus Grype 0.121.3 for confined M1
evidence collection with explicit Docker archive then native-SBOM input. The pair
covers the retained
GDAL matcher failure and reconciles the development image's installed inventory.
The scoped security tool-choice review passes; owner/storage/full-baseline
requirements still govern M0, and common-image M1 acceptance remains open.

Independent readback of the primary agent's trial confirms:

- Syft completed in 80.95 seconds and Grype in 60.87 seconds, both exit zero.
  Both identify development image
  `sha256:b32d1c74915c7f7235c4f1bd02ff8e25808be7c8bac665e925a01785bc9f9afa`.
  Recomputing the direct-inventory comparison matches all 324 normalized venv
  Python name/version pairs and all 475 Debian name/version pairs.
- Grype reports `GHSA-r5m4-5vww-w9f5` with related `CVE-2026-8212` for GDAL
  3.10.2 at `/opt/venv/.../gdal-3.10.2.dist-info/METADATA` and cache locations.
  Retained debug logs contain zero `match constraint error` messages.
- The report contains 3,006 matches and 330 `ignoredMatches`, all latter entries
  covering `linux-libc-dev` under the default exact-indirect ignore rule.
  These are qualification counts, not production findings or risk dispositions.
- Database schema is v6.1.10, built 2026-11-10 06:21:20 UTC. The descriptor
  retains provider capture timestamps and immutable archive URL with SHA-256
  `f536af5882d8e03ad3e3ea5b32b3fc1965d55321ddab67ad7a5d7aeec3725190`.
  At this trial it was about 23 hours old, close to the proposed 24-hour limit;
  do not reuse it later merely because that earlier evaluation passed.
- Syft catalogs 2,527 artifacts; 38 binary records lack package URLs. These
  include Windows launchers and PuLP's CBC executable. They require unmanaged
  coverage/disposition in M1. All installed Python/Debian pairs are represented.

Native SBOM SHA-256 is
`92ed14352698b4f106d66757316f28a4c948384fa715985eebb8e0ae899765c0`;
CycloneDX SHA-256 is
`3abe8e67ef46a1032cb04ad79070dcae11c258a07664ecae8e65c9b3b4265d91`;
Grype report SHA-256 is
`582fda0ba80be60ca62fee290936a539d0149d16ace96bb478e9fbcc5a0c63dd`;
reconciliation SHA-256 is
`fffb7b6b304d65299191ca14e8ac5eb5e1f3c4f84ae33308008a69c7422be4d7`.

### Preserve all suppression evidence

The qualification used `include-matcher-suppressions: false`, so its 330 ignored
records do not exhaust internal suppressions. Pinned
[`vulnerability_matcher.go`](https://github.com/anchore/grype/blob/v0.121.3/grype/vulnerability_matcher.go)
lines 176-181 append otherwise discarded hard-coded/distro suppression records
when this option is true. The audit wrapper must set it **true** and disposition
the union of `matches` and `ignoredMatches`, retaining suppression reasons.
[`--show-suppressed`](https://github.com/anchore/grype/blob/v0.121.3/cmd/grype/cli/options/grype.go)
is table-only; it does not expose additional JSON records. Setting that flag
cannot replace `include-matcher-suppressions`.

The follow-up scan explicitly enabled this configuration and again produced
3,006 matches plus 330 ignored records, with no additional internal suppressions
for this image. Its report `grype-dev-all.json` has SHA-256
`6e4f8883a9174584d4aa0c30576fc6e434157d575bd5f2b6ce320774a35679ac`.
Keep the setting even though the counts happen to agree for this fixture.

Malformed-SBOM and missing-database trials each exited 1 and left a **zero-byte
JSON output file**. Accepted evidence must require a successful command, valid
schema, correct identities and reconciled inventory; file existence alone is
demonstrably insufficient. Retain `malformed-sbom-receipt.json` and
`missing-db-receipt.json` with their failed output paths.

The Grype log also notes missing Go function symbols and consequent module-level
matching; review possible false positives instead of silently suppressing them.
Syft's cache-directory warning requires explicit writable job-local cache
configuration. Normalize scanner-produced files to 0600 before retention; a
0700 parent currently protects files even when the container creates them 0644.

### Scanner dependencies: explicit dispositions and open conditions

The tool self-scan retained ten records: two per scanner and six for temporary
Cosign. Neither scanner nor verifier may be called advisory-free.

`GO-2026-5932` is **not affected for the exact Syft and Grype executables pinned
in section 6**. The same standard-library ELF method recovered 100,211 Syft and
103,402 Grype function names; neither inventory nor either complete binary byte
search contains `golang.org/x/crypto/openpgp`. Each has 609 ProtonMail OpenPGP
functions. As with Trivy, this disposition is executable-specific and expires
on tool/advisory change; it does not suppress other `x/crypto` advisories.

`GO-2026-6905` has a **scope-specific exclusion for the evaluated M1 commands**;
automated enforcement remains a required M3/M4 condition. The official
[advisory](https://pkg.go.dev/vuln/GO-2026-6905) identifies a negative ar-member
length causing `Reader.Read` to panic; no fixed version is named. Both scanner
binaries link that function. Tagged Syft
[`parse_deb_archive.go`](https://github.com/anchore/syft/blob/v1.57.1/syft/pkg/cataloger/debian/parse_deb_archive.go)
uses it when cataloging `.deb`/`.ipk` files and validates only the global ar magic
before reading member headers. This is a real reachable feature of the tools.

The actual development-image descriptor excludes `deb-archive-cataloger`.
Tagged [`package_tasks.go`](https://github.com/anchore/syft/blob/v1.57.1/internal/task/package_tasks.go)
assigns it to declared/directory scope, not image scope. An explicit
`docker-archive` Syft input followed by Grype reading the produced SBOM can
therefore exclude this path without reducing the demonstrated installed-package
coverage. The fixture below now verifies the mode exclusion and real
counterexample. M1 may use those exact confined modes; the M3 wrapper must enforce
them and reject partial parsing, with regression acceptance in M4. Requiring
that future wrapper before selecting the M0 tool would be circular. Do not mark
the whole binary
not affected, permit arbitrary directory/auto-detected targets, or waive UNKNOWN.
If the vulnerable path is required, obtain an upstream repair or an explicit
time-bounded owner risk decision; no such acceptance has been granted here.

Cosign 3.1.4 has scanner-reported High `GO-2026-6860` (`x/net`) and
`GO-2026-6865` (`klauspost/compress`), Medium `GO-2026-6866` (`x/net`) and
`GHSA-j6qf-3m9c-vwj3` (`go-chi`), plus UNKNOWN `GO-2026-6225`
(`docker-credential-acr-env`) and `GO-2026-5932` (`x/crypto`). It was confined to
verification of upstream signature bundles and is not a candidate application
or scanning runtime dependency. These records still require command-specific
triage or a qualified replacement before making it the supported deploy/CI
verifier. The trial's provenance evidence is retained with this limitation;
no general risk acceptance or claim of verifier safety is implied.

### Malformed ar fixture: scope exclusion and recovered failure

The primary agent built a scratch image containing one inert 68-byte `.deb`
fixture: valid ar global/header framing with a `control.tar.gz/` member whose
decimal size is `-1`. Fixture SHA-256 is
`c6611d2654c10c24c3ab380f75d09f520092044fc61b202f4efaed884103dd87`;
image ID is
`sha256:61b021cdf57a42145c49123f3c04616482df5a460314b5dac98a537209875808`.

Default `docker-archive` scanning exited zero, excluded `deb-archive-cataloger`,
and emitted no file unknowns. Forcing that cataloger also exited zero, but the
native JSON **records the triggered panic** in
`files[0].unknowns` at `/fixture/negative-size.deb`:
`deb-archive-cataloger: recovered from panic while parsing file: runtime error: slice bounds out of range [:-1]`.
The absence of stderr or a process crash was not a clean parser result. Pinned
[`generic.invokeParser`](https://github.com/anchore/syft/blob/v1.57.1/syft/pkg/cataloger/generic/cataloger.go)
lines 251-256 recover parser panics, log at Debug and return an error subsequently
stored as file-level uncertainty. Independent artifact readback establishes both
the real trigger and exclusion under the intended mode.

Default/forced native SBOM SHA-256 values respectively are
`c2b683d7bb4ba2a00944976cdf9cf1f8a43c0512d525cd015ab92b8a28e2071c`
and `22e6a73a63ee9c73ecaf18a4e01bcab5f25b16d674a5e7a321d11a85e2ea5627`.
Retained `syft-generic-cataloger.go` SHA-256 is
`c691b391e9cc63c62003244f06f262af7aa2278a504230155341c20aa7ddc3e9`.

The future evaluator must reject parser/analysis failures in native
`files[].unknowns`, not rely solely on command status or logs. Separately, the
development SBOM contains 1,969 file unknowns, all
`unknowns-labeler: no package identified in executable file`, including Python
shared libraries/extensions. These are ownership/coverage gaps to reconcile
with direct interpreter/native/package evidence in M1; they are not the 38
package records without PURLs and must not be silently discarded. The
development scan has no recovered-parser-panic unknowns. Preserve the native
SBOM so its richer uncertainty evidence reaches the policy evaluator.

Self-scan SHA-256:
`28548a211817bd10ae985110c7d829d09b49f36f218e66d13a3e6f8a06ba50fe`;
tool inventory SHA-256:
`ab6c0646b2222c59e1989e591cb8451ac214589e2c237ee378b5d0c88cdcc1db`;
Syft/Grype function inventories respectively:
`4c9ce7f79ee1f0d499598df4f425e49b3d746617559a39eb8db348e714af4510`,
`269635cdb20dc0ee32e1a51e2e54110b76e4b61eea09ec3351c1e2d42f6d7b06`.
The trial also retains the official advisory and tagged source excerpts.

M1 can proceed with the reviewed confined image-only pair once M0's separate
owner/storage/full-baseline gates pass. It must retain native unknowns, all
matched/suppressed findings and direct common-image coverage/resource evidence.
M3/M4 must implement/test mode enforcement, parser/error rejection, supported
verifier treatment, and CI/deploy authority. No production rollout is authorized.

## 8. Common-image scientific `.par` classification refinement

The unchanged baseline image
`sha256:1819856096bf838cdf32fe52b035d13971e6aaa3aad4652b63759926fae23d74`
exposes a concrete filename collision. Independent native-report readback finds
55,980 file records and 17,673 file unknowns: 15,574 Java archive parser errors
on `.par` files and 2,099 unidentified executables. All parser errors are
`java-archive-cataloger: unable to read files from java archive: zip: not a valid zip file`.
The initial native SBOM SHA-256 is
`ced601880be4a9fc4aecfdfbb849dd6587f9ec84b49886ee69d73e72c3f091fc`.
Its zero command exit and installed-package reconciliation do not establish
acceptable analysis; preserve this failed report.

Pinned [`java/archive_parser.go`](https://github.com/anchore/syft/blob/v1.57.1/syft/pkg/cataloger/java/archive_parser.go)
line 37 includes `**/*.par` in `archiveFormatGlobs`.
[`java/cataloger.go`](https://github.com/anchore/syft/blob/v1.57.1/syft/pkg/cataloger/java/cataloger.go)
lines 27-28 pass those globs directly to the Java archive parser. The extension
also names CLIGEN scientific station text shipped in this image. No configurable
Java-only filename exception was found in the tagged `ArchiveCatalogerConfig`.

Private evidence is retained beneath
`/workdir/weppcloud-deployments/.local/dependency-security/evidence/baseline-2041fb8e2-20261111/`:
`analysis-unknowns.json`, `reports/syft-baseline.json`,
`par-file-readback-receipt.json`, and `par-file-readback.json`. The readback
receipt runs Python from the exact image with network disabled, read-only root,
dropped capabilities, no-new-privileges and bounded CPU/memory. It checks all
15,574 paths, including 15,564 climate paths, nine CLIGEN test paths, and one
management-script data path. Independent aggregate readback confirms every file
is regular, UTF-8, contains no NUL, is not recognized as ZIP, has CLIGEN markers,
and matches the retained clean-source hash comparison. Sizes range from 6,630 to
7,292 bytes; the manifest SHA-256 is
`593b9e98a66da5ceda2c4efbb6c12fbe08d997dd00e817ec06a3fd3fe1074812`.
An additional independent local-byte comparison reproduced all 15,574 image
hashes, allowing content inspection of those identical bytes without another
image execution. Full text inspection found only ordinary whitespace and
printable text plus 16 initial BOMs and accented Tenerife station-name letters
(`ñ`, `í`, `ó`, `ü`, `á`). No other control or non-ASCII content was present.

The approved narrow refinement is to classify and retain this exact scientific
data set before a new scan, then exclude only those proven bytes. It is not an
advisory exception, parser-error waiver, or permission to disable Java. Existing
`wepppy/climates/cligen/cligen.py:Station` checks only selected early rows and
uses fixed-width numeric parsing; whitespace splitting gives false failures
when adjacent fields contain negative numbers. The classification must cover
the complete text, expected CLIGEN structure and numeric rows, and ZIP identity.
Check more than initial ZIP magic because ZIP archives may contain a preamble.

Independent inspection of all 79 numeric rows (zero-based lines 3-81) verifies
their expected climate/wind labels and numeric-text alphabet. Of 15,574 files,
15,563 also pass all 12 six-character finite-number fields per row. Tenerife's
first 13 climate rows sometimes omit one leading label space; that explicit
79-character variant accounts for 62 files. Eleven files have existing numeric
formatting anomalies across 17 rows/27 cells: two Tenerife `SD SOL` rows
(`Estacion_11_TEJINA01.par`, `Estacion_97_TAGANANA.par`) overflow the field layout,
and nine `webservices/tests/cligen` fixtures contain embedded numeric spaces such
as `7 .27`. All eleven still have the complete expected labels, numeric-only
data blocks, scientific text metadata, identical source/image hashes, and no
ZIP/binary identity. Their exact paths/hashes/anomalous cells are retained in
private `par-independent-classification.json` with the diagnostic source and
execution receipt. **Classification passes for this exact manifest with these
explicit anomalies; scientific correctness of the station values does not.**
Do not edit scientific data or generalize acceptance of future malformed text
under this dependency-security change.

The retained diagnostic completed in 28.87 seconds with exit zero. Classification
JSON SHA-256 is
`f1de1a36ef669e69d497f391ecfbd17e017a4653b9093175cccd51ba4cfbb847`;
diagnostic source SHA-256 is
`0e01b59e3546bf0780a41e233d19e095035a1803ca778e774c7e9362c03011c8`.
Source, result, execution receipt and log are mode 0600 in the private evidence
directory. This source is a retained review diagnostic, not the M3 wrapper.

Pinned [`image_source.go`](https://github.com/anchore/syft/blob/v1.57.1/syft/source/stereoscopesource/image_source.go)
lines 174-193 applies exclusions globally across catalogers, matches absolute
paths with `doublestar.Match`, and adds `/**` descendants for each pattern. None
of the 15,574 verified paths contains glob metacharacters. A literal file list
is safe after regular-file checks but expands to 31,148 linear patterns. A
compressed absolute per-parent `*.par` pattern set is also acceptable **only if
its complete match set on the exact image equals the verified regular-file
path/hash manifest**, including rejection of matching directories, symlinks and
extra files. Retain the set-equality receipt and effective configuration hash;
repeat content and set validation for every candidate. Do not silently widen a
slow literal list to a directory or extension exemption.

The first 26-parent-glob trial correctly failed set equality: it matched 28,277
paths instead of 15,574, including 12,703 symlinks under
`GHCN_Intl_Stations/all_years`. Replacing that parent's wildcard with the one
validated literal `WukariNRA.par` retains 26 total patterns (25 parent globs plus
one exact file). Independent readback of the revised exact-image receipt shows
15,574 expected and actual paths, no extras/missing/nonregular entries and no
symlink ancestors. Preserve both trials:

- `par-glob-readback.json` SHA-256:
  `223e9b6ffa734ed94ea7cf89da589a45d7591289d3f0e43997f561723cad1d4e`.
- `par-glob-refined-readback.json` SHA-256:
  `9417fb743274a5acf745f4ddda5df0eb5d47babee736b995481e56ff28a524c0`.

These measured match sets support the compact exclusion configuration for this
image. They do not imply that the additional symlinks are malicious or may be
silently removed from the application.

The new scan must use the same immutable image/archive, retain Java cataloging,
preserve installed package/path/version coverage and show no unexpected parser
errors. Keep original and regenerated reports. The separate 2,099 executable
ownership gaps still need direct evidence/dispositions. Future wrapper tests
must cover changed content, a ZIP/binary at an approved path, an extra `.par`,
and configuration/match-set drift. The classified rescan now passes this narrow
qualification: all 2,260 artifact identity tuples are preserved, no Java parser
errors remain, and the same 2,099 executable ownership unknowns remain. Native
classified SBOM SHA-256 is
`4e16ee17e667c7855523171c4d473e104f0ef64871a81b485e31ceb23d755897`;
configuration SHA-256 is
`11ed929c6c6d2ef2b689eee0a6bbb14c58e3a98b1897f9115636512d5a98d3e9`.
The classified Grype report retains the original 2,894 matches and 327 ignored
records (SHA-256
`dc77eb289908012c12baf8121ff890ba79a3cee3c7cdf2ac5e1907faad1e867e`).
This closes the file-classification qualification gap, not the separate
advisory/ownership or future-wrapper acceptance gates.

## 9. Supplemental Go symbol evidence and kernel-header applicability

### Go symbols: retain the original finding universe

The exact-image refinement `golang.capture-symbols: all` with
`golang.use-packages-lib: false` is acceptable as a confined **supplemental
diagnostic**. Pinned Syft
[`golang/config.go`](https://github.com/anchore/syft/blob/v1.57.1/syft/pkg/cataloger/golang/config.go)
documents that the former reads function metadata while the latter disables
the `go/packages` path that can execute Go tooling and access the network.
Continue network-disabled scanning with the validated scientific-data exclusions,
and retain both the native symbol SBOM and command/configuration receipts.

Do not replace the classified scan without symbols as the finding universe.
Grype's pinned
[`gosymbols/qualifier.go`](https://github.com/anchore/grype/blob/v0.121.3/grype/pkg/qualifier/gosymbols/qualifier.go)
uses a package's symbol map to reject advisory imports/functions that do not
intersect it. Missing symbol evidence or advisory import data preserves
module-level matching. However,
[`OnlyQualifiedPackages`](https://github.com/anchore/grype/blob/v0.121.3/grype/matcher/internal/only_qualified_packages.go)
filters failed qualifiers during vulnerability search, before creating match or
ignored-match records. **`include-matcher-suppressions: true` does not preserve
these symbol-filtered rows.** Retain every primary advisory/package/version/path
identity, compare the supplemental result, and keep removed rows pending until
independently dispositioned. The primary agent accepted this guard requirement;
no symbol-based disappearance is an approved suppression.

Function absence can support an exact-binary, exact-advisory **not affected**
proposal only when the advisory specifically identifies affected imports or
functions and the extraction/normalization evidence covers them. Bind the binary
hash, image/path, Go version and architecture, advisory aliases/revision,
complete relevant symbol evidence and reevaluation trigger. A linked function
does not establish a reachable call path; a missing or partial symbol map does
not establish absence. The official
[Go vulnerability tool documentation](https://github.com/golang/vuln/blob/master/cmd/govulncheck/doc.go)
likewise distinguishes binary symbol evidence from source call-graph analysis.

Pinned source has concrete limits requiring case-specific readback:

- Syft [`symbols.go`](https://github.com/anchore/syft/blob/v1.57.1/syft/pkg/cataloger/golang/symbols.go)
  lines 63-76 recovers inlined names as well as top-level functions. Its
  `funcNameTable` silently falls back to top-level names on unsupported headers
  or invalid offsets (lines 206-256). Verify the exact binary's supported header
  and full name-table coverage before relying on absence.
- The same source drops module-less vendored standard-library imports when
  assigning symbols (lines 330-333, 370-374). Compare the advisory against raw
  import/function evidence; do not infer absence from that attribution alone.
- Grype [`golang_symbol.go`](https://github.com/anchore/grype/blob/v0.121.3/grype/pkg/golang_symbol.go)
  normalizes pointer receivers, method wrappers and generic names, but explicitly
  records a missed-match limitation for nested generic parameter groups. A
  relevant normalization ambiguity remains unresolved, not not-affected.
- Native parser errors and extraction unknowns remain blocking analysis errors.
  Inspect per-binary symbol coverage even when no new unknowns appear.

Independent symbol-SBOM readback finds 2,260 artifacts and the same 2,099
ownership unknowns. esbuild's `go1.23.12` standard library has 115 import groups
and 7,642 symbols; git-lfs's `go1.24.4` standard library has 156 and 11,665;
esbuild's `golang.org/x/sys` has two and 22. In contrast,
`/usr/local/bin/docker`'s `go1.21.11` standard library still has **no symbols and
an empty architecture**, despite the requested `all` scope and no new parser
unknowns. Its findings must remain at module granularity. Native supplemental
SBOM SHA-256 is
`d7c013b30ebad73e7d4547069fa251c10fd0788e172030d6ff344637db0585d3`;
configuration SHA-256 is
`9682423397dbe5426867d0b6d49a826b7a6bbd0dbb3cca4235071f75143b09ae`.
No advisory-specific Go not-affected decision is granted by this design review.

The subsequent supplemental Grype trial confirms the retention limitation:
2,841 matches and 327 ignored records, compared with the primary 2,894 and 327.
Independent reconciliation by advisory ID/namespace, package/type/version and
binary paths finds **53 primary records missing from both supplemental
collections** (29 esbuild, 24 git-lfs), with no added records. All are Go
matches, including the esbuild `x/sys` record `GO-2026-5024`. Every one remains
pending in the primary universe. Supplemental report SHA-256 is
`7eea3b7824f360cfafd35c24a0a92717e234727ef31233b2cf54e450eb1008b7`.
Its retained receipt marks the database stale and this run diagnostic-only;
it cannot satisfy a fresh acceptance scan.

### `linux-libc-dev`: a package-specific applicability proposal

Independent readback confirms all 327 ignored records are
`exact-indirect-match` entries on `linux-libc-dev` version `6.12.116-1`, type
`deb`, matched through upstream source `linux`. Grype's
[`ignoreLinuxKernelHeaders`](https://github.com/anchore/grype/blob/v0.121.3/cmd/grype/cli/commands/root.go)
default explains their placement in `ignoredMatches`; it does not constitute a
WEPPpy disposition. Retain all 327, including 11 Critical, 58 High, 49 Medium,
one Low, 58 Negligible and 150 Unknown records.

The exact-image `dpkg-query -L linux-libc-dev` receipt succeeds and retains
2,686 paths: 2,558 `.h` entries plus directories, header aliases and package
documentation. No kernel image, kernel module or `perf` executable appears in
that package file list. The list SHA-256 is
`b8fc3e2ab7f3b2ecd0866b9829581abc764a5c97f4d749ea5f0fdea9f9f51a3f`.
This agrees with Debian's
[package description](https://packages.debian.org/trixie/linux-libc-dev):
userspace development headers sourced from Linux.

These facts support an itemized **not affected for this header package**
proposal when the matched advisory concerns implementation absent from the
package. They do not support a global `linux`/CVE ignore or any assertion about
the production host kernel. Avoid calling every entry a kernel-runtime-only
flaw: [CVE-2026-80670](https://security-tracker.debian.org/tracker/CVE-2026-80670)
concerns the `perf` userspace tool, and
[CVE-2018-1121](https://security-tracker.debian.org/tracker/CVE-2018-1121)
describes process enumeration through procps and kernel interfaces. The narrower
rationale is that the affected implementation is absent from this exact
header-only package; other image components/paths require their own review.

Retain every advisory alias and package/image identity in the disposition
ledger, the file-list evidence and the relevant affected-component explanation.
A direct header/inline/macro defect or a future changed package/advisory must be
reviewed separately. The grouped scope rationale is supported; the itemized
ledger and final advisory acceptance remain pending. No accepted-risk exception
or broad suppression is proposed.

## 10. Python Brotli patch provenance and separate bundled copies

The installed Python distribution reports version `1.2.0`, which falls within
the version range of
[GHSA-9v8h-qqgm-4m35 / CVE-2026-111497](https://github.com/advisories/GHSA-9v8h-qqgm-4m35).
Version alone misses its VCS provenance. Exact-image `direct_url.json` identifies
`google/brotli` commit `d89c4b1c52e25ddafe047bc78bbee5c1e24b1809`.
Independent GitHub comparison confirms the advisory's
[main-branch fix](https://github.com/google/brotli/commit/0ed4268a4401abcb4472096340477cf4af7d1a2b)
`0ed4268a4401abcb4472096340477cf4af7d1a2b` is its ancestor (154 commits ahead,
zero behind). Divergence from release tags or other branch-specific fix commits
does not negate that ancestry.

Exact-image cached `c/dec/decode.c` bytes match the upstream file at the installed
commit, SHA-256
`c74c2d668314fefe645d3ab9bbafe6b6db8a95769ca06dc54d875610c803fc56`.
Source readback confirms the invalid-block-switch error, propagation through
literal/command/distance block-switch helpers, and `BROTLI_SAFE_WITH_STATUS`
calls at each processing site. The initial retained upstream tool output had
one extra trailing newline; the original mismatch and writer output remain
retained, with only that verified added byte removed for exact comparison.
The image source was not modified.

The source file is in a build cache, so it would be insufficient by itself.
Retained `baseline-build-retry.log` lines 2126-2129, 2249 and 2284 explicitly
resolve, build and install Python Brotli from the same full commit. Exact-image
`brotli-installed-readback.json` resolves the imported extension to
`/opt/venv/lib/python3.12/site-packages/_brotli.cpython-312-x86_64-linux-gnu.so`;
its SHA-256
`ddd8f72be33cfbd7a459625555610cdf31b97fbfca8e4cd799085f708a3f4ceb`
matches the distribution's `RECORD`. Its direct URL names the same commit, and
a bounded real compression/decompression round trip passes. This is build and
artifact identity evidence, not a compiled exploit regression test.

Together these records support **not affected by this advisory for this exact
installed Python artifact** because the known fix is already present, despite
the unchanged displayed version. The cached source-package record also retains
the patched source. Subsequent exact-image readback hashes the archived wheel's
extension and the Git checkout's built extension; both are byte-identical to the
installed extension above. The disposition therefore covers the three Python
package records at the installed distribution, cached wheel and cached source
paths only. Keep separate path identities and trigger
reevaluation on image/binary/commit or advisory changes. This is not an
accepted-risk exception or a global waiver for Brotli 1.2.0.

Private evidence hashes:

- `brotli-installed-readback.json`:
  `0cc404dbd0853e9296fd9245a574e6562b4aac274d62a7b280a7ff08a71270b2`.
- `brotli-cache-binaries.json`:
  `af0ebe80f972ad292ad7fb8d64dcc88c042b435cf396bd94fbea53f46052cc1e`.
- `brotli-source-readback-normalized.json`:
  `226f9d92f57aa4e562ee75d0203fbcc380dad3fff41892a7c30011c704892e7c`.
- `upstream-metadata/brotli-patch-provenance.json`:
  `2928a9c653d4e30ad16817d256c2301845a493583ecc834b21a6216f6751d130`.
- `baseline-build-retry.log`:
  `ce3f271e0538e03c3561d73635b8e278072ee6994b66ce6bd92ae14410175f14`.

Pinning the existing Git requirement to this validated commit is the smallest
M2 candidate for reproducibility of the Python package; it preserves the
evaluated source and API rather than requiring an unrelated distribution
change. It still requires the package's candidate build, runtime and regression
gates, and does not remediate separate native copies.

The exact-image executable inventory also identifies
`pillow.libs/libbrotlidec-08d35d18.so.1.2.0` and
`pycurl.libs/libbrotlidec-70b438f9.so.1.1.0`, their common libraries and cache
copies. Python Brotli's VCS provenance says nothing about these independently
bundled decoders. F6-S8 requires component-specific version/patch provenance or
remediation and representative Pillow/PyCurl parity evidence. Their filename
versions raise an applicability question; they do not alone prove the fix is
absent. Keep the shared-advisory assessment open for every confirmed consumer,
including Debian-packaged copies under their own distro/backport evidence.
