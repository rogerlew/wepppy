# Tracker — WMesque Catalog Synchronization

## Quick Status

**Started**: 2026-10-14 20:16 UTC
**Updated**: 2026-10-14 20:57 UTC
**Phase**: M1–M4 implemented/reviewed; M5 artifact acceptance passed, image/broad gates running
**Next milestone**: Finish M5 gates, then separately authorized M6 rollout
**Security**: High; independent implementation review approved, findings closed
**Plan**: [Active ExecPlan](prompts/active/wmesque_catalog_sync_execplan.md)

## Task Board

- [x] Capture governance and static analysis; scaffold package and reviews.
- [x] M1: Resolve manifest, transfer/publication layout, endpoint/error contract, and writer placement.
- [x] M2: Implement compatible server metadata and publication fixtures on forest.
- [x] M3: Implement client priority/failover and provenance on forest.
- [x] M4: Implement manual sync/RQ wrapper with scheduling disabled.
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
| Master transfer export/access not yet activated | Live remote sync cannot be enabled | Verify task SSH identity, credentials, trust, source closure/capacity in M6/M7; NED remote VRTs require materialization |
| Kubernetes geodata is read-only for compute workers | Sync cannot run on ordinary workers as configured | Select smallest authorized writer path before rollout |
| Kubernetes scheduler dry-run and three-task assertion | Naive activation enables unrelated jobs or fails readiness | Define sync-only activation in deployment repo |
| Replica lag and unpinned requests | Different runs may use different revisions | Document behavior and provenance; do not claim name-based reproducibility |
| New dataset source families | Unhandled driver sidecars could invalidate a published copy | Validate representative dependency closure before publication; GeoTIFF/VRT fixture gate passed |

## Verification Checklist

- [ ] Focused tests and broad `wctl run-pytest tests --maxfail=1` gate.
- [x] Stub checks if interfaces change; changed-code exception checks.
- [x] RQ dependency catalog, graph check, and actual job tree.
- [x] Real raster/source checks, downstream prepared inputs, and fresh representative output.
- [x] Default, override, outage, interrupted sync, overlap, extension, and adoption tests.
- [x] Operator documentation and fallback/timeout ADR.
- [x] [Correctness review](artifacts/20261014_correctness_review.md) complete.
- [x] [Security review](artifacts/20261014_security_review.md) complete.
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

### 2026-10-14 UTC — Execution

Operator authorized M1–M5 and forest restarts. Contract checkpoint `193df8b8c`
passed two independent reviews. First focused runs: 16 passed/1 legacy opt-in
skip and 41 passed. Broad suite and implementation reviews running. M5 uses
isolated fixture data/services with real forest batch workers; no production
activation. Scheduler snapshots source/destination arguments to avoid worker
environment drift. NED remote VRT dependencies require operator materialization
before managed publication; legacy retrieval is preserved.

### 2026-10-14 UTC — Forest artifact acceptance

Real scheduled batch jobs verified adoption, failed-copy recovery, and concurrent
reads across publication. Actual SIGKILL during a 268 MB copy preserved the old
catalog and retry succeeded. An isolated canonical project fork rebuilt DEM,
landuse, soils, and spatial PRISM climate, prepared model files, and executed a
100-year hillslope. Native report readers verified five loss rows and 36,525
daily-water rows. Focused service/scheduler tests: 72 passed, one legacy opt-in
skip; EDDE/helpers: 59 passed. API stubs, stub completeness, RQ graph/job inspection,
and changed exception gates pass. Both independent reviews approved fixes.
See [acceptance evidence](artifacts/20261014_forest_acceptance.md). Broad suite and
image validation remain in progress. Read-only forest1 checks found matching
identity/mount ownership and the same missing SSH client; Dockerfiles now add it
without changing identity, credentials, or mounts.
