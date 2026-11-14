# Security-fix production rollout

## Authority and validation

Roger authorized deployment to wepp1, wepp2 and wepp3 and coordinated Redis
credential rotation under the amended
[release exception](20261113_gdal_residual_risk_exception.md). Its expiration is
2026-12-13T22:16:59Z. Remaining dependency findings and unidentified native-file
coverage are accepted risks, not verified clean or not affected.

Application revision `f6a5b29dc6235c378577651a052b708ed4b0e017` passed 13,904
Python tests (437 skipped), 197 focused checks, frontend lint, 1,082 Jest tests
and three Node tests. The full suite was not rerun during deployment.

## Receipt comparison correction

The first wepp1 resume stopped before service changes. The only configuration
difference was `x-wepppy-service.env_file`, an unused extension containing
wctl's random temporary env-file pathname. Commit `c1f603ec2` excludes top-level
`x-` metadata after Compose expands anchors into actual services. It changes no
application code, dependency specifications, Dockerfiles or runtime settings.

Security review of this bounded correction: service environments, image IDs,
mounts, secret references, networks and volumes remain hashed; source cleanliness,
host/daemon identity, evidence freshness, protected approvals and immutable-image
activation checks remain enforced. The regression changes the temporary path
and confirms acceptance, then changes an effective service environment and
confirms rejection. All 76 focused retained-candidate/deployment tests passed in
disposable Compose; four changed documents passed lint. This is the executing
agent's review, not a new independent review.

Original f6 receipts, evidence, accepted-risk dispositions and approvals remain
private audit history. Replacement builds run through the canonical build mode;
all three replacement approvals were collected before activation. This repeated
work prompted the proportional policy correction below; it is not the new default.

## Execution state

A second pre-cutover refusal exposed unignored generated controllers staging
files. The bundle itself was already ignored, but its `.deploy.*` and
`.rollback.*` siblings were not. Scoped entries in wepp1's `.git/info/exclude`
allow these temporary generated files while retaining source cleanliness checks.
Direct staging-file/readback checks passed; the refusal log is retained as
`wepp1-c1-deploy-staging-refusal.log`. Equivalent `.gitignore` entries are part
of the follow-up documentation change; no application/image rebuild is needed.

Replacement builds completed on all three hosts at source
`c1f603ec25f4d74131f561640d80f5e479c11929`. Every candidate passed a real-driver
raster smoke check as `1002:130` on `/wc1/runs`: valid `.tif`, `.tiff` and `.img`
files passed and both content-to-extension mismatches failed. All three hosts'
Python/Debian package-version counts and normalized scanner finding groups match
their f6 predecessors. The legacy evaluator accepted 3,495 finding keys on
wepp1/wepp2, 3,494 on wepp3, and 1,201 explicit native coverage-gap dispositions
on each host.

| Host | Common image | State |
| --- | --- | --- |
| wepp1 | `sha256:59b83546fe83ba356cc143e50c7501b3a87ddf7b0e5ccb4d6cfecfb5bd642c18` | Activated; 24 services match receipt, six health checks pass |
| wepp2 | `sha256:4aa810dcaaafd57a323c177d7c2550429f61e54245d7e1f935c94ae47ed0c54b` | Activated; three services match receipt, health check passes |
| wepp3 | `sha256:f44868d73ce3a83333b471beced51766e9dec56eb152c1ecbec40b391c0c626b` | Activated; service matches receipt, worker registered as 1002:130 |

wepp1 activation ledger:
`activations/30c364be3bfd9994998095d913246c307eca6e767c9374b8389b82446c5288ba/20261114T035628Z-eed3892dc5e30d2b-efmpxf/activation.json`.
Its public web/RQ-engine checks pass and queue dequeue resumed. Redis rotation
is completed as recorded below. Initial live preflights showed 21 idle workers and zero
queued/started jobs in default, batch and fork-archive. Installed RQ rejects
`rq-info --detailed`; the readback used the direct Redis registries.

wepp2 activation ledger:
`activations/30c364be3bfd9994998095d913246c307eca6e767c9374b8389b82446c5288ba/20261114T040103Z-d007d916e92bb375-qrwcm0/activation.json`.
After both activations, all 21 workers were registered, all three queues had zero
queued/started work, and global dequeue was resumed.

To make room on wepp2, the two old f6 transport archives were losslessly
compressed. Decompressed SHA-256 values match their original retained receipt;
the raw reports, databases, manifests, approvals and candidate images remain.

Raw evidence, deployment logs and credential backups remain under the private
`/workdir/weppcloud-deployments/.local/dependency-security/` store on each host.
Do not publish credentials or credential hashes.

## Deployment governance correction

The governing [production deployment policy](../../../infrastructure/production-deployment-policy.md)
replaces repetitive per-host scans and tooling-only image rebuilds. Protected
release decisions explicitly list approved images and accepted risks; version-2
host bindings independently record reviewed tooling provenance. Gates validate
these small records without invoking scanners or rereading raw scan bundles.
Application/build-input changes, wrong images, configuration drift, dirty source,
unreviewed tooling, tampered decisions and expired approvals still reject reuse.

Validation: 83 focused retained-candidate/deployment tests passed; after the final
private-directory check, all 26 retained-candidate tests passed again. This is
focused development validation, not a production full-suite rerun. The executing
agent reviewed the change's approval, source-equivalence and drift boundaries;
no additional independent review was requested or claimed.

## Completed rollout and rotation

All three canonical deployments exited zero. wepp3 activation ledger:
`activations/30c364be3bfd9994998095d913246c307eca6e767c9374b8389b82446c5288ba/20261114T043908Z-087d6048e50c5c8b-y0scps/activation.json`.
Its old RQ worker/scheduler exited gracefully; a later kill request found the
old container already stopped and did not signal the replacement. Roger cancelled
his batch `compile_dot_logs_rq` job; rotation began only after active work cleared.

Redis rotation completed on 2026-11-14 UTC. A temporary dual-password ACL allowed
clients to restart sequentially on wepp1, wepp2 and wepp3. Secret files retained
their inodes, ownership and permissions; wepp3 required sudo for its existing
file ownership. The old credential was revoked, ACL saved, and Redis restarted.
Post-restart authentication verified that only the new credential works and the
old one is rejected. Redis is healthy; private backups remain available.

The owned RQ suspension was released. Authenticated `operator.add(1, 2)` probes
returned 3 on all queues:

- default: `deploy-probe-41ffa058a61848c09edf94d93bfc8edf`
- batch: `deploy-probe-e39917a8bbfb4a04af3cab08810bc827`
- fork-archive: `deploy-probe-97beb9c11c3042779f3119f11a94dbf7`

Final image/state readback passed for 24/3/1 selected services on wepp1/2/3;
all eight configured health checks passed. Public `/weppcloud/health` and
`/rq-engine/health` passed. Sanitized argv checks covered 25/11/4 containers
respectively and found neither old nor new Redis credential in process arguments.
RQ registry entries briefly included prior worker registrations after restart;
queue execution, rather than that raw count, establishes worker recovery.

Governance tooling `04165dfe7984956928369da12e47f1c74cd33833` is installed on all
three hosts. Their application images remain the c1 images above. Protected
release decision `a069d6fdf34d91430cbb97ebdb2036f7e14c60e19964e8246a38419bb3945e54`
authorizes those explicit images under the original exception deadline. Actual
read-only gates passed in 3.25/1.78/2.16 seconds on wepp1/2/3, without image rebuilds,
scans or full-bundle hashing. The first manual gate invocation omitted Compose
stdin and correctly rejected; supplying the canonical rendered configuration
passed. No application full suite was rerun.

Deployment is complete. Remaining dependency/native remediation remains owned
follow-up under the exception ending 2026-12-13T22:16:59Z, not unfinished rollout.
