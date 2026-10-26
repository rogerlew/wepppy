# ADR-0108: Production browse worker timeout

Status: accepted for implementation; deployment pending. Date: 2026-10-26 UTC.

## Decision and provenance

Roger selected the recommended explicit 120-second Gunicorn worker timeout for
wepp1 browse in this Codex conversation on 2026-10-26. Participants: Roger and
Codex. Decision owner: Roger. Implementer: Codex. The prior effective value was
Gunicorn's implicit 30 seconds. The wepp1 command retains eight Uvicorn workers;
graceful shutdown remains 30 seconds and project-route proxy reads remain 10
minutes. Other environments and services are unchanged.

## Rationale and alternatives

Monday browse workers repeatedly timed out, and directory listings reached
65.2 seconds. The [NFS report](../infrastructure/ui-rcds-nfs-vs-dev-nfs.md)
records loaded create/rewrite operations near 57 seconds. A bounded increase
may reduce worker churn during temporary blocking I/O. It is not a request
execution deadline: async workers may serve longer requests while heartbeats
continue. The manifest scan already uses a thread. Neither NFS causality nor
resolution of Mariana's separate two-second HTTP 500 is established.

Retaining 30 seconds provides less tolerance for observed stalls. Disabling
timeouts would remove worker recovery. Raising to the proxy's ten minutes
would delay recycling unnecessarily. Additional worker, retry, auth and logging
changes are outside this literal configuration decision.

## Risk, observation and rollback

Genuinely stuck workers occupy capacity longer. Roger owns rollout and the
14-day post-deployment review. Compare worker timeouts per hour, manifest
success, directory latency and worker memory. Reassess if latency or capacity
worsens, or the 500 recurs. Revert this option to the prior default through the
canonical deployment process if harmful. Storage/event-loop remediation and
representative workload evidence are prerequisites to reducing the setting.

## Evidence and completion boundary

See [work package](../work-packages/20261026_browse_worker_timeout/package.md).
Closure means local configuration validation and commit, not production
recovery. Deployment follows package closure at the operator's direction.
