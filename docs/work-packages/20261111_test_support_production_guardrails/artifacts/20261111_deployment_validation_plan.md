# F1-F7 deployment-validation plan

**Status**: Source-informed draft; M4/F6/candidate hold; execution authority absent
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

## Source reconciliation (2026-11-12 UTC; no execution)

Re-read `scripts/deploy-production.sh`, `wctl/install.sh`, production Compose,
wepp1 overlay and worker Compose. Installed preset `wepp1` selects production
plus `docker-compose.prod.wepp1.yml`; `worker` selects
`docker-compose.prod.worker.yml` for wepp2. Host installation and running image
IDs still require separately authorized read-only verification before approval.

| Change | Source-defined consumers | Activation constraint |
| --- | --- | --- |
| F1 | weppcloud, query-engine, Caddy/browser credential integration | check valid/private/public workflows and static/proxy source |
| F2 | browse, dtale, Bootstrap admission in web/common-image consumers | all loader/admission consumers must share accepted revision |
| F3 | browse plus deployed static assets | preserve valid filename navigation |
| F4 | weppcloud, rq-engine, status, preflight, served frontend assets | Go service names in Compose are status/preflight |
| F5/F6 | WEPPCLOUD_IMAGE consumers in full and worker presets | Python workers must receive reviewed common image too |
| F7 | weppcloud; host wctl/browser tooling for non-production validation | production remains route-absent; do not mint support token there |

The common-image full preset contains weppcloud, browse, download, dtale,
profile-playback, elevationquery, metquery, wmesque, wmesque2, query-engine,
shape-converter, rq-engine, webpush, rq-worker, rq-worker-batch and scheduler.
The wepp1 overlay disables the dedicated fork/archive role. The worker preset
contains rq-worker, rq-worker-batch and separately imaged weppcloudr. Whether
weppcloudr imports changed Python code must be inspected on the exact candidate;
its distinct image is not covered merely by a common-image rebuild.

`--targeted-web` recreates only weppcloud/rq-engine and is insufficient for the
combined F1-F7 rollout. The full/worker paths derive their service maps, build,
verify topology, retain Redis/static-assets/health behavior and observe restart
counts. Use `scripts/deploy-production.sh --print-plan` under each correct
installed preset to review the concrete activation before authorization.
Do not substitute raw Compose recreation or a registry/Kubernetes workflow.
Preserve queue data and require `--no-flush-rq-db --skip-docker-prune` for this
reviewed retention window; no cancellation or Redis flush is implied.

Known-good image IDs/configuration, F6 evaluator acceptance, service drain
policy and exact rollback invocation are unresolved inputs, not placeholders
that may be ignored at execution. The batch-only rollback option does not
provide a general full-stack rollback. The future operator must verify a
containment-preserving retained-image/configuration recovery through the
canonical entry point before approving activation.

Hold conditions now include the F7 NFS cleanup failure: even the actual local
create/load/delete sequence cannot yet satisfy direct path absence. Rehearsal
must prove repair under production-equivalent mounts and identity. A 200
cleanup response is explicitly insufficient. No final approval is sought while
M4, F6 M4, exact combined tests, image IDs and rollback inputs are absent.

## Draft review corrections and final gate blockers

Operations reviewer `deployment_review` and security reviewer
`contract_security` identified the following required safeguards. These are
planning requirements; no deploy-script change or execution is authorized here.

- Require `--skip-docker-prune` for every rehearsal and production activation
  while rollback images/observation are retained. The script defaults to
  `docker system prune -a -f`, which can remove unused known-good images.
  Pruning requires a separate decision after the rollback/observation window.
- Inventory every host/worker sharing Redis DB9 before the global RQ fence.
  Record fence owner, heartbeat, paused/drained worker identities and final
  resume receipt across hosts. Script error recovery can resume the fence after
  partial activation; rehearsal must prove coordinated safe worker recovery,
  including mixed-image failure, before accepting local health as sufficient.
- Existing `compose_deploy_contract.validate_runtime_config` validates secret
  wiring, not F6 dependency evidence or F7 profile/flag invariants. Required
  pre-disruption image/advisory and profile/route checks must become concrete,
  reviewed blocking steps before activation. They are currently unimplemented
  final-gate prerequisites, not assumed protections of the current script.

Final runbook approval remains withheld until exact candidate/image/rollback
identities, these pre-disruption gates, the cross-host fence recovery receipt,
F6 M4 and F7 NFS/browser acceptance are supplied. No current draft verdict
permits service activation or production mutation.

Freeze the reviewed checkout and verify its full revision immediately before
activation; require supported `--skip-pull` so the script's default pull cannot
replace the evidence-bound source. Any pull or source change invalidates the
candidate/image/gate receipts and returns to review before activation.

Independent recheck: `deployment_review` (operations/security control) and
`contract_security` (security reviewer) confirmed these draft corrections on
2026-11-12 UTC. No open medium/high draft-quality findings; approved only as a
nonexecuted HOLD document. Final runbook/execution approval remains withheld.

The operations review also found the common dev support flag reached lazy Flask
consumers without the new profile. M1 now sets development on the common anchor;
production and worker common anchors pin production/false. All source-defined
Flask consumers pass configured-startup tests and rendered-value checks.
