# Tracker - wepp1 common-image dependency security gate

## Quick Status

Current direction (Roger, 2026-11-12): continue dependency remediation; defer
deployment-resume work. Stale NFS handles require manual recovery, without
automatic waiting. Next repair work targets Mistune and the qualified native
library findings; deferred resume work must not block these repairs.

Remediation status (2026-11-12): master includes cryptography, certifi, urllib3,
pyasn1, msgpack and nbconvert upgrades. Authlib/joserfc are updated and tested
in the isolated candidate. Other dependency/native repairs remain open. The
operator redirected focus to remediation; deployment-resume design is on hold.

**Timezone**: UTC  
**Last updated**: 2026-11-12 UTC
**Current phase**: M0 complete; M1 image dispositions and native coverage in progress  
**Finding**: F6 / SEC-06 (Medium, exploitability unconfirmed)  
**Change security impact**: high  
**Dedicated security review**: `artifacts/20261110_security_review.md`  
**Starting revision**: `2041fb8e2`

**Accepted M0 checkpoint**: `d4b175436`

The M3 local manual importer passes 31 focused tests, actual private artifact
readback and independent correctness/security review. Full pytest passes at
2026-11-11 08:52 UTC: 13,533 passed, 435 skipped. Fresh npm lint and all 1,069
npm tests pass. This is development-runtime component validation, not M4.
The evaluator and confined collector are implemented. Actual CI producer handoff,
deployment integration, native coverage and advisory dispositions remain open.
See `artifacts/20261112_parser_collector_acceptance.md` for the latest candidate
producer qualification and `artifacts/20261112_oauth_candidate_validation.md`
for the later clean OAuth candidate. Its 18 Authlib rows are removed, but the
actual gate rejects native coverage. M4 is not complete.

## Task Board

- [x] Isolated candidate `63ae6f940` implements Python/auth/Starlette and
  packaging-tool remediation; focused consumers and fresh/incremental host
  installers pass. Independent source reviews have no Medium/High findings.
- [ ] Finish clean image/full gates and remaining GDAL/native dispositions;
  deployment resume remains deferred.


- [x] (2026-11-12 UTC) Clean native dependency candidate `37e7dd311bbd`
  passes 110 focused tests and the actual PATH report with decoded plot and
  installed-library hash readback. F6 native repair artifact records evidence.
  Further Python/GDAL repairs, fresh scan and full gates remain open; resume
  remains deferred and stale NFS handles require immediate manual recovery.

- [x] (2026-11-12 UTC) Implement Mistune 3.4.0 and PyCurl 7.49.0 in the
  isolated candidate after before/after consumer checks (19 cases each).
  Mistune upstream checks pass 35 unittest and 65 pytest cases. Final common
  build, scan and full gates remain open; see
  `artifacts/20261112_mistune_pycurl_remediation.md`.


- [x] Exact clean OAuth image passes 50 callback tests in 9.71s after a quiet
  standard-stack retry; failed startup receipt is preserved. See
  `artifacts/20261112_oauth_candidate_validation.md`.

- [x] Corrected parser collection 6 passes producer/readback checks; actual
  evaluator blocks on unresolved native coverage with empty approvals.

- [x] Itemize all 2,105 native unknown paths/1,201 hashes with ownership
  proposals; supplemental component coverage and dispositions remain open.
  See `artifacts/20261112_native_coverage_review.md`.

- [x] Independently review isolated OAuth revision `afe6e7264`; 50 component
  tests pass, clean build passes in 658.72s. Installed version delta is exactly
  Authlib plus joserfc; native GDAL sentinels match. No forest activation.
- [ ] Implement and prove actual CI lifecycle from
  `artifacts/20261112_ci_producer_design.md`; keep deployment workflow selection
  separate and pending.

- [x] Complete real parser candidate collection and inventory reconciliation;
  retain blocked policy status and qualified-diagnostic correction.

- [x] Confirm F6 audit scope and the wepp1 common-image production boundary.
- [x] Discover prior dependency-upgrade and immutable-image precedent.
- [x] Scaffold package, active ExecPlan, policy/inventory artifacts, and review
      gates.
- [x] Record mandatory full pytest, npm lint, and full npm test gates.
- [x] M0: reproduce evidence; evaluate/select pinned scanner tooling; ratify
      thresholds, exceptions, retention, and deploy behavior.
- [ ] M1: build exact baseline image; generate/reconcile SBOM and scan reports;
      disposition every finding.
- [ ] M2: implement compatible upgrade batches with focused boundary tests.
- [ ] M3: add CI/test-image and pre-activation artifact gates with failure tests.
- [ ] M4: rebuild the final candidate; run focused gates, full pytest, npm lint,
      full npm tests, and independent reviews.
- [ ] M5: perform separately authorized wepp1 rollout and closeout.

## Decisions and Discoveries

- Real-bundle readback found an order-only Grype location mismatch. Correct
  full-object multiset comparison preserves every location field and duplicate
  count; finding approval keys and unresolved advisory status are unchanged.

- Decision (Roger, 2026-11-11): transfer evidence **manually** to the selected
  private store; production remains Docker Compose through canonical wctl/deploy
  entry points. Verify imported report hashes/identities before acceptance.
  Rationale: use the operator-selected bounded handoff without adding a transfer
  service or changing production topology. M3/M4 must validate this handoff.

- The audit retained only a summary: 168 advisory records across 22 Python
  package names, with duplicates. No raw report, scanner/database identity, or
  exact image identity is available, so the count must be reproduced rather
  than accepted as the package baseline.
- No repository-integrated SBOM/vulnerability scanner or local `syft`, `trivy`,
  `grype`, `osv-scanner`, or `pip-audit` executable was found at scaffold time.
  Docker is available. Tool selection therefore requires the dependency
  evaluation gate before integration.
- The common Dockerfile installs 259 requirement lines, including one Git source
  and five range-constrained lines, and also downloads/vends components that a
  Python-only audit can miss.
- The primary npm lock is used in the static-builder stage; Node modules are not
  copied wholesale into the runtime image, but build-time compromise or a
  vulnerable bundled browser dependency can still affect emitted assets.
- The existing generated full-baseline workflow does not trigger on
  `docker/requirements-uv.txt`, and `docker/Dockerfile.test` is pinned to an
  existing published common-image digest. The repair must prove tests run on the
  reviewed dependency candidate.
- The operator requires exact full commands to pass. Prior precedent that used a
  controlled aggregate workaround does not authorize one here.

## Validation and Review

The itemized M1 review packet preserves all 3,221 scan rows and 3,133
artifact-scoped alias groups. Version 3 proposes 327 header-only, three exact
patched Python Brotli and 109 absent MariaDB implementation dispositions;
2,782 rows remain unresolved. No
approval or activation clearance is inferred. See
`artifacts/20261110_advisory_dispositions.md` for hashes and coverage limits.

The 19 npm audit rows have independently supported not-affected proposals only
for the exact runtime/static build; CI admission remains pending. The first
crypto/TLS-only clean Compose build is running in a detached checkout. Authlib
adoption is held for the reviewed OAuth failure/CSRF contract checkpoint;
`artifacts/20261111_oauth_contract_decision.md` records the concrete proposal.

Preparatory unchanged-source common-image build succeeds, using canonical
production/wepp1 Compose overlays and immutable base/vendor arguments. Exact
image ID and command evidence are in `artifacts/20261111_baseline_image.md`.
Native import readback passes as UID 1002/GID 130; GDAL/Fiona use GDAL 3.10.3
while Rasterio bundles 3.8.4. Image inventory/scan and the full baseline rerun
have completed. The original database exceeds the 24-hour freshness limit, so
those reports remain triage evidence. A separately retained November 11 database
is fresh; the clean crypto/TLS scan has no matches for those upgraded packages.
The same-database baseline comparison removes 22 raw selected-package rows with
no package-level additions. Whole-image findings and coverage remain blocking.

The clean crypto/TLS candidate builds with exactly three installed-version
upgrades, unchanged native versions, 51 focused tests and seven TLS checks
passing. Details are in `artifacts/20261111_upgrade_research.md`. The isolated
test-image candidate-base argument passes a real local build, layer/runtime
identity readback, native/Python version parity and another 51 focused tests.
The npm source/generated workflow now runs lint before tests; generation parity
passes. Remote CI evidence collection and the deploy hook remain open.
Production remains Docker Compose through installed wctl/deploy-production,
as explicitly reaffirmed by Roger; no registry dependency is introduced.

The first full pytest run failed on an obsolete Runs help-link assertion after
13,429 passes. The test now follows the existing UI contract; all 11 module tests
pass. The exact full rerun passes: 13,502 passed, 435 skipped. npm lint and all
1,069 npm tests pass; the stub completeness check passes. Complete receipts and
hashes are retained privately in the M0 `baseline-final/` directory. The baseline
records its starting revision and unchanged dependency manifest hashes. Installed wctl selects the dev
image, so this run does not establish candidate-image parity.

Trivy 0.76.2 was rejected after a reproduced Python GDAL matching omission.
Independent review approves pinned Syft 1.57.1 to Grype 0.121.3 for confined
image-only evidence collection: 324/324 Python and 475/475 Debian versions
reconcile in the development-image trial, and Grype detects the omitted GDAL
case. Parser failures and unidentified executables require native SBOM readback;
scanner exit zero alone is insufficient. These are qualification results, not
production common-image dispositions.

Roger approved the concrete policy and selected `/workdir/weppcloud-deployments/`
for retention. Evidence and approved policy hashes are stored in its ignored,
private `.local/dependency-security/` area. CI ingestion and deployment retention
remain M3/M4 validation boundaries. See `artifacts/20261110_m0_validation.md` for
identities, report hashes, measured trials, baseline status, and limitations.
Primary dependencies, deployment code and production systems are unchanged;
candidate dependency changes are confined to the detached checkout.

## Timeline

- 2026-11-11 04:44 UTC: source/tooling discovery and package scaffold.
- 2026-11-11 05:05 UTC: begin M0 full regression baseline on forest.
- 2026-11-11 05:11 UTC: retain isolated scanner trial and independent M0
  security/operations review; concrete owner policy proposal prepared.
- 2026-11-11 UTC: reproduce Trivy matching failure; qualify alternative; obtain
  independent scoped-tool approval and owner policy/storage ratification.
- 2026-11-11 07:18 UTC: green full baseline retained; reviewed M0 checkpoint.
- 2026-11-11 08:52 UTC: importer full regression passes; reviewed local evidence
  importer, candidate test-image wiring and npm lint checkpoint. The detached
  crypto/TLS batch has clean-build, fresh-scan and focused compatibility evidence;
  the final candidate, advisory decisions and deployment integration remain open.
- Pending: exact-image inventory, triage, compatible batches, and gate wiring.
- Pending: complete final regression gates and independent reviews.
- Pending: separately authorized rollout; no production action performed.

## Handoff

The full M0 baseline passes and the reviewed checkpoint accompanies this update.
The scoped tool/policy decision is reviewed and ratified; do not request approval
again. Continue M1 dispositions and native coverage before release acceptance. Use a clean detached checkout for M1: local `out/` is about
852 GiB and is not excluded from Docker context. Preserve the original branch
and unrelated dirty files. Keep raw reports in the owner-selected private store.
The final candidate cannot be handed off unless the exact full pytest and npm
commands pass against the reviewed dependency image and lock.

## Continuation (2026-11-12 UTC)

Roger requested completion through M4 with the F7 continuation. Reconcile the
existing detached crypto candidate and private evidence before further changes.
All policy, advisory, exact-image and final validation gates remain required;
production rollout and risk exceptions remain separate.

2026-11-12: promoted the previously validated crypto/TLS requirement patch to
main source. Standalone evaluator and 35 adversarial/positive tests now pass;
independent security component review approved after coverage fixes. See
[component receipt](artifacts/20261112_evaluator_component.md). Producer, CI
handoff, deploy wiring, native/advisory dispositions and exact-image M4 remain
open. Authenticated SSH/SCP through the existing trusted `runner-02` alias now
passes a disposable synthetic bundle transfer, independent manifest hash check,
private import and remote fixture cleanup. This resolves access discovery, but
actual CI candidate collection before cleanup is still unvalidated. Receipt:
private `remote-transfer-trial-20261112/transfer-receipt.json`.

The small parser batch has disposable compatibility and boundary probes;
Msgpack retained-memory and nbconvert output-path defects reproduce on the old
versions and pass on candidates. These are not clean-build/final-image receipts.
Direct MariaDB/header package inventory reconciles 1,557 regular files and
1,052 symlinks. Advisory and native coverage approvals remain open.

Clean parser candidate build passes from `6c0c213a2` (584.36s), and its isolated
test image builds. Exact candidate focused probes/Quarto render and producer
trial are running. Security review rejected candidate-side Python as inventory
authority; replacement reads a never-started container export under trusted
host Python without extracting/executing its files. M1/M3/M4 remain open.

2026-11-12 deployment integration decision: independent review found that fresh
no-cache rebuilds conflict with exact-image manual approval on a later invocation.
The concrete retained-candidate resume versus same-invocation review proposal is
in `artifacts/20261112_deploy_approval_boundary.md`. Operator selection is pending;
no generic skip-build bypass or deployment workflow change has been implemented.
Producer qualification and advisory review continue independently.
