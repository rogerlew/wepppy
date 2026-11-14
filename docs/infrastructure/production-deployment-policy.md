# Production deployment policy

## Authority

Roger directed this correction on 2026-11-14 UTC after one deployment consumed
approximately 25% of his weekly agent quota. Deployment had expanded into
repeated host builds, scans and evidence verification without proportional
benefit. This policy supersedes conflicting deployment guidance in ADR-0140,
work-package plans, evidence runbooks and operator skills. A deployment request
does not authorize an open-ended audit or redesign of the release process.

## Required deployment work

Use the existing Docker Compose deployment entry point for wepp.cloud:
installed `wctl` and `scripts/deploy-production.sh`. Preserve the established
host order, runtime identities, mounts, data and rollback path.

1. Identify the approved release and affected services. Reuse its completed
   tests, builds, scans and explicit residual-risk decisions.
2. Check host identity, relevant configuration/secret availability, disk capacity
   and active work. Drain affected jobs gracefully; do not flush queues or kill
   running jobs as routine deployment work.
3. Preserve the prior image/configuration, activate the selected artifacts, and
   verify running image identities, service health and worker registration.
4. Exercise a bounded smoke check for the workflow actually changed. Record
   the outcome and any remaining accepted risks.

## Reuse evidence; do not multiply it by host count

Scan a release artifact once and reuse that approval when deploying the same
immutable artifact to another host. Host receipts and configuration checks may
be host-specific; vulnerability scans are not inherently host-specific.

For existing host-local Compose builds with different image IDs, compare the
relevant dependency/build inputs and installed inventory. Image-ID differences
alone do not justify repeating the entire export/SBOM/advisory pipeline on every
host. Investigate material differences with the smallest relevant check. Do not
claim equivalence when it is unverified; retain that uncertainty in an explicitly
accepted release exception when the operator has authorized it. Do not introduce
a registry or change deployment topology just to obtain reuse.

Documentation, test-only, deployment-helper and receipt-format changes do not
invalidate an unchanged application image or require rebuilding and rescanning
it. Validate the changed tooling with focused checks and record its provenance
separately from application build identity. Generated staging files are not
source drift. Rechecking selected image/configuration identity before cutover
does not require repeatedly rereading multi-gigabyte scan bundles.

An approved rollout does not require another scan solely because time elapsed
between hosts. Respect the release approval's expiry and review triggers; new
relevant evidence or material artifact changes can require reassessment.

## Proportionate validation and risk decisions

Do not rerun the full test suite on production as a deployment prerequisite.
Reuse the release's passing development/CI results. Run focused checks for
subsequent fixes; documentation-only changes need documentation checks only.
Do not repeat full suites merely because a receipt or source commit changed.

An explicit operator residual-risk exception is a release decision. Existing or
unrelated findings and accepted native coverage gaps must not indefinitely block
patches for identified vulnerabilities. Keep those risks visible and owned;
do not label them fixed or not affected without evidence. Do not reopen the same
accepted decision or ask for the same authorization again without new evidence.

Broader audits, exhaustive dependency remediation, new review processes and
deployment-tool redesign are separate work. State their concrete benefit and
likely time/quota cost before expanding scope. Do not silently turn a bounded
deployment into that work. Keep monitoring concise and avoid redundant probes.

## Executable workflow

The retained-candidate tool supports protected release decisions and version-2
host bindings through `publish-release-approval`; see the
[release approval runbook](dependency-security-evidence.md#release-approval-normal-deployment-path).
These reuse release evidence and separately bind current deployment tooling.
They do not invoke scanners or repeatedly hash the raw evidence bundle.
Application/build-input changes, wrong images, dirty source, configuration drift,
unreviewed tooling and expired decisions still reject activation. The legacy
strict scan-bound evaluator is available when explicitly selected.
