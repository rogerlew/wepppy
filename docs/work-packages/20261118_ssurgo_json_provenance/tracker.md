# Tracker

- Contract: independent correctness/security reviews closed; ancestors 090e9f2b6 and 2f9aff0a7.
- Implementation: 39f24ce92; explicit JSON selection and persisted provenance across six consumers.
- Generated artifacts: 501 canonical files match; 499 base sidecars verified; 24,049 positive cache rows match from 34 HTTP fetches. Six non-valid outcomes preserved.
- Validation: 75 focused tests, two-module stubtest, stub hygiene and exception gate pass. Broad/extended suite environment blockers retained in artifacts/validation.md.
- Numerical environment: matched frozen reference passes; initial development-image diagnostic-comment mismatch retained, with no relaxed comparison rules.
- Service evidence: soil-data-access/artifacts/wepppy-parity/json-client; harness 60a699f, runtime 9dc2264.
- Publication: task/ssurgo-json-provenance and task/wepppy-json-parity; service evidence commit 9227204. No master integration or deployment.
- Integration candidate: task/ssurgo-json-merge, copied soil-only commits onto remote master; no inherited unrelated security changes. Exact soil sources match the validated branch; 75 focused tests pass again.

- Next direction (2026-11-18): mirror-first deployment default with observable SDA fallback; geographic/live parity deferred until SDA recovery.
- Forest contract: 43c78bf95 and ADR-0145; implementation and independent correctness/security reviews complete.
- Forest validation: 151 focused tests plus 24 review-closure tests and four cache-clear/persistence tests passed; two-module stubtest, stub hygiene, exception gate passed. Broad suite blocked by missing SECRET_KEY during collection.
- Official import: forest-id-20261001-vi-20161013-v1; 31,841 components, 132,604 horizons; 100 SSURGO and all eight selected STATSGO2 map units pass exact raw projection comparison.
- Queued acceptance: two unseen keys; primary cold/warm, direct-file reference, warm SDA-cache fallback and dual failure. Each successful case has 76 prepared soils; exact base/prepared parity and independent sidecar/artifact readback pass.
- Deployment: soil-api and soil-db healthy on forest; shared web/RQ consumers now use the mirror-first default. Four normal-queue canary jobs pass, including 152 exact-reference prepared inputs. forest1/production remain later scope.
- Evidence and limitations: [forest-validation.md](artifacts/forest-validation.md); service artifacts/forest. No national coverage or live SDA success claim.

- Approved activation: PR #675 merged at 0ae17ad8a393a4fbe250241b2253b77cc475d06b; candidate/merge governance pass. All five shared forest consumers now select mirror-first and reach the pinned release. Unrelated local history/work preserved; source/configuration rollback copies retained.
- Activation evidence: artifacts/forest-activation; real normal-queue build and soil-preparation canaries validate generated inputs and source sidecars.

- National recovery complete on forest: official nationwide SSURGO and STATSGO2 active; 22,073,263 imported rows; all five source-query families match. cavernous-oxygen rebuilt without SDA fallback, with 21 base provenance hashes and all 32 prepared hillslope inputs verified. National canaries match 152 reference inputs; authenticated routes return 200. Evidence: artifacts/national-activation.json. Full live SDA parity remains deferred.

- Current rollout scope (2026-11-18): forest1 deferred by operator; prioritize a full wepp.cloud release (wepp1 → wepp2 → wepp3), including other committed changes, application database migrations, and nationwide SSURGO plus STATSGO2. Production discovery is read-only so far; release assembly and migration rehearsal are pending. CILogon provider activation remains separately held.

- Production preparation: combined remote and committed local master in task/soil-production-rollout (merge 693ab6f83). Restored application database rehearsal upgrades f6b8d27a901c → a7c1106e42b9 with all pre-existing table-column hashes unchanged; 5,482 users. Live schema unchanged. Production Compose parses with private soil database and loopback-default API port 18080; runtime activation remains pending. See artifacts/production-migration-rehearsal.json and ../../infrastructure/soil-data-production.md.

- PR #678 merged at 9a50ccbf7d7ef279c1b13c41d3b72eeff77e7a39 after exact owner approval; merge tree matches approved d7af0b40e. Wepp1 build completed and images retained. National import checksum verified on wepp1. No live migration or service activation yet. Operator requests canonical-script first-install support and image-based deployment; follow-up implements explicit new-service declarations and checksum-pinned source-receipt image reuse without rebuilding. New focused lifecycle tests: eight passed.

- Deployment tooling follow-up: 118 retained-image/execution/plan tests pass; shell and docs checks pass. Actual wepp1 image reuse check matches the source receipt. Existing NAS used for private checksum-verified image distribution; host-local approvals remain required. Dedicated implementing-agent review: artifacts/production-script-review.md. Live migration and activation remain pending.

- PR #679 integrated at 0f2ec047d9f323877e84e489d3f5006bf0b559d5 with identical approved tree. Images loaded across hosts. Live account migration passed (5,482 legacy users). First full attempt omitted the raw Compose soil profile and recovered; retry explicitly exports COMPOSE_PROFILES=soil-data. National loading and host activation checks remain in progress.

- Production complete (2026-11-18 UTC): canonical wepp1 → wepp2 → wepp3 activation succeeded using identical transferred images. Account migration passed; national import has 22,073,263 rows. Eight consumers reach the pinned shared API. SSURGO/STATSGO2 queued builds and preparation passed four jobs, two verified base sidecars and 152 exact reference files. Authenticated homepage/profile return 200. Retained evidence: artifacts/production-activation.json. Runbook includes explicit soil profile, image-tag alignment, and narrowly scoped local UFW rule. Forest1/CILogon/public API hosting/live SDA parity remain deferred.
