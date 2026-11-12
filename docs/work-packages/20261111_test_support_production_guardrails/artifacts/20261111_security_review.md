# Security review - Test-support production guardrails and F1-F7 readiness

## Metadata

- **Package**: `docs/work-packages/20261111_test_support_production_guardrails/`
- **Reviewer**: unassigned; must be independent of implementation author
- **Date**: pending
- **Scope reviewed**: deployment profile, Flask registration/routes, WEPP_AUTH
  bearer use, CSRF exemption, wctl/Playwright transport, Compose, evidence
  handling, and F1-F7 readiness/deploy planning
- **Commit/branch context**: pending final candidate; starting revision
  `cfa1fc6e79ad1db643bd70c95bc8d44dc7083367`
- **Related artifacts**:
  - Correctness: `artifacts/20261111_correctness_review.md`
  - QA: `artifacts/20261111_qa_review.md`
  - Contract decision: `artifacts/20261111_contract_decision.md`
  - Failure matrix: `artifacts/20261111_failure_class_matrix.md`

## Security Triage Decision

- **Security impact level**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the package changes whether public routes exist,
  validates signed bearer credentials, exempts mutations from cookie CSRF,
  transports a transient token through agent tooling, and constrains production
  deployment configuration.
- **Threat model assumptions**:
  - Missing/invalid profile cannot enable a non-production capability.
  - Only authorized host/container users can mint WEPP_AUTH tokens through wctl.
  - Production does not register the routes, regardless of credential validity.
  - Development/test token holders are trusted with environment-wide support
    create/delete authority.
- **Valid states controls must preserve**: production support absence, ordinary
  dev startup with support disabled, authorized no-ceremony agent smoke,
  existing successful endpoint payloads, and explicit denial/error paths.

## Initial Findings Register

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Production registration | Env drift or profile parsing could register support routes in production | Default production, literal Compose values, startup rejection, actual route inventory | Open |
| SEC-02 | High | Bearer auth | Validation after parsing/filesystem work would retain an unauthenticated side effect | Authenticate first; negative state assertions | Open |
| SEC-03 | High | Token handling | Automatic mint/injection could leak JWT through stdout, argv, URLs, reports, logs, or broad request headers | In-memory capture, narrow helper, exact-token scans | Open |
| SEC-04 | Medium | CSRF/auth composition | Broad CSRF exemption could allow session-only mutation or affect unrelated routes | Exempt exact bearer-only views; cookie-alone denial | Open |
| SEC-05 | Medium | Non-production deletion | Valid token can delete any resolvable run in its environment | Explicit privileged capability, production exclusion, short TTL, owner acknowledgment | Open pending risk acceptance |
| SEC-06 | Medium | Profile compatibility | Unknown/default handling could silently become development or break with a fallback | Strict enum, no fallback, startup tests/docs | Open |
| SEC-07 | Medium | Readiness governance | Roll-up could mark partial F1-F7 work complete or hide deployment gaps | Exact evidence matrix, F6 M4 gate, evidence-grade vocabulary | Open |
| SEC-08 | Low | Audit/log detail | Auth failures may disclose bearer/claims or enable log flooding | Token-free bounded audit fields; no raw payloads | Open |

Risk acceptance requires security reviewer recommendation and explicit package
owner acknowledgment. SEC-05 cannot be marked accepted from this scaffold.

## Surface Checks

### Valid-State Non-Interference

- [ ] Correctness matrix covers absent, disabled, enabled, legacy, and hostile
      states separately.
- [ ] Production absence and authorized agent usability both have direct tests.
- [ ] Security checks do not add manual login/cookie/CSRF ceremony to the
      canonical smoke wrapper.
- [ ] No implementation success is inferred from a status code alone.

### Authentication, Authorization, and CSRF

- [ ] Exact issuer/signature/time/audience validation uses existing WEPP_AUTH.
- [ ] Exact `test:support` scope is required before any side effect.
- [ ] Missing/invalid/wrong-audience/expired returns 401; missing scope returns
      403; production remains unregistered/404.
- [ ] Cookie/session alone grants no authority.
- [ ] CSRF exemption is limited to bearer-only support views.
- [ ] Token lifetime is bounded and documented; no anonymous fallback exists.

### Secrets and Credential Handling

- [ ] No new signing secret or plaintext/static test token is introduced.
- [ ] Existing `WEPP_AUTH_JWT_*_FILE` contract remains unchanged.
- [ ] Token mint output is captured without logging and passed only to the
      intended child/helper.
- [ ] Tokens do not appear in argv, URLs, profiles, screenshots, traces,
      Playwright reports, retained JSON, logs, or exception output.
- [ ] No production support token is minted or mounted.

### Input and Filesystem Boundaries

- [ ] Existing run-ID traversal/NUL/separator validation remains intact.
- [ ] Auth occurs before `parse_json_payload`, `create_run_dir`, `get_wd`, or
      `shutil.rmtree`.
- [ ] Denied create/delete cases prove filesystem noninterference.
- [ ] Valid deletion is restricted by the documented non-production profile and
      bearer capability; no hidden marker/registry state exists.
- [ ] Error handling does not silently claim cleanup success when the target
      remains.

### Agent Tooling

- [ ] wctl mints inside the WEPPcloud container using existing secret mounts.
- [ ] Tool logs show commands but never captured token stdout.
- [ ] Playwright receives the token transiently and attaches it only to support
      requests.
- [ ] Direct-agent guidance does not encourage printing/copying long-lived
      tokens.
- [ ] Mint failure stops before network mutation.

### Deployment and Supply Chain

- [ ] Production profile and disabled flag are literals in effective Compose.
- [ ] Host overrides cannot weaken the invariant.
- [ ] F6 exact-image evidence matches the combined candidate.
- [ ] Deployment plan uses installed wctl and `scripts/deploy-production.sh`.
- [ ] F8 is not silently implemented through this package.
- [ ] No production action occurs under this package's current authority.

### Logging and Incident Readiness

- [ ] Auth outcome logs contain route/status only, with bounded cardinality.
- [ ] Production route inventory and startup failure are observable.
- [ ] Rollback preserves the production route-absence invariant.
- [ ] Any recurrence opens a new package rather than mutating closed history.

## Validation Evidence

- Automated checks: pending.
- Actual configured Flask/route inventory: pending.
- Unmocked non-production smoke: pending.
- Exact-token retained-output scan: pending.
- Combined F1-F7 gates: pending F6 M4 and final candidate.
- Deployment-plan independent review: pending.

## Residual Risk

- A valid test-support bearer can create and delete any resolvable run in the
  configured development/test environment. The proposed justification is that
  minting requires authorized host/container access and production categorically
  excludes the routes. Reviewer recommendation and operator acknowledgment are
  required at closeout.
- Production deployment validation remains outstanding after package closure;
  the final status must remain pre-deployment-ready until separately executed.

## Verdict

- **Gate status**: fail until implementation, evidence, and review complete.
- **Unresolved findings**: High 3; Medium 4; Low 1 at scaffold.
- **Release recommendation**: hold.

## Sign-off

- **Security reviewer**: pending.
- **Package owner**: pending.

## Artifact Observability Gate

The package does not change model/report artifacts. It does create disposable
run directories and retained validation records.

- [ ] Create/load/delete evidence uses normal authorized project tools and
      direct filesystem readback.
- [ ] Failed creation/deletion state is visible and cleanup is verified.
- [ ] Retained readiness/deployment artifacts include provenance and results
      without credentials or private data.
- [ ] No hidden registry or marker is required to understand cleanup authority.

Reference:
`docs/standards/artifact-observability-standard.md` and
`docs/standards/generated-artifact-validation-standard.md`.
