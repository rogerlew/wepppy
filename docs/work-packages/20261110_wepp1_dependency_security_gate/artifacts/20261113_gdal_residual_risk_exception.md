# Security-fix release and GDAL residual-risk exception decision

## Operator amendment: security-fix release

Roger authorizes proceeding with the security-fix release while accepting the
remaining dependency findings and unresolved native advisory coverage in the
retained candidates below. This amendment supersedes the narrower release
restrictions below where they conflict. It does not require compiling GDAL or
completing the entire dependency review before deploying these fixes.

The operator's rationale is that the existing deployment already carries these
risks, or greater risks, and delaying fixes for identified vulnerabilities leaves
that exposure in place. A scanner match alone does not establish exploitability.
The existing deployment has not been scanned here to prove a complete
finding-by-finding comparison; this acceptance does not claim that comparison
was performed or that every remaining finding is harmless.

The release scope is source revision
`f6a5b29dc6235c378577651a052b708ed4b0e017` and these retained common images:

| Host | Image ID |
| --- | --- |
| wepp1 | `sha256:91d1173924bcc45643ce87ab5312ef59e394c30dac4b37ac663768281e80b8a2` |
| wepp2 | `sha256:ee3281b7d6d185c75e38fbb98a430486503fc97f1237ab2572de6839fbe99334` |
| wepp3 | `sha256:6957133e3c8d3de9812d0f735cd0b6e4a7cbdf72e5b5cd70b0f9be88ae746bd2` |

Accepted residual scope includes the retained scanner matches and ignored
matches, including Debian and PyPI GDAL findings beyond the original aliases,
and the unresolved native coverage (2,105 paths / 1,201 unique hashes reported
for wepp1). All three images have 1,552 Critical/High/Medium/Unknown matches;
these are review records, not a count of confirmed exploitable vulnerabilities.
Applicability review and remediation remain follow-up work. Do not fabricate
not-affected conclusions or native coverage evidence to represent acceptance.

Roger remains the owner and approver. The existing expiration of
`2026-12-13T22:16:59Z` applies to this release exception. A changed candidate or
evidence of a new regression requires reassessment; this is not a permanent
policy waiver for later releases. Preserve the exact image/evidence bindings
and record accepted risk explicitly in deployment approval records. If the
current evaluator cannot represent this release exception, implement that
explicit representation before activation rather than silently bypassing it.

The full local suite already passed with 13,904 passed and 437 skipped;
focused and frontend gates also passed. Roger explicitly directs that the
full suite not be rerun for this documentation amendment. Retain those results
for the tested revision and use the normal deployment preflights.

Roger authorizes Redis credential rotation on wepp1, wepp2, and wepp3 as part
of deployment, including coordinated application of the replacement credential
to Redis and its consumers and the necessary service restarts. Verify
authenticated connectivity and queue/worker recovery during deployment without
printing credentials. Rotation is not a prerequisite to preparing this release.
The observed exposure was in this session's diagnostic transcript; no public
disclosure or unauthorized use was established.

## Deployment execution amendment

Roger explicitly authorized deployment on 2026-11-14 UTC. The first activation
attempt stopped before service changes because receipt comparison included
Compose extension metadata containing wctl's random temporary env-file path.
The bounded correction excludes only top-level `x-` metadata after anchor
expansion; effective runtime configuration remains fully compared. This requires
replacement source-bound builds and evidence. The same release acceptance and
expiry apply to those successors after fresh image-specific evaluation and
confirmation that this correction changes no application or dependency inputs.
Retain the original receipts and failed-attempt log; record replacement identities
in the deployment artifact. No full-suite rerun is requested for this tooling fix;
run focused retained-candidate and deployment regression checks.

## Decision

Roger explicitly accepts the residual risk for the affected installed PyPI GDAL
finding instead of compiling and maintaining a custom GDAL/Rasterio stack. The
accepted advisory aliases are `GHSA-r5m4-5vww-w9f5` and `CVE-2026-8212`. This
decision is limited to the exact GDAL installation reported in each final
candidate image and does not cover Debian GDAL packages, another version, a
different path, another advisory, or an unmatched native-coverage item.

The machine-readable private disposition must bind the final Grype finding key,
image ID, source revision, static lock hash, installed GDAL version and reported
path after fresh evidence collection. It may not be prepared from an earlier
candidate or by weakening the evaluator. The evaluator must reject any stale or
unmatched disposition.

## Exception fields

- **Disposition:** `accepted-risk`
- **Owner and approver:** Roger, WEPPcloud production operator
- **Created:** `2026-11-13T22:16:59Z`
- **Expires:** `2026-12-13T22:16:59Z`
- **Rationale:** compiling a private GDAL toolchain creates disproportionate
  maintenance and scientific compatibility risk; a supported packaged upgrade
  was explicitly deferred.
- **Compensating control:** `F6-RU-01` admits uploaded `.tif/.tiff` only as
  self-contained `GTiff` and `.img` only as self-contained `HFA`, rejects
  mismatched drivers and companions, performs full-band decode before
  publication, and reasserts locked file identity before asynchronous reuse.
- **Evidence:**
  `20261113_raster_upload_contract_decision.md`,
  `20261113_raster_upload_correctness_review.md`,
  `20261113_raster_upload_security_review.md`, and
  `20261113_gdal_qualification.md`.
- **Review trigger:** any new or changed advisory, GDAL/Rasterio version or
  package path, candidate image, source revision, evidence bundle, scanner or
  database, raster admission behavior, Compose configuration, or compensating
  control; renewal also requires fresh review.

## Original release boundary (superseded by the operator amendment)

This is the operator authorization needed to create an exact, private
machine-readable exception after final candidate scanning. It is not a blanket
waiver, does not approve an image before its evidence passes, and does not by
itself authorize service interruption or activation. Production readiness still
requires fresh host-bound retained candidates, imported evidence, exact
dispositions, protected approvals, and green deployment preflights.
