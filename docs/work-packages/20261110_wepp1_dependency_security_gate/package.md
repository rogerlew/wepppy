# wepp1 common-image dependency security gate

**Status**: Open (2026-11-11 UTC); M0 complete with green full baseline and
reviewed checkpoint; M1 inventory/disposition work executing

**Timezone**: UTC

## Overview

Remediate security audit finding F6/SEC-06 by replacing manifest-only advisory
counts with an artifact-bound dependency inventory, risk disposition, compatible
upgrade sequence, and repeatable release gate for the common WEPPcloud image
built for wepp1. The audit observed 168 Python advisory records across 22 package
names, including duplicate aliases, but retained no machine-readable scan and did
not inspect the running or candidate production image. That count is a triage
signal, not evidence that 168 vulnerabilities are installed, reachable, or
exploitable.

The package starts from the exact image produced by `docker/Dockerfile` through
the canonical wepp1 Compose/deploy path. It binds the image ID or digest to a
software bill of materials (SBOM), operating-system and language scan reports,
scanner/database identities, and a disposition for every finding. Compatible
security upgrades are grouped by runtime boundary and validated in a clean
rebuilt candidate. Incompatible native, framework, or workflow migrations move
to explicit follow-up packages rather than being forced into a bulk upgrade.

The operator requires the complete canonical Python and primary frontend gates.
Before handoff, the final candidate must pass `wctl run-pytest tests
--maxfail=1`, `wctl run-npm lint`, and `wctl run-npm test`. A segmented or
focused run does not replace these gates.

## Threat Model

- **Assets**: user identities and OAuth flows, private run data, worker
  authority, mounted `/wc1` and `/geodata`, runtime secrets, and production
  availability.
- **Adversaries/failures**: exploitation of an applicable vulnerable component,
  a compromised package or build input, dependency-confusion or provenance
  drift, and an incompatible upgrade that silently weakens an application
  boundary.
- **Trust boundaries**: requirements and lockfiles cross package registries,
  Git repositories, base images, build runners, container layers, the local
  wepp1 image store, and finally running services.
- **High-value paths**: authentication/OAuth/crypto defects, hostile-input parser
  defects, HTTP/TLS client defects, and worker-side library defects with access
  to shared mounts or secrets.
- **Assumptions to prove**: the scanned image is the exact candidate tested and
  selected for deployment; scanner coverage includes its Python and Debian
  packages; frontend findings are tied to the exact lock; exceptions are owned
  and expire; distinct non-common service images are not misrepresented as
  covered.

## Objectives

- Build the common image with immutable or recorded build inputs and capture its
  exact local image ID and, where published, manifest digest.
- Generate a standard SBOM from that exact image and verify it against direct
  installed-package readback.
- Scan installed Python and Debian packages, and audit the exact primary
  frontend lock used by the static-builder stage.
- Reproduce or supersede the audit's preliminary advisory signal with retained,
  machine-readable evidence tied to scanner and advisory-database versions.
- Disposition every result by installed version, affected code path, deployment
  reachability, exploit preconditions, fixed version, and action.
- Prioritize compatible authentication/OAuth, cryptography/TLS, network-client,
  and hostile-input parser fixes without blind bulk upgrades.
- Add repeatable candidate-image and manifest gates to the appropriate CI source
  workflow, and design a fail-closed pre-activation check for the canonical
  wepp1 deployment path.
- Prove the final dependency set with focused boundary tests, a clean image
  rebuild, full pytest, npm lint, and full npm tests.

## Scope

### Included

- The common runtime built by `docker/Dockerfile` and selected as
  `${WEPPCLOUD_IMAGE:-wepppy:latest}` by the wepp1 production Compose stack.
- `/opt/venv` Python packages installed from `docker/requirements-uv.txt`,
  including direct, transitive, range-constrained, and Git-sourced entries.
- Debian packages, base-image provenance, downloaded Docker CLI and Quarto
  components, the DuckDB spatial extension, and vendored Git repositories in
  the common image, with explicit scanner-coverage limits.
- `wepppy/weppcloud/static-src/package-lock.json`, including production browser
  dependencies and build-time packages that can affect emitted static assets.
- `docker/Dockerfile.test`, `docker/docker-compose.test.yml`, and the generated
  workflow source under `.github/forest_workflows/` as needed to ensure the full
  suite runs against the reviewed candidate dependency image.
- A bounded gate in `scripts/deploy-production.sh` after the common image is
  built and before any service is stopped or recreated, subject to the M0
  operator policy checkpoint.
- Focused compatibility tests for packages actually upgraded, plus the complete
  Python and primary frontend gates.

### Explicitly Out of Scope

- Blindly upgrading every old package or treating scanner severity alone as
  exploitability proof.
- Changing application authentication, authorization, parser policy, scientific
  behavior, runtime identities, mounts, secrets, or network topology merely to
  accommodate an upgrade.
- Distinct CAP, Caddy, Redis, PostgreSQL, status/preflight Go, WEPPcloudR, and
  auxiliary image dependency remediation. They remain named inventory rows and
  require their own evidence/package unless they inherit the common image.
- Major native ABI migrations such as a Python GDAL version that is incompatible
  with the image's system `libgdal`; these become separate work packages.
- Scanning live production containers or installing tools on wepp1 during this
  scaffold. No production action is authorized.
- Claiming all advisories are remediated when a time-bounded accepted-risk item
  or excluded image remains.

## Complexity Budget

- **Existing mechanisms reused**: Docker image IDs/digests, the canonical
  Dockerfile and deploy script, `wctl`, the isolated test Compose stack,
  generated Forest workflows, npm lock/audit output, and direct package readback.
- **New mechanisms permitted**: one pinned, non-runtime SBOM/scanner toolchain;
  one machine-readable policy/exception format; one image gate shared by CI and
  pre-activation deployment checks.
- **Tool adoption constraint**: any new scanner must pass the precedent,
  capability-overlap, dependency-tax, and maintenance gates in
  `docs/standards/dependency-evaluation-standard.md` before integration.
- **Simplest plausible path**: inspect and gate the exact common image; do not
  build a new vulnerability service, datastore, or daemon.
- **Evidence required before escalation**: a retained failure showing the pinned
  scanner cannot inventory or assess a component that materially affects F6.
- **Explicitly prohibited expansion**: new runtime libraries solely for
  scanning, a hosted security platform, silent scanner fallback, or automatic
  dependency upgrades without review.

## Generated Artifact Validation Gate

- **Applicable**: yes. The production image, SBOM, scan reports, bundled static
  assets, and test image are generated artifacts.
- **Intent evidence**: source revision, manifest hashes, build arguments, base
  references, vendored Git references, and scanner policy revision.
- **Persisted-state evidence**: image ID/digest and immutable report filenames.
- **Generated-intermediate evidence**: SBOM and raw Python/OS/npm scan JSON,
  each hashed and bound to the image/lock identities.
- **Prepared/consumed-input evidence**: direct `/opt/venv` package inventory,
  `dpkg-query` output, static lock hash, and test-runtime base image identity.
- **Execution evidence**: scanner/policy exit status plus focused, full pytest,
  npm lint, and npm test receipts on the final candidate.
- **User-facing result evidence**: production-equivalent health and selected
  authentication/parser workflow smokes when rollout is separately authorized.
- **Direct unmocked boundary**: the actual locally built image, not a reconstructed
  requirements list.
- **Raw evidence storage**: gitignored `out/security-audit-20261110/f6/` or a
  protected CI artifact; tracked docs retain hashes, versions, summary, and
  dispositions without secrets.
- **Highest completion claim currently supported**: diagnosed and scaffolded.

## Stakeholders

- **Decision owner**: WEPPpy maintainer and wepp1 operator.
- **Primary implementers**: dependency, Docker/build, CI, and affected subsystem
  maintainers.
- **Reviewers**: correctness/UX, QA/code quality, security/supply chain, and
  wepp1 operations for the deploy gate.
- **Security reviewer**: required and independent of the implementation author.

## Success Criteria

- [ ] The candidate common image has an exact image ID/digest and recorded source
      revision, build arguments, base references, and vendored refs.
- [ ] SBOM coverage is reconciled against direct Python and Debian package
      inventories; omissions are explicit.
- [ ] Python, OS, and primary npm reports record scanner/database versions and
      bind to the exact image or lock hash.
- [ ] Every finding has one reviewed disposition: fixed, verified not present,
      not affected with evidence, time-bounded accepted risk, or separate
      blocked follow-up.
- [ ] No unresolved applicable Critical/High finding remains; applicable Medium
      findings are fixed or explicitly accepted with owner, rationale,
      compensating control, and expiry.
- [ ] Compatible upgrades preserve auth/session/OAuth, parsing, networking,
      geospatial/native, RQ, and report behavior relevant to changed packages.
- [ ] The final common and test images rebuild from clean inputs and expose the
      reviewed versions and artifact identities.
- [ ] Dependency changes trigger a repeatable CI artifact gate and full baseline
      suite against the reviewed dependency image.
- [ ] The pre-activation wepp1 gate fails closed on missing/stale scan evidence
      or a policy failure, without stopping the running known-good stack.
- [ ] `wctl run-pytest tests --maxfail=1` exits zero on the final candidate.
- [ ] `wctl run-npm lint` and `wctl run-npm test` both exit zero on the final
      candidate lock.
- [ ] Independent correctness, QA, security, and operations reviews pass.

## Parameterization ADR Gate

- **Parameterization change present**: workflow freshness, exception, and
  evidence-retention limits; no scientific parameterization change.
- **ADR required**: yes.
- **ADR links**: [ADR-0140](../../adrs/ADR-0140-dependency-security-gate-policy.md).
- **Decision provenance captured**: yes, in the scope/policy artifact.

## Dependencies

### Prerequisites

- Complete the scanner/tool evaluation without adding an application runtime
  dependency.
- Ratify advisory thresholds, exception schema, database freshness, artifact
  retention, and fail-closed deployment behavior before implementation.
- Capture clean pre-change full pytest and npm lint/test baselines.

### Blocks

- Closure or explicit disposition of security audit finding F6/SEC-06.

## Related Packages and Precedent

- [Dependabot PR triage and local stack rebuild](../20260715_dependabot_pr_triage_stack_rebuild/package.md)
  is the primary compatible-batch, no-cache rebuild, full pytest, and npm
  validation precedent.
- [Private canary image](../20260813_weppcloud_private_canary_image/package.md)
  provides immutable common-image publication and digest precedent for
  `openwepp.org`; it does not redefine wepp1 deployment.
- [RQ 2.12 upgrade](../20261027_rq_2_12_upgrade/package.md) demonstrates a
  subsystem-specific dependency upgrade and runtime acceptance.
- [Dependency evaluation standard](../../standards/dependency-evaluation-standard.md)
  governs adoption of the scanner toolchain.
- [Generated artifact validation standard](../../standards/generated-artifact-validation-standard.md)
  governs image/SBOM/report identity claims.

## Timeline Estimate

- **Expected duration**: 1-3 weeks, depending on the number of applicable
  upgrade batches and native compatibility blockers.
- **Complexity**: high because evidence spans build provenance, Python, Debian,
  npm, CI, and production activation boundaries.
- **Finding severity**: Medium with current exploitability unconfirmed.
- **Change security impact**: high because auth, parsers, build inputs, CI, and
  production deployment gating may change.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **CWE/OWASP mapping**: CWE-1104; OWASP Top 10 2021 A06 Vulnerable and Outdated
  Components.
- **Triage rationale**: dependency and build changes can alter internet-facing
  authentication, parsing, networking, worker execution, and supply-chain trust.
- **Security review artifact**:
  [artifacts/20261110_security_review.md](artifacts/20261110_security_review.md).

## Hardening and Observation Model

- **Failure signature**: a production-candidate image contains an undispositioned
  applicable advisory or cannot produce fresh digest-bound scan evidence.
- **Scope boundary**: correct and gate the common-image dependency failure class
  without redesigning unrelated services or application behavior.
- **Hypothesis**: if CI and deployment evaluate the exact candidate image and
  lock against a reviewed policy, new applicable vulnerabilities and provenance
  drift will block before activation.
- **Health signals**: fresh successful scan per candidate digest; zero
  undispositioned Critical/High findings; full test gates green; exception count
  and age non-increasing.
- **Danger signals**: manifest-only claims, scanner/database identity missing,
  stale report reused for a new image, `|| true`/silent fallback, permanent
  exceptions, broad incompatible batches, or tests running on a different base.
- **Observation model**: stateless recurrence-triggered. A newly disclosed
  applicable advisory, expired exception, report/image mismatch, or gate bypass
  opens a new package and blocks promotion under the canonical policy.
- **Temporary calluses**: any exception is temporary and must name an owner,
  expiry, compensating control, and removal condition.

## Validation Scope Decision

The operator explicitly requires broad validation. Required commands on the
final candidate are:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

Run focused tests first for each upgraded boundary, but they do not replace the
three commands above. The exact full commands must exit zero after the final
manifest/lock change and clean image rebuild. A segmented run, partial rerun, or
baseline-only reproduction does not close this package without a new explicit
operator waiver.

## References

- `docker/Dockerfile`
- `docker/Dockerfile.test`
- `docker/requirements-uv.txt`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.wepp1.yml`
- `scripts/deploy-production.sh`
- `wepppy/weppcloud/static-src/package.json`
- `wepppy/weppcloud/static-src/package-lock.json`
- `.github/forest_workflows/stubtest.yml`
- `.github/forest_workflows/npm-tests.yml`
- `.github/workflows/publish-weppcloud-image.yml`
- [Active ExecPlan](prompts/active/implementation_execplan.md)
- [Scope and policy decision](artifacts/20261110_scope_and_policy_decision.md)
- [Surface inventory](artifacts/20261110_surface_inventory.md)
- [Scanner evaluation](artifacts/20261110_scanner_evaluation.md)
- [Correctness review](artifacts/20261110_correctness_review.md)
- [QA review](artifacts/20261110_qa_review.md)

## Deliverables

- Reviewed scanner evaluation and artifact-bound advisory policy.
- Exact-image SBOM, scan receipts, package inventories, and disposition matrix.
- Compatible dependency batches with direct boundary and full regression evidence.
- CI and pre-activation gates with fail-closed/error-path tests.
- Correctness, QA, security, and operations review artifacts.
- Separately authorized wepp1 rollout evidence, if requested.

## Follow-up Work

Open separate packages for incompatible native/framework migrations and for
distinct wepp1 images excluded from this Python common-image finding. Do not hide
those boundaries under an all-clear claim for the common image.
