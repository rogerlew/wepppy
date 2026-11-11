# Exact-image advisory dispositions

**Status**: M1 review in progress; activation remains blocked.

## Evidence identity

The subject is baseline image
`sha256:1819856096bf838cdf32fe52b035d13971e6aaa3aad4652b63759926fae23d74`,
built from `2041fb8e2`. M0 was subsequently accepted at checkpoint `d4b175436`.
That checkpoint adds documentation and one test correction; it does not change
dependency inputs. Because the Dockerfile copies the checkout, the image still
belongs to its original revision and cannot be relabeled as a checkpoint build.

Raw evidence remains under the protected store's
`.local/dependency-security/evidence/baseline-2041fb8e2-20261111/`.
The authoritative no-symbol scan is `reports/grype-classified-all.json`, SHA-256
`dc77eb289908012c12baf8121ff890ba79a3cee3c7cdf2ac5e1907faad1e867e`.
Its matches and ignored matches are exactly equal to those in the original scan;
scientific-file classification changed analysis coverage, not findings.

The itemized `disposition-review-v3.json`, SHA-256
`1673d77c194955999f02f2fa392653e691aa392ffa0186f2ad776bbe2608bf46`,
retains every source record, package/version, artifact ID, paths/layers, advisory
aliases, affected/fixed versions, severity and scanner suppression. Alias
normalization is scoped to an artifact identity and preserves all source rows.
The retained generator and evidence hashes support independent readback. Version
1 remains retained; version 2 adds the Brotli command receipts and build log
needed to bind the patch provenance to the actual image. Version 3 adds the
reviewed MariaDB proposals and links the separate npm review. No packet is an
approval.

## Review accounting

| Category | Source rows | State |
| --- | ---: | --- |
| Header-only `linux-libc-dev` | 327 | Proposed not affected; itemized review pending |
| Exact patched Python Brotli copies | 3 | Proposed not affected; itemized review pending |
| Absent MariaDB server/tools or config-only artifact | 109 | Independently supported not-affected proposals |
| Other records | 2,782 | Pending applicability and repair review; blocking |
| Total | 3,221 | 3,133 artifact-scoped alias groups; no clearance |

The header proposal is confined to `linux-libc-dev` 6.12.116-1: retained package
contents contain UAPI headers rather than the affected executable implementation.
It does not clear the host kernel, another binary package, or every advisory
sharing the Linux source-package name. Scanner suppression is retained as source
data and is not an approval.

The three Python Brotli artifacts are built from commit
`d89c4b1c52e25ddafe047bc78bbee5c1e24b1809`, containing upstream decoder fix
`0ed4268a4401abcb4472096340477cf4af7d1a2b`. Exact source, build log, installed
RECORD and binary hashes agree. This supports the narrow GHSA-9v8h-qqgm-4m35 /
CVE-2026-111497 proposal despite version metadata 1.2.0. Pillow and PyCurl bundle
separate Brotli libraries and remain outside that proof.

Independent review examines all 112 MariaDB rows and supports 109 absence-based
proposals. Three CVE-2026-44172 client/dev/compat rows remain blocking: both the
exact shared library and explicitly static-linked archive report Connector/C
3.4.9 but fail the upstream Big5 escaping regression. A bounded positive control
using the upstream unsigned-byte correction passes; no installed library is
changed. Version readback alone therefore cannot override the advisory finding.
The private `mariadb-correctness-review/manifest.json` binds the source, binary,
ownership, failed/positive probes and itemized review, SHA-256
`82fe6f93abc9e07e70ddb6aafb3b20752603808f370e36ff8eaec533daf0ed59`.

## Blocking coverage and repair work

The database build timestamp is outside the approved 24-hour window. All scans
here support triage only. The 2,099 executable analysis gaps require native
coverage reconciliation; Python distribution ownership alone does not establish
the identities of libraries embedded in a wheel.

Supplemental Go-symbol scanning removes 53 findings before Grype's match and
ignored-match output. Those records remain in the authoritative no-symbol report
and in `symbol-filtered-primary-records.json`. Symbol filtering cannot silently
shrink the disposition universe.

Actual application call sites include Authlib in
`wepppy/weppcloud/utils/oauth.py` and its security callback, Requests throughout
the climate and acquisition clients, and Starlette in browse, query, upload and
shape-converter services. These are investigation entry points, not blanket
reachability conclusions. Candidate upgrades and missing focused coverage are
recorded in `20261111_upgrade_research.md` and
`20261110_focused_validation_map.md`.

The separate exact-lock npm audit retains 19 dependency findings (4 High,
11 Moderate, 4 Low), with zero production-only findings. Independent review
supports not-affected proposals for this exact runtime and recorded static build:
the packages are absent from the runtime and outside the fixed copy-only build
and reviewed Linux install-lifecycle call paths. This is not a dev-dependency
waiver, and PR/CI execution remains pending. The itemized review covers 19 rows
and 22 advisory aliases in `npm-audit/review/frontend-reachability-review.json`,
SHA-256 `9eec2dea6374a516faf5ce17fe11231687461ff6711e0ccf3541edfbc03e1aaa`.
No accepted-risk record, fixed disposition, M1 acceptance, or production rollout
is implied by this review packet.
