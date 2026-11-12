# Dependency evaluator component — 2026-11-12

Status: local component approved by independent security and QA review; not wired to collection, CI,
or deployment. No image clearance, M3/M4 completion, or advisory waiver.

`tools/security/evaluate_dependency_evidence.py` verifies a private, manually
retained manifest-schema-1 bundle. Trusted callers must independently supply
manifest, policy and disposition hashes plus exact source/image/lock identity.
Candidate-controlled hashes are not approval. The implemented policy is exactly
`2c381b5cf53b40278a1145d8bbf32e314647be8328010aaa9005ae414cd4e6be`;
other policy revisions fail rather than inheriting hardcoded semantics.

Required roles are `syft.json`, `grype.json`, `npm-audit.json`, `package-lock.json`,
`inventory.json`, `receipt.json`, and the retained `vulnerability.db`. The bundle
must be private (0700 directory, 0600 regular files). Read and hash the bytes
actually parsed; reject symlinks/nonregular files and changed reads.

The receipt binds successful refresh/scan/inventory commands, source revision,
clean state, before/after database/SBOM/lock hashes, audit report hash, full npm
command/effective configuration, timestamps, exact tool versions/binary hashes,
and static-build lock identity. Database metadata is read from retained SQLite,
not merely trusted from report text. Freshness remains 24 hours with five minutes
future skew; no CLI clock override exists.

## Scope and disposition rules

Qualified Syft configuration is pinned in full. Grype configuration is pinned
in full except the output filename, which does not affect matching. The recorded
configurations are in `tools/security/scanner_scope.json` and hash constants bind
them to the qualified reports. Symbol-filtered and partial scans fail.

Direct Python/Debian name/version/path readback must be present in SBOM artifacts.
Python uses PEP 503 normalization. Native executable paths reconcile both ways,
are nonempty, and direct hashes agree with available SBOM hashes. Unidentified
executables require separately approved, exact-hash coverage with owner, reviewer,
evidence and embedded-library advisory coverage. Parser errors remain failures.
The future collector must prove actual image/native sentinels, not invent an
empty inventory or substitute package ownership for embedded-library coverage.

All Grype matches and ignored rows are retained. Evaluate the highest severity
across primary and related advisory records; Unknown also requires review. This
is conservative conflict handling, not an automatic applicability conclusion.
A low vendor score cannot silently waive a higher related score. Dispositions
bind exact installation/location and the complete ID/namespace/severity set.
Daily EPSS metadata does not change a Grype identity; path/alias/severity changes
do. npm disposition keys conservatively bind the complete supported row because
it also represents transitive dependency relationships.

Full npm dependency count alone cannot prove scope: the actual retained all and
production-only reports both describe 490 dependencies. The trusted receipt must
bind the full-scope command, effective omit/include settings, exact report bytes,
and unchanged lock. A future producer must create those observations from its
real invocation with controlled configuration; a candidate-written assertion is
not independently trusted evidence.

No still-matched row can be labeled fixed. Accepted risks require owner/reviewer,
rationale, evidence, control, trigger and valid dates, with a maximum 30-day span.
No real advisory exception was created. Low/Negligible rows remain counted.

## Independent review corrections

Security and QA reproduced false passes in early drafts: omitted native files,
partial catalogers, production-only audit, malformed native approvals, ignored
file parser errors, lower primary severity, missing advisory identity and empty
native universe. All received regression tests and explicit checks. A real
backports.zstd inventory mismatch prompted proper PEP 503 normalization.

The focused synthetic suite exercises malformed/stale/tampered evidence and
approved-format fixture decisions. These fixture approvals are not real risks.
The retained real crypto candidate remains blocked by unresolved advisories and
native coverage; no passing evaluator receipt is claimed for it.

## Remaining integration

Implement the pinned confined producer, exact-image/native inventory collection,
protected CI handoff, and pre-disruption deployment hook. Verify actual retained
bundle/import/evaluation and missing/stale/blocking failures before activation.
Then rebuild the final candidate and run M4's exact full commands and reviews.

Final focused receipt: 35 tests passed, two dependency deprecation warnings,
9.81 seconds. Security and QA approved the remediated component with no open
medium/high findings, conditioned on independently trusted hashes and producer
provenance. The latter is still an integration obligation, not implemented proof.
