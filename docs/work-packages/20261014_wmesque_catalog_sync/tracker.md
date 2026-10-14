# Tracker — WMesque Catalog Synchronization

## Quick Status

**Started**: 2026-10-14 20:16 UTC
**Updated**: 2026-10-14 20:24 UTC
**Phase**: Scaffold complete; implementation not started
**Next milestone**: M1 — contracts and bounded fixture design
**Security**: High; dedicated review required, pending
**Plan**: [Active ExecPlan](prompts/active/wmesque_catalog_sync_execplan.md)

## Task Board

- [x] Capture governance and static analysis; scaffold package and reviews.
- [ ] M1: Resolve manifest, transfer/publication layout, endpoint/error contract, and writer placement.
- [ ] M2: Implement compatible server metadata and publication fixtures on forest.
- [ ] M3: Implement client priority/failover and provenance on forest.
- [ ] M4: Implement manual sync/RQ wrapper with scheduling disabled.
- [ ] M5: Validate forest scheduled integration, downstream artifacts, and Compose parity.
- [ ] M6: Complete independent reviews and publish compatible support on wepp.cloud when authorized.
- [ ] M7: Canary receiving deployment sync and local-first routing when authorized.
- [ ] M8: Enable recurrence, validate recovery, and close with evidence.

## Decisions

- **2026-10-14 20:24 UTC** — Operator specified a shared tailnet for all deployments for now. Governance “Scheduled Synchronization” and M1 now use private sync connectivity; rsync over SSH is the preferred proposal. Actual task connectivity and permissions remain unverified. Public bulk-transfer and cross-tailnet support are excluded to keep implementation simple.
- **2026-10-14 20:16 UTC** — Operator selected wepp.cloud as master, extension-only receiving catalogs, and seamless adoption through ordinary sync. Authority: governance, “Catalog Authority and Extensions.” Avoid runtime conflict machinery.
- **2026-10-14 20:16 UTC** — Operator requires unconfigured deployments to use wepp.cloud. Authority: governance, “Deployment Endpoint Defaults.” Local service installation alone must not change routing.
- **2026-10-14 20:16 UTC** — Scaffold only this session. Interface details in the assessment remain proposals until M1 resolves them; no invented production access or writer permissions.

## Risks and Open Decisions

| Issue | Impact | Next action |
| --- | --- | --- |
| Transfer export/access and source dependency closure unverified | Live sync cannot be activated | Inventory representative VRTs and authorized source transport in M1 |
| Kubernetes geodata is read-only for compute workers | Sync cannot run on ordinary workers as configured | Select smallest authorized writer path before rollout |
| Kubernetes scheduler dry-run and three-task assertion | Naive activation enables unrelated jobs or fails readiness | Define sync-only activation in deployment repo |
| Replica lag and unpinned requests | Different runs may use different revisions | Document behavior and provenance; do not claim name-based reproducibility |
| Publication layout and in-flight readers | Partial/mixed data if cutover is unsafe | Prove stable revision reads on actual storage |

## Verification Checklist

- [ ] Focused tests and broad `wctl run-pytest tests --maxfail=1` gate.
- [ ] Stub checks if interfaces change; changed-code exception checks.
- [ ] RQ dependency catalog, graph check, and actual job tree.
- [ ] Real raster/source checks, downstream prepared inputs, and fresh representative output.
- [ ] Default, override, outage, interrupted sync, overlap, extension, and adoption tests.
- [ ] Operator documentation and fallback/timeout ADR.
- [ ] [Correctness review](artifacts/20261014_correctness_review.md) complete.
- [ ] [Security review](artifacts/20261014_security_review.md) complete.
- [ ] Authorized rollout and rollback evidence; no open medium/high findings.

## Progress Notes

### 2026-10-14 20:24 UTC — Shared tailnet assumption

Updated governance, assessment, package scope, and active plan. Runtime behavior,
client defaults, and deployment permissions are unchanged. Implementation remains
unstarted.

### 2026-10-14 20:16 UTC — Scaffold

Created brief, active plan, tracker, and pending review artifacts from the static
assessment. No tests of runtime behavior or live deployment actions were performed.
Next executor starts M1 and maintains both this tracker and the plan. Documentation
lint passed for all five package files, the root project tracker, and AGENTS.md.
The root onboarding size gate passed at 160 lines; whitespace checks passed.
Spelling preview suggested only “afterward” to “afterwards”; retained the existing
valid American spelling.
