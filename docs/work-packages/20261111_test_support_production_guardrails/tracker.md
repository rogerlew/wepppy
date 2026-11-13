# Tracker - Test-support production guardrails and F1-F7 readiness

## Quick Status

Operator clarification (2026-11-12): retained NFS handles require manual
intervention, without automatic waits/retries or process restarts. Existing
support cleanup already fails explicitly; canonical recovery guidance is now
explicit in `docs/schemas/weppcloud-test-support-contract.md`.

**Timezone**: UTC
**Started**: 2026-11-12 01:01 UTC
**Current phase**: M4/M5 passed; full regression failed; F6 M4 remains open
**Last updated**: 2026-11-12 UTC
**Next milestone**: resolve regression failure and F6 M4 before combined readiness
**Finding**: F7 / SEC-07 (Low conditional; High impact when enabled)
**Change security impact**: high
**Dedicated security review**: yes
**Security artifact**: `artifacts/20261111_security_review.md`

Package closure means F1-F7 are ready for an authorized combined deployment
validation, not deployed. F6 M4 and the final combined regression receipt are
hard prerequisites for that claim.

## Task Board

- [x] (2026-11-13 UTC) Corrected Python image `af7643725c95` from
  `64cc736c2` passes 187 focused tests, actual PATH plot readback and frontend
  lint/all 1,079 tests. Fresh scan has zero OAuthlib rows (2,716/332 total).
- [ ] Exact-image full Python gate stopped after 6,304 passes/380 skips on
  missing ASRIS cache-directory setup in the isolated bind mount. Creating the
  ignored directory restores all 25 module tests; full rerun remains required.
  Qualified private GDAL staged
  repair passes 12 crash probes and exact ABI/normal controls; coherent package
  integration remains open. Rasterio TLS runtime isolation, eight-array parity
  and 53 owned consumer tests pass; exact trial security finding is closed by
  supersession. Full GDAL helper and owned Rasterio wheel build pass; 57
  consumer/security tests and 13 GDAL regressions pass. Final image acceptance
  remains open.
  See F6 `artifacts/20261113_gdal_qualification.md`. Resume remains deferred.

- [x] (2026-11-12 UTC) Clean Python image `9f9e75e6515a` passes 187
  focused tests and actual PATH artifact readback; fresh collection succeeds
  (2,717 matches/332 ignored). Scan exposes OAuthlib 4.0.0 still affected;
  4.0.1 follow-up passes 717 upstream and 38 application tests.
- [ ] Rebuild the corrected pin, complete full gates and qualify remaining
  GDAL/native repairs. Resume remains deferred.

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

F6 Mistune/PyCurl candidate pins and focused consumer checks are implemented;
clean batch build and final gates remain open. Resume stays deferred and NFS
retained handles require manual recovery without waits.


### Ready / Backlog

- [x] M0: amend and ratify the canonical deployment-profile, test-support JWT,
      response, and CSRF contract; obtain two independent read-only reviews.
- [x] Commit the M0 contract/review checkpoint as a standalone ancestor and
      record its exact revision here and in the ExecPlan.
- [x] M1: implement production-default profile parsing and startup rejection.
- [x] M2: require the existing scoped WEPP_AUTH bearer on test-support routes;
      add focused no-side-effect negative tests.
- [x] M3: make `wctl run-playwright` mint/capture/inject the short-lived token;
      centralize support-route headers in Playwright smoke helpers.
- [x] M4: validate rendered Compose, actual route inventories, focused Python,
      wctl, npm/Playwright, and unmocked create/load/delete behavior.
- [x] M5: close correctness, QA, and security review findings.
- [ ] M6: wait for and verify F6 M4, reconcile F1-F7 evidence and exact candidate
      ancestry, then run one combined full Python/frontend regression gate.
- [ ] M7: finalize and independently review the deployment-validation plan;
      reconcile the audit board and `PROJECT_TRACKER.md` without deployment.
- [ ] Close the package at pre-deployment readiness and archive the active
      ExecPlan with an outcome summary.

### In Progress

- [ ] Investigate the failed full regression latency assertion; retain the
      required full-gate obligation after F6 candidate freeze.

### Blocked

- [x] Historical NFS deletion and unactivated-profile holds are resolved by
      the authorized repair and live forest acceptance receipt.

- [ ] Package closeout is blocked until F6 reaches its M4 exact-image,
      full-regression, and independent-review acceptance gate.

### Done

- [x] Recorded operator decisions: profile defaults production, agent auth must
      be low friction, smoke markers are excluded, and F7 closes the F1-F7
      pre-deployment remediation phase (2026-11-12 01:01 UTC).
- [x] Confirmed current F7 code registers the blueprint only when the flag is
      true but applies no authentication inside ping/create/delete
      (2026-11-12 01:01 UTC).
- [x] Selected the existing WEPP_AUTH issuer and `wctl` container boundary as
      the smallest low-friction authentication mechanism; no new static secret
      or identity system is proposed (2026-11-12 01:01 UTC).
- [x] Scaffolded package, active ExecPlan, contract decision, failure-class
      matrix, F1-F7 readiness matrix, deployment plan, and review artifacts
      (2026-11-12 01:01 UTC).
- [x] Scoped markdown lint passed for all ten package files, `AGENTS.md`, and
      `PROJECT_TRACKER.md`; root AGENTS size and `git diff --check` passed
      (2026-11-12 01:15 UTC).

## Decisions

- **2026-11-12 01:01 UTC - Default profile is production.** Missing profile is
  not a development shortcut. Recognized non-production values must be explicit;
  unknown values fail startup.
- **2026-11-12 01:01 UTC - Reuse WEPP_AUTH.** A short-lived JWT with audience
  `weppcloud-test-support` and scope `test:support` avoids a new static secret.
  `wctl run-playwright` performs mint/capture/injection so agents do not manage
  login cookies or token copying.
- **2026-11-12 01:01 UTC - No smoke markers.** The scoped bearer is an
  environment-wide development/test support capability. A token holder can
  delete any resolvable run in that non-production environment. Production
  profile exclusion is mandatory and this residual authority is reviewed
  explicitly.
- **2026-11-12 01:01 UTC - F1-F7 roll-up is evidence-only coordination.** This
  package does not rewrite closed/history records or claim deployment. It
  records the evidence grade and unresolved rollout obligations of each owner.
- **2026-11-12 01:01 UTC - F8 stays separate.** Host-port/ingress work may share
  a future deploy window, but it is not necessary to close F7 or the F1-F7
  pre-deployment remediation set.

## Confirmed Starting Evidence

- `configuration.config_app()` parses only `TEST_SUPPORT_ENABLED`, defaulting
  false; there is no canonical runtime deployment profile.
- `_blueprints_context.register_blueprints()` registers `test_bp` whenever the
  flag is true.
- `test_bp._require_enabled()` checks only the flag. Ping, create, and delete
  have no login, role, scope, audience, or ownership check.
- Delete resolves the submitted identifier through `get_wd()` and recursively
  removes the resulting directory. Identifier validation blocks traversal but
  does not establish authorization.
- Production Compose loads a generated env file and does not currently pin the
  test-support flag as a literal service environment value.
- The existing `wctl issue-auth-token` command mints WEPP_AUTH JWTs inside the
  WEPPcloud container, and `auth_tokens.decode_token()` validates issuer,
  signature, time, and audience.
- Six Playwright smoke specifications call create/delete directly, and the wctl
  preflight calls ping without a credential.
- The audit was source/configuration-only; live wepp1 test-support state was not
  verified.

## Validation Matrix

| Boundary | Positive case | Negative/hostile case | Required evidence |
| --- | --- | --- | --- |
| Profile parser | explicit production/development/test | absent defaults production; unknown rejects | focused configuration tests |
| Startup guard | non-production plus disabled/enabled as contracted | production plus enabled rejects | direct app startup tests |
| Route inventory | development/test enabled registers exact three routes | production contains no `/tests/api/*` | actual Flask URL map |
| Bearer validation | exact issuer/audience/scope, unexpired token | missing, malformed, forged, expired, wrong audience/scope | route tests with zero side effects |
| CSRF boundary | bearer-only create/delete works without cookie CSRF | session/cookie alone grants nothing | actual configured Flask app test |
| wctl token handling | wrapper mints and injects token | mint failure exits before ping/npm; token absent from output | wctl unit tests and sanitized transcript |
| Playwright helpers | ping/create/delete carry bearer | unrelated requests do not carry bearer | helper/spec tests and request capture |
| Run lifecycle | create, load, delete, path absent | invalid token creates/deletes nothing | unmocked non-production smoke |
| Production Compose | literal production profile, support disabled | env-file attempt cannot enable route | rendered Compose and route inventory |
| F1-F7 roll-up | exact candidate contains accepted fixes | stale/missing/reopened evidence blocks readiness | readiness matrix and combined gates |

## Risks and Mitigations

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Stale production override triggers startup failure | Medium availability | Medium | pin literals; render before service replacement; fail before disruption | Open |
| Token appears in command/log/test artifact | High | Low | capture output in memory; never argv/URL/log; scan retained evidence | Open |
| Wrapper attaches bearer to unrelated traffic | High | Low | support-route helper only; explicit request-capture tests | Open |
| Smoke client omits auth and silently skips | Medium | Medium | fail fast with actionable wctl error; no anonymous fallback | Open |
| Test token deletes a non-smoke run in non-production | Medium | Low | explicit environment-wide capability; issuer requires authorized host/container access; production route exclusion | Accepted design; reviewer recommendation and owner acknowledgment recorded |
| Default-production breaks raw local startup | Low | Medium | dev Compose sets explicit development; documentation and startup errors | Open |
| F1-F7 readiness overstates F6 or rollout evidence | High | Medium | exact evidence matrix; F6 M4 hard dependency; separate deployed status | Open |
| F8 scope leaks into F7 | Medium | Low | explicit exclusion and separate follow-up | Mitigated by scope |

## Hardening Signal Log

- **Baseline health signals**: feature defaults false, but no profile invariant or
  authentication exists if enabled.
- **Post-change health signals**: production route count remains zero;
  authenticated smoke success; zero side effects on auth denial; wrapper needs
  no manual credential step.
- **Danger signals**: route appears under production, bearer material is
  retained, token reaches unrelated requests, startup silently normalizes an
  unknown profile, or F1-F7 matrix contains an unowned gap.
- **Temporary callus register**: none planned.
- **Observation model**: pre-deployment receipt plus recurrence-triggered new
  package after closure.

## Review Gates

Source/draft approvals below do not waive M4 or authorize release/deployment.

- [x] Operator-approved contract delta captured in canonical documents.
- [x] Two independent M0 contract reviews closed before implementation.
- [x] Standalone M0 ancestor recorded.
- [x] Correctness review passes with no unresolved medium/high findings.
- [x] QA review passes with no unresolved medium/high findings.
- [x] Security review passes with no unresolved medium/high findings.
- [x] Deployment-validation plan receives independent operations/security review.
- [ ] F1-F7 readiness matrix contains exact candidate/evidence identities.

## Verification Checklist

### Focused

- [ ] `wctl run-pytest tests/weppcloud/test_configuration.py --maxfail=1`
- [ ] `wctl run-pytest tests/weppcloud/routes/test_test_bp.py tests/weppcloud/routes/test_blueprint_registration.py --maxfail=1`
- [ ] `PYTHONPATH=/workdir/wepppy pytest tools/wctl2/tests/test_playwright_command.py`
- [ ] Rendered dev and production Compose assertions pass.
- [ ] Targeted Playwright support-route lifecycle passes with token-free logs.

### Combined F1-F7

- [ ] F1-F7 focused owner gates remain green or have exact newer equivalents.
- [ ] F6 M4 exact-image and advisory-policy gate passes.
- [ ] `wctl run-pytest tests --maxfail=1` passes once on the exact final candidate.
- [ ] `wctl run-npm lint` passes on the exact final candidate.
- [ ] `wctl run-npm test` passes on the exact final candidate.
- [ ] Required status2/preflight2 Go gates remain green.
- [ ] Changed-file broad-exception and code-quality observations are recorded.
- [ ] Changed documentation passes scoped `wctl doc-lint`.

### Deployment Planning, Not Execution

- [ ] Exact wepp1/wepp2 service and image impact is inventoried.
- [ ] Canonical `scripts/deploy-production.sh` and installed wctl preset are the
      only planned wepp.cloud deployment entry points.
- [ ] Safe pre-deploy, post-deploy, rollback, evidence retention, and disposable
      fixture checks are specified for F1-F7.
- [ ] Production mutation checks remain blocked until separately authorized.

## Timeline

- **2026-11-12 01:01 UTC** - package scaffolded and operator decisions recorded.
- **Pending** - M0 canonical checkpoint.
- **Pending** - M1-M4 implementation and focused acceptance.
- **Pending** - M5 independent reviews.
- **Pending** - M6 F6 dependency and combined F1-F7 regression receipt.
- **Pending** - M7 deployment-plan review and pre-deployment readiness closeout.

## Progress Notes

### 2026-11-12 01:01 UTC: Initial scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Translated the operator's profile, low-friction auth, no-marker, and F1-F7
  wrap-up decisions into package scope and acceptance gates.
- Reconciled current source, Compose, JWT, wctl, smoke-consumer, and F1-F6
  package evidence.
- Created the required active ExecPlan and review/planning artifacts.

**Blockers encountered**:

- F6 is still executing and must reach M4 before this package can claim combined
  F1-F7 readiness.
- Contract-first policy blocks implementation until M0 is reviewed and committed.

**Next steps**:

1. Draft/amend the canonical test-support and runtime-profile contracts.
2. Obtain two independent read-only reviews and commit the standalone checkpoint.
3. Execute M1-M4 without expanding into markers, a static secret, or F8.

**Test results**: documentation scaffold only. `wctl doc-lint` reports zero
errors/warnings for all ten package files, `AGENTS.md`, and
`PROJECT_TRACKER.md`; `git diff --check` and the root AGENTS 160-line size gate
pass.

## Handoff

Execute
`prompts/active/implementation_execplan.md`. Update this tracker and that plan at
every stopping point. Preserve unrelated dirty work, especially generated
`docs_index.json` and the controller-input-validation package. Do not deploy or
restart forest/wepp1/wepp2 services without explicit authority.

M0 standalone contract ancestor: `21a75b7944573f6b41f6c091349458b5b9ab1e4b` (2026-11-12 UTC).

## Execution update (2026-11-12 UTC)

M0-M3 implementation and independent source reviews are complete. See
[validation](artifacts/20261112_validation.md) for 77 focused Python tests,
59 CLI tests, 1,076 Jest tests and three native HTTP tests, actual production
URL map (zero support rules), and production/wepp1 Compose override resistance.
M4 create/load succeeds with real objects; delete fails path-absence on NFS.
All identified disposable fixtures were recovered after process exit. General
cleanup redesign remains excluded. No service restart or deployment occurred.
F6 M4, exact combined gates and final deployment-plan acceptance remain blocked.
The ExecPlan stays active; no pre-deployment readiness is claimed.

Implementation revision: `c2507338fbdcd5e7156e708f84a43691942ef19f`.

Final local sanity receipt: **13,721 passed, 437 skipped**, exit 0 in 1:04:40.
This shared-worktree run began before final refinements and does not satisfy M6.
F6 tracker recheck still shows M1 in progress; its M4 gate remains unmet.
Before any future reload, the existing development container needs an explicit
development profile; the Compose source edit does not change its environment.
No reload was performed. See the validation artifact for the runtime caveat.

## Authorized continuation (2026-11-12 UTC)

Roger approved bounded NFS cleanup repair and live browser acceptance on forest.
The earlier no-restart/no-cleanup hold is superseded for this workflow. F6 is
also authorized through M4; no production rollout or advisory waiver is implied.
Investigation is active; acceptance remains pending actual artifact evidence.

NFS contract ancestor: `11a805e09`. Both independent contract reviews approved
before implementation. Focused route/RQ tests: 33 passed; logging/NoDb/F5:
43 passed, 2 skipped. Actual NFS removal passed with three living controller
processes and late records preserved listeners without recreating the path.
500-record queue drain: old 0.02015s, new 0.51923s; full record readback matched.
Correctness review found permissive lexists absence readback; changed to lstat
with only FileNotFoundError proving absence, adding EACCES/ESTALE regressions.

Forest M4 acceptance now passes; see [receipt](artifacts/20261112_forest_acceptance.md).
The historical NFS/browser hold is resolved for the exercised workflow. F6 and
combined candidate gates still block package closure.

Live forest M5 also passes: actual Chromium runs0 page load, missing/invalid
bearer denials, valid deletion with lstat absence, and exact minted-token scans
across 147 output/log/trace/report items. All log collection commands returned
zero. Independent QA closed the log-command and three-part-runid evidence gaps.
The current full regression failed at a latency assertion; this dev-runtime receipt cannot
substitute for F6's exact final-image M4 or F7's combined M6.

2026-11-12 full regression update: the exact command stopped after 13,528 passes
and 437 skips at the run-catalog readonly-marker notification latency assertion:
catalog p95 244.22ms versus baseline 0.65ms exceeds the 50ms delta contract.
This is a failed receipt, not M6 acceptance. Docker image export overlapped;
observed host I/O pressure motivates a quiet focused reproduction after export,
without relaxing the threshold. No logging path is called by the marker setter.
Receipt: `out/f7-nfs-20261112/full-pytest-failure-receipt.json`.

Quiet focused follow-up passes both marker-latency cases without changing the
50ms contract: readonly p95 delta 5.62ms; TTL 4.98ms. The preceding export-overlap
follow-up passed readonly but failed TTL (477.92ms). This supports host I/O
contention as the cause; it does not replace the still-required exact full rerun.
Retained logs: `/tmp/f7-catalog-latency-quiet.log` (mixed result during export),
`/tmp/f7-catalog-latency-no-export.log` (2 passed in 11.08s).

2026-11-12 continuation: F6's isolated OAuth candidate builds cleanly, passes
50 callback tests and removes 18 Authlib rows in its fresh scan. Its actual gate
still rejects native coverage; CI/deployment integration and final broad gates
remain open. Forest live acceptance remains passed, but this does not close F7
M6/M7 or F6 M4. See F6 `artifacts/20261112_oauth_candidate_validation.md`.
