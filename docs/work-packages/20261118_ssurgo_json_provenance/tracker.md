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
