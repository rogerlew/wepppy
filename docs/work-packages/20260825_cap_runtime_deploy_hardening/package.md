# Production Compose Deployment and CAP Runtime Hardening

**Status**: Open (2026-08-25)
**Timezone**: UTC

## Overview

On 2026-08-25, a full `wepp.cloud` Docker Compose deployment built a manually
curated subset of images, recreated the entire default stack, and reported
success after checking only WEPPcloud health. CAP restart-looped because its
non-root runtime migration was missing, and a new RQ worker failed DEVAL renders
because the recreated WEPPcloudR container used a stale April image without the
new render entrypoint.

This package fixes the shared deployment contract, makes the CAP repair
durable, prevents stale or incompatible images from being activated, and
requires integrated testing of the exact production command on forest1. CAP
activation retains a measured, bounded login-only maintenance gap; it does not
require logout, cookie clearing, site-data clearing, session rotation, or
interruption of already authenticated use.

## Objectives

- Define and enforce CAP's UID/GID, secret-read, and data-volume-write contract.
- Migrate fresh and supported legacy CAP state idempotently without exposing or
  replacing the secret or discarding the token ledger.
- Replace the full mode's hand-maintained partial build set with an explicit
  contract that builds every locally buildable service it recreates.
- Make `scripts/deploy-production.sh` distinguish and validate build targets,
  recreated services, expected-running services, migrations, and functional
  acceptance checks.
- Enforce worker/WEPPcloudR protocol compatibility and validate an RQ-driven
  DEVAL render before production rollout.
- Reproduce the original failures in automated tests and prove the repair at
  the unmocked Compose boundary.
- Execute the exact no-flag full deployment twice on forest1
  (`wc-prod.bearhive.duckdns.org`), with integrated auth, CAP, RQ, WEPPcloudR,
  rollback, stale-image, and idempotence evidence before production rollout.

## Scope

### Included

- `services/cap/Dockerfile`, CAP Compose configuration, CAP volume/secret
  initialization, and their operator documentation.
- A guarded `--targeted-cap` deployment mode that leaves the rest of wepp1 and
  all workers running.
- Full-deploy and targeted-deploy service selection, preflight, readiness, and
  failure reporting in `scripts/deploy-production.sh`.
- `weppcloudR/Dockerfile`, worker/renderer execution protocol files, image
  compatibility checks, and DEVAL end-to-end deployment acceptance.
- Executable deployment-mode tests for full wepp1, targeted web, targeted CAP,
  wepp2 worker, and wepp3 fork/archive topologies.
- Tests for fresh, populated legacy root-owned, malformed/unreadable, and
  correctly migrated CAP runtime states.
- Forest1 exact-command integrated rehearsal, rollback rehearsal, wepp1/wepp2
  rollout, and telemetry evidence.

### Explicitly Out of Scope

- Changing CAPTCHA difficulty, challenge semantics, login UX, OAuth behavior,
  or Flask authentication/session contracts.
- Introducing Kubernetes or a container registry into `wepp.cloud`; production
  remains host-built Docker Compose through `scripts/deploy-production.sh`.
- Adding CAP to wepp2/wepp3; worker topologies remain CAP-free.
- Broad refactoring of deployment orchestration unrelated to services actually
  selected for a deployment.
- CAP high availability or a redundant proxy cutover; this repair permits a
  measured, bounded login-only gap while preserving all browser/session state.
- Kubernetes/registry deployment changes for `openwepp.org`.

## Stakeholders

- **Primary**: WEPPcloud users and production operators
- **Reviewers**: independent correctness, operations, and QA reviewers
- **Security Reviewer**: independent security reviewer
- **Informed**: WEPPcloud maintainers

## Success Criteria

- [ ] A fresh CAP deployment starts as UID/GID `10001:10001`, reads only its
  mounted secret, writes its persistent ledger, and passes `/cap/health`.
- [ ] A populated legacy root-owned CAP data volume is migrated without token
  ledger loss and passes a redeem/write exercise.
- [ ] An unreadable CAP secret or unwritable CAP volume stops deployment with an
  actionable error before deployment is reported successful.
- [ ] A full deployment checks CAP health and fails if CAP is restarting,
  stopped, or unhealthy; targeted web mode does not claim to validate CAP.
- [ ] Full mode cannot recreate any locally built service from an image that
  was omitted from the candidate build; executable tests and forest1 receipts
  prove build/recreate set equality.
- [ ] Worker and WEPPcloudR images pass a versioned protocol/entrypoint
  compatibility gate before activation.
- [ ] A real forest1 RQ-driven DEVAL render finishes and publishes a validated
  HTML artifact and receipt through the Compose backend.
- [ ] CAP cannot listen ready when its ledger is unreadable, unwritable,
  malformed, or an unexpected filesystem type; acceptance includes a complete
  challenge/redeem/siteverify canary.
- [ ] Atomic secret replacement reapplies least-privilege named-UID ACLs for
  every effective CAP-secret consumer without group/world read access.
- [ ] `--targeted-cap` prevalidates the candidate, recreates only CAP, and
  automatically restores a host-local known-good image after activation
  failure without pruning the rescue image.
- [ ] Forest1 runs the exact no-flag production script twice, proving forward
  deploy, failure detection/recovery, rollback, integrated user workflows, and
  idempotence; production preserves authenticated sessions and requires no
  browser data remediation.
- [ ] Correctness/UX, QA, operations, and security reviews have no unresolved
  critical or high findings; package closure also requires all medium findings
  closed under repository policy.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes; incident conversation, operator
  evidence, and this package decision log

## Dependencies

### Prerequisites

- Existing CAP implementation and tests in
  `docs/work-packages/20260701_auth_cap_captcha/`.
- Production Docker Compose deployment contract in `docker/AGENTS.md` and
  `scripts/deploy-production.sh`.

### Blocks

- Any future full production deployment that recreates CAP should wait for this
  package's durable migration and health gate.

## Related Packages

- **Related**: [Auth Cap.js CAPTCHA](../20260701_auth_cap_captcha/package.md)
- **Related**: [Session Cookie Namespace Migration](../20260823_session_cookie_namespace_migration/package.md)
- **Incident**: [Production Compose Partial-Build Deployment Failures](../../infrastructure/incident-2026-08-25-production-compose-partial-build.md)

## Timeline Estimate

- **Expected duration**: 3-5 days
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: changes touch production secret-file permissions,
  container identity, persistent authentication-adjacent state, and deployment
  wiring.
- **Security review artifact**:
  `docs/work-packages/20260825_cap_runtime_deploy_hardening/artifacts/2026-08-25_security_review.md`

## Hardening and Callus Softening

- **Failure signatures**: `EACCES: permission denied, open
  '/run/secrets/cap_secret'`; `EACCES: permission denied, open
  '/var/lib/cap/tokensList.json'`; `docker-cap-1` restart loop; public
  `/cap/health` HTTP 502; login CAPTCHA unusable across Safari and Chrome;
  `cannot open file '/srv/weppcloudr/render-compose-request.R': No such file or
  directory`; DEVAL Docker backend exit 2.
- **Valid-state baseline**: populated legacy secret file mode `0600`, owned by
  the deployment account; populated named volume owned by root; CAP image user
  `10001:10001`.
- **Scope boundary**: fix the full/targeted Compose build-recreate-validate
  contract, CAP runtime migration, and worker/WEPPcloudR compatibility without
  replacing Docker Compose or redesigning authentication.
- **Related prior hardening efforts**:
  `docs/work-packages/20260701_auth_cap_captcha/`,
  `docs/standards/hardening-lifecycle-standard.md`, and the targeted production
  deployment work recorded in
  `docs/work-packages/20260823_session_cookie_namespace_migration/`.
- **Health signals**: CAP restart count remains zero; `/cap/health` succeeds;
  login CAPTCHA loads and redeems; deploy exits nonzero for deliberately broken
  permissions; full-mode build/recreate parity holds; DEVAL Compose render
  succeeds; no recurrence of CAP EACCES or missing-renderer signatures.
- **Danger signals**: world/group-readable secrets, discarded token ledger,
  hidden permission repair, unconditional broad ownership changes, health
  checks for services not deployed, or successful deploy status with a
  restarting service.
- **Observation window**: 14 days after production rollout.
- **Temporary calluses introduced**: none planned. Any compatibility migration
  must be idempotent, narrowly scoped, documented, and assigned sunset criteria
  before implementation.
- **Callus softening hypothesis**: after all supported hosts persist the
  canonical ownership/ACL contract through the observation window, any
  one-time legacy migration path may be removed only after direct fresh and
  populated-state tests plus all review gates.

## References

- `services/cap/Dockerfile` - CAP non-root runtime identity.
- `docker/docker-compose.prod.yml` - CAP secret and named-volume mounts.
- `scripts/deploy-production.sh` - canonical `wepp.cloud` deploy entry point.
- `docker/AGENTS.md` - Docker Compose production boundary.
- `docs/standards/hardening-lifecycle-standard.md` - incident-hardening rules.
- `docs/infrastructure/incident-2026-08-25-production-compose-partial-build.md`
  - authoritative incident record and timeline.
- `artifacts/2026-08-25_review_disposition.md` - consolidated blocking review
  findings and ratified design.

## Deliverables

- Durable runtime permission/migration implementation and regression tests.
- Simplified full-deployment build/recreate parity and per-service acceptance.
- Worker/WEPPcloudR compatibility gate and DEVAL end-to-end canary.
- Forest1 exact-command integrated test evidence.
- Updated operator/runtime documentation and forest1/production evidence.
- Independent correctness, QA, operations, and security review artifacts.

## Follow-up Work

- Record 14-day telemetry and decide whether any one-time migration logic can be
  retired under the callus-softening protocol.
