# Regression Risk Register

## User Experience Risks

| Risk | Failure visible to users | Required control/evidence |
| --- | --- | --- |
| Forced logout | Login prompt immediately after deploy | Legacy SID adoption test with remember cookie absent |
| Lost active form state | Submission fails or page reload required | Existing-page POST and heartbeat across cutover |
| Login/CSRF loop | Repeated 400/401 after reload | Multi-request browser test asserting stable new SID and recorder 204 |
| Shared-device surprise | Wrong identity restored | First signed SID is authoritative; logout cannot scan onward |
| Browser-specific cookie order | Safari fails while Chromium passes | Duplicate-cookie canaries in Safari, Chromium, and Firefox |

## Security Risks

| Risk | Consequence | Required control/evidence |
| --- | --- | --- |
| Cross-account candidate choice | Account confusion or unauthorized access | Skip only bad signatures; never scan past first signed SID |
| Unsigned/forged legacy value | Session fixation | Existing signer validation before Redis lookup |
| Hostile oversized Cookie header | CPU/Redis amplification | Byte, candidate-count, and deduplication bounds |
| Credential logging | Session compromise | Value-free outcome codes and log-redaction tests |
| Legacy override of new state | Downgrade/session fixation | Presence of new name blocks legacy fallback |
| Parent-domain collision recurs | CSRF/session churn returns | `__Host-` invariants and production startup failure |
| Deleting unowned generic cookie | Breaks other applications | No ordinary deletion; response-header regression tests |

## Compatibility and Operations Risks

| Risk | Consequence | Required control/evidence |
| --- | --- | --- |
| Flask/rq-engine name mismatch | Token bridge 401 | Dual-read both services; mixed-version matrix |
| Partial fleet rollout | Intermittent auth failures | rq-engine first; atomic web cutover; no Gunicorn generation overlap |
| Worker configuration drift | Per-request session churn | Startup assertion and effective-name observability |
| Rollback after new-cookie issuance | Users stranded on new name | Never use an unmodified legacy-only rollback image |
| Premature legacy retirement | Dormant active tab loses session | At least one 12-hour TTL plus skew and adoption evidence |
| Redis outage during selection | Login failures or unsafe fallback | Explicit service error; never treat unverifiable candidate as valid |

## Test Matrix Minimum

- New only; invalid new plus valid legacy with no downgrade; legacy only;
  bad-signature legacy before valid legacy; signed missing legacy before valid
  legacy with no onward scan; repeated legacy; multiple identities; new plus
  hostile legacy; no remember token; valid
  remember token; explicit opt-out; logout; CSRF header/form; heartbeat;
  rq-engine token bridge; CAP anonymous state; mixed old/new service versions;
  rollback; first-request POST; oversized/malformed headers; `__Host-` browser
  enforcement; three-browser live smoke.
