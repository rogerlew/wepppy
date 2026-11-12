# F1-F7 deployment-validation plan

**Status**: Scaffold only; candidate and execution authority absent  
**Date**: 2026-11-12 UTC  
**Execution authorization**: none

This document will become the reviewed runbook for validating the combined
F1-F7 candidate. It does not authorize pulling, building, restarting, deploying,
mutating production data, or probing a live system beyond separately approved
read-only checks.

## Required Inputs Before Final Review

- Exact Git revision and clean candidate source receipt.
- Exact wepp1 common/test image IDs and F6 SBOM/scan/disposition identities.
- F1-F7 readiness matrix with no unresolved medium/high review finding.
- Current installed wctl presets and rendered Compose/host overrides for wepp1
  and any affected wepp2 worker services.
- Current `scripts/deploy-production.sh` revision and its supported targeted/full
  deployment modes.
- Known-good image/container mapping and rollback entry point.
- Named operator, validation owner, evidence recorder, and rollback owner.
- Explicit authority for every planned production mutation.

## Stage 0: Scope and Topology Confirmation

Before any deployment, map each finding to the exact services/images it changes.
Expected starting hypotheses, which must be verified rather than assumed:

| Finding | Likely production surface | Topology question to resolve |
| --- | --- | --- |
| F1 | query-engine, WEPPcloud/Caddy token bridge | Does activation require only web/query services? |
| F2 | Bootstrap, browse, D-Tale, shared image | Which containers must be recreated for all loaders/admission paths? |
| F3 | browse and Caddy-served browse assets | Is static output baked, bind-mounted, or service-only? |
| F4 | WEPPcloud/rq-engine, status2, preflight2, frontend assets | Which exact five-service forest mapping applies on wepp1? |
| F5 | Python web/microservices/RQ workers | Which wepp2 worker processes consume the sanitizer changes? |
| F6 | common/test image and activation gate | Which wepp1/wepp2 services share the final image? |
| F7 | WEPPcloud config/routes and smoke tooling | Production route must remain absent; no support token is needed in production |

Record active jobs, queues, container identities, service health, mounts,
identities/groups, Redis/PostgreSQL health, and disk headroom. Do not cancel
jobs. Decide whether a drain is required using existing operator procedures.

## Stage 1: Pre-Activation Gates

Run the exact F6 evidence/policy gate before service disruption. Render the
production Compose configuration and assert:

- `WEPPCLOUD_DEPLOYMENT_PROFILE=production` for WEPPcloud;
- `TEST_SUPPORT_ENABLED=false` as an effective literal;
- no test-support signing/token material beyond existing WEPP_AUTH requirements;
- exact F4 origins/secrets and F1 query configuration;
- no password-bearing Redis URLs/argv regress from the F5 prerequisite;
- affected image IDs match the reviewed candidate; and
- the Flask route inventory generated from the candidate contains no
  `/tests/api/*` entry.

Run safe offline/isolated focused acceptance for F1-F7 against the exact images.
No production project is used at this stage.

## Stage 2: Production-Equivalent Rehearsal

Use the approved forest/production-equivalent environment and the same Compose
family, identities, mounts, secrets-as-files, proxy routing, and service graph.
Activate the exact candidate through the environment's canonical procedure.

Re-run the F1-F7 checks listed below against disposable authorized fixtures.
Retain image/container identities, rendered-config hashes, response classes,
browser assertions, artifact hashes, and cleanup receipts. Do not retain
credentials, raw JWTs, private payloads, real secret canaries, or unredacted
tracebacks.

The rehearsal must pass before requesting production execution authority.

## Stage 3: Planned Production Activation

The future operator must use the installed wctl preset and
`scripts/deploy-production.sh`. The exact command and targeted/full service set
remain TBD until Stage 0 establishes the actual impact graph. No raw Docker
Compose substitute, registry workflow, or Kubernetes procedure is permitted for
wepp.cloud.

Before activation, confirm rollback mapping and that the deploy preflight fails
before disruption on missing/stale F6 evidence or invalid F7 production config.
Record start/end timestamps, source revision, image IDs, affected containers,
health transitions, and untouched services.

## Stage 4: Finding-Specific Post-Activation Checks

Every production mutation below requires explicit operator approval. Prefer a
pre-authorized disposable run and inert fixtures; never use a retained user run.

### F1: Query access boundary

- Owner/Admin/public positive reads follow the ratified matrix.
- Anonymous and unrelated clients cannot query/activate a private disposable
  run and cause no catalog/dataset/log side effect.
- Absolute, traversal, encoded-separator, symlink, and unsupported identifiers
  reject through an isolated hostile corpus, not host filesystem paths.
- Direct browser query flow remains functional with token-free URLs/logs.

### F2: Pickle restriction

- Allowed Bootstrap inputs still pass in a disposable repository.
- `.pkl`, `.pickle`, and mixed-case variants reject before deserialization.
- Existing authorized pickle artifacts remain listable/downloadable but expose
  no preview/D-Tale capability.
- Verify no loader call, not merely HTTP status.

### F3: Browse output safety

- An authorized disposable directory containing the approved inert filename
  corpus renders labels as text and encodes each URL segment exactly once.
- Browse/download/schema/D-Tale actions still navigate valid Unicode and ASCII
  names.
- Browser execution counters remain zero; cleanup is verified.

### F4: Status/preflight WebSockets

- The production frontend sends short-lived run-bound credentials to both
  services without token-bearing URLs or persisted headers.
- Authorized messages arrive; missing/cross-run/wrong-origin connections reject
  before run-channel Redis access.
- Selected protocol, logs, browser storage, reports, and retained evidence are
  token-free.

### F5: Traceback sanitization

- Use synthetic non-production canaries in an approved disposable validation
  path; never inject real production secrets into a failure.
- Verify frames, absolute paths, error correlation, and readable auth errors
  remain useful.
- Verify canaries are absent from API, container log, run file, RQ Redis, and
  status sinks, including sanitizer-failure fallback.
- Confirm normal paths perform no sanitizer secret snapshot work.

### F6: Dependency evidence gate

- Read back exact running image/package identities and compare with the accepted
  SBOM/scan bundle.
- Confirm the activation receipt names the current scanner DB/policy evidence.
- Exercise auth/session/OAuth, native imports, Redis, PostgreSQL, browse/D-Tale,
  RQ worker registration, and representative scientific execution boundaries
  required by the F6 package.
- Rejection of missing/stale evidence must already be proven before activation;
  do not sabotage a running deployment to retest it.

### F7: Test-support production guard

- Inspect the running candidate's effective profile/flag and Flask URL map.
- `GET /weppcloud/tests/api/ping` returns the normal not-found behavior through
  Caddy, but the URL-map evidence is authoritative.
- Do not attempt create/delete in production because the routes must not exist.
- Confirm no support token was minted, mounted, or retained for production.

## Stage 5: Cross-Host and Worker Checks

If Stage 0 confirms F5/F6 code or images run on wepp2, verify exact wepp2 image,
worker registration, queue consumption, Redis credential transport, sanitized
failure persistence, and rollback identity. A healthy wepp1 web stack does not
prove wepp2 worker compatibility. Do not deploy to wepp2 merely because the
common image changed; use the canonical worker procedure and explicit authority.

## Rollback Triggers

Rollback/hold triggers include:

- production test-support route present or invalid profile accepted;
- private query authorization bypass or valid query regression;
- any pickle loader/admission bypass;
- executable browse filename content or broken valid navigation;
- status/preflight credential omission, cross-run access, or reconnect failure;
- secret canary in any retained sink or unusable error observability;
- running image/evidence mismatch, dependency gate bypass, native import or
  auth/session regression;
- queue/worker loss, mount/permission mismatch, or cleanup failure affecting
  existing workflows.

Rollback must restore the named known-good image/config through the canonical
entry point. Rollback does not close the finding; retain evidence and reopen the
owning package/incident record.

## Evidence and Cleanup

- Retain exact revisions, image/container IDs, timestamps, health summaries,
  sanitized response assertions, artifact hashes, and route names.
- Never retain raw tokens, credentials, private payloads, real secret values,
  complete environment dumps, or production user run identifiers.
- Clean every disposable run, repository, Redis marker, browser session, and
  synthetic artifact. Verify cleanup rather than recording only a success code.
- Record any unverified host/service as unresolved; do not infer parity.

## Review and Authorization Gates

- [ ] Exact combined candidate and impact inventory filled in.
- [ ] F1-F7 readiness matrix passes.
- [ ] Forest/production-equivalent rehearsal plan reviewed.
- [ ] Operations reviewer approves service order, drain, health, and rollback.
- [ ] Security reviewer approves live checks and evidence handling.
- [ ] Package owner approves accepted residual risks.
- [ ] Production execution authority is recorded separately with timestamp and
      exact targets.

