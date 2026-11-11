# Tracker - wepp1 common-image dependency security gate

## Quick Status

**Timezone**: UTC  
**Last updated**: 2026-11-11 UTC  
**Current phase**: M0 complete; M1 image dispositions and native coverage in progress  
**Finding**: F6 / SEC-06 (Medium, exploitability unconfirmed)  
**Change security impact**: high  
**Dedicated security review**: `artifacts/20261110_security_review.md`  
**Starting revision**: `2041fb8e2`

## Task Board

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

Preparatory unchanged-source common-image build succeeds, using canonical
production/wepp1 Compose overlays and immutable base/vendor arguments. Exact
image ID and command evidence are in `artifacts/20261111_baseline_image.md`.
Native import readback passes as UID 1002/GID 130; GDAL/Fiona use GDAL 3.10.3
while Rasterio bundles 3.8.4. Image inventory/scan and the full baseline rerun
have completed. The refreshed database currently exceeds the 24-hour freshness
limit, so resulting scans are triage evidence only.

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
No dependencies, workflows, deployment code, or production systems have changed.

## Timeline

- 2026-11-11 04:44 UTC: source/tooling discovery and package scaffold.
- 2026-11-11 05:05 UTC: begin M0 full regression baseline on forest.
- 2026-11-11 05:11 UTC: retain isolated scanner trial and independent M0
  security/operations review; concrete owner policy proposal prepared.
- 2026-11-11 UTC: reproduce Trivy matching failure; qualify alternative; obtain
  independent scoped-tool approval and owner policy/storage ratification.
- 2026-11-11 07:18 UTC: green full baseline retained; reviewed M0 checkpoint.
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
