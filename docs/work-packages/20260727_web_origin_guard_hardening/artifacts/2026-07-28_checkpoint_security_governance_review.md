# REM-04 checkpoint security and governance review

**Review type**: Independent read-only WP00 checkpoint review

**Remediation / milestone**: REM-04 / GOV-00A-M1D

**Reviewed starting revision**: `4c574dcd6c6a07b80cc0e704961f108728ab90ea`

**Review scope**: Authority, scope containment, CSRF/origin spoofing,
forwarded-header trust, cookie deletion boundaries, diagnostics disclosure, and
contract-first eligibility

**Implementation review**: Current implementation was read only as evidence;
it was not treated as normative intent.

## Verdict

**Fail — checkpoint is not ready for the standalone ancestor commit.**

Unresolved findings: **1 high, 2 medium, 0 low**.

The operator's requests to execute the revised package provide explicit
authorization for the finite remediation described by the checkpoint. The
GOV-00A-M1D decision and REM-04 register row also satisfy the bounded-remediation
registration shape: stable id, dated package, borrowed owners, exact source
boundary, exclusions, high security classification, and operator authorization
are present. Those elements are conditional checkpoint candidates, not yet
effective authority. The checkpoint still fails
`docs/standards/contract-first-change-standard.md` because an applicable
canonical contract conflicts with the amendment and material security rules are
not sufficiently closed for consistent implementation and regression review.

## Findings

### High — H1: Forwarded-origin authority conflicts with the still-canonical session contract

**Evidence**

- The contract decision lists
  `docs/schemas/weppcloud-session-contract.md` as applicable.
- The proposed CSRF contract says raw `X-Forwarded-Proto`,
  `X-Forwarded-Host`, `X-Forwarded-Port`, and `X-Forwarded-Ssl` values must not
  independently add allowed origins and says
  `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` must no longer expand the guard.
- The session contract's “Same-Origin and Security Contract” still explicitly
  permits those rq-engine forwarded-origin aliases when
  `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true` and recommends configured
  external aliases as a preference rather than a requirement.
- The current rq-engine helper implements that session-contract switch, showing
  that the conflict controls a real authorization path rather than editorial
  wording.

**Impact**

Two simultaneously applicable canonical contracts authorize opposite behavior
at a cookie-authenticated token-minting boundary. Choosing either behavior in
WP01 would use implementation to resolve normative intent. This is exactly the
contract-conflict stop condition in the contract-first standard, and retaining
the switch can allow attacker-controlled forwarded headers to enlarge the
accepted-origin set when ingress does not overwrite them reliably.

**Required action**

Amend the session contract in WP00 to remove the compatibility exception,
cross-link the shared browser-origin rule, and state the migration consequence
for deployments that enabled the switch. Record the conflict and its
disposition in the contract decision. Add a regression vector proving that the
enabled legacy environment variable cannot add an allowed origin. Re-review
the reconciled checkpoint before committing it.

### Medium — M1: “Trusted proxy” authority is asserted without an enforceable trust precondition

**Evidence**

- The proposed rule permits allowed origins from framework request properties
  “after the configured trusted-proxy middleware” and describes the TLS bridge
  as a “trusted-proxy scheme mismatch.”
- Flask globally installs `ProxyFix(..., x_proto=1, x_host=1, x_port=1)`; the
  rq-engine installs no corresponding proxy-header middleware; the
  query-engine helper currently reads raw forwarded headers itself.
- REM-04 expressly excludes Caddy configuration and deployment, and neither the
  amendment nor the registration identifies the ingress invariant that makes
  framework-normalized scheme/host/port authoritative for each of the three
  services.
- The regression table says “trusted internal HTTP request” but provides no
  negative vector for a direct/untrusted request carrying spoofed proxy headers.

**Impact**

Implementers and reviewers cannot distinguish a trustworthy framework-derived
public tuple from request state rewritten using untrusted client headers.
Removing direct header reads alone does not establish a trusted boundary,
especially for Flask where framework properties are themselves ProxyFix
outputs. This leaves origin spoofing dependent on undocumented topology.

**Required action**

Define, per service, the exact authoritative inputs and required ingress
precondition. State that deployments must ensure the service is reachable only
through the configured final trusted proxy (or name an existing enforceable
equivalent), and define safe behavior when that precondition/public origin is
not available. Add negative vectors for raw forwarded headers on an untrusted
request and for conflicting normalized Host/port inputs. If satisfying this
requires proxy or deployment changes, revise the registered scope and obtain
the corresponding authority rather than silently relying on excluded work.

### Medium — M2: The copied-report “fixed catalog” does not define the fixed title/severity mapping or constrain report metadata values

**Evidence**

- The diagnostics amendment says title and severity come from a fixed report
  catalog and calls the complete catalog normative.
- It enumerates fourteen check ids, but does not map any id to its fixed title
  and severity.
- `overall` and `generated_at` are allowed fields without a normative value
  domain or derivation rule. The fixed status-to-message mapping is complete,
  but the other copied values are not.
- Current runtime check definitions contain the missing title/severity values;
  under the contract-first standard, those implementation values are evidence
  and cannot manufacture normative intent.

**Impact**

WP03 could still copy runtime-controlled title/severity or accept arbitrary
report metadata while claiming conformance to an allowlist. That weakens the
disclosure boundary and prevents exact hostile-input tests from proving that
all copied prose is fixed.

**Required action**

Add the complete id-to-title-to-severity table to the canonical diagnostics
spec. Define `overall` as a fixed enumeration derived only from sanitized
checks, define `generated_at` as a locally generated timestamp in a stated
format, and retain `site_prefix` as normalized path-only data. Add hostile
runtime title/severity/overall/timestamp cases to the proposed regression
evidence and prove none are copied.

## Confirmed controls

- Scope containment is otherwise explicit: only three existing guards, reset
  cookie-target construction, copied-report construction with narrowly adjacent
  safe probe codes, focused tests, and governance documentation are included.
- New endpoints, authentication/role changes, OAuth, Caddy/deployment, queue
  wiring, schemas, parameterization, diagnostics presentation, and unrelated
  owner work are expressly excluded.
- The reset-cookie rule is appropriately narrow: configured session and
  remember tuples only, host-only semantics for unset domains, no synthesized
  parent/path variants, and no generic CSRF cookie names.
- The origin decision order correctly makes `cross-site` reject and prevents a
  present conflicting `Origin` from being overridden by
  `Sec-Fetch-Site: same-origin`; existing CSRF and authentication remain
  layered requirements.
- The package correctly uses the full checkpoint path rather than classifying
  normative hardening as urgent conformance restoration.

## Gate conclusion

Operator approval and bounded-remediation registration are sufficient in form,
but the checkpoint as a whole is not yet acceptable. H1 and both medium
findings must be resolved and dispositioned, followed by independent re-review.
No production implementation file may be edited until both checkpoint reviews,
the primary-agent disposition, reconciled canonical contracts, registration,
and governance milestone are committed together as a standalone ancestor and
its full revision is recorded in the REM-04 tracker.

## Post-Fix Rereview — 2026-07-28

**Verdict**: **Fail — one high finding remains.**

Remaining unresolved findings: **1 high, 0 medium, 0 low**.

### Finding status

- **H1 remains open.** The session contract now correctly delegates to the
  shared browser-origin contract, makes
  `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` inert, documents the deployment
  migration, and requires a negative regression. However, the same amended
  `docs/schemas/weppcloud-csrf-contract.md` still contains a contradictory
  requirement under “rq-engine and 3rd-Party API Requirements”:
  “Forwarded-origin aliases (`X-Forwarded-Proto`, `X-Forwarded-Host`) for
  rq-engine cookie-path same-origin checks MUST remain opt-in via
  `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`.” This conflicts inside the
  canonical CSRF contract with the new rule that the switch is inert and raw
  forwarded headers never add allowed origins. Remove or replace that stale
  requirement with a cross-reference to the Browser Same-Origin Guard Contract,
  then re-run this review.
- **M1 is closed.** The amendment now identifies authoritative inputs and
  ingress preconditions per service, defines safe rejection when public
  authority is unavailable, limits the bridge to the exact HTTP:80 to HTTPS:443
  same-host pair, and requires raw-forwarded-header and alternate-bridge
  negative vectors.
- **M2 is closed.** The diagnostics contract now provides the complete immutable
  id/title/severity mapping, fixed status messages, sanitized `overall`
  derivation, locally generated timestamp, constrained path-only prefix, and
  hostile/duplicate/unknown input vectors.

No additional high or medium issue was identified beyond the remaining internal
forwarded-origin contradiction. Operator authorization and the
REM-04/GOV-00A-M1D registration remain sufficient in form, but the checkpoint
cannot pass or become the standalone ancestor while H1 remains unresolved.

## Final Post-Fix Confirmation — 2026-07-28

**Verdict**: **Pass.**

Remaining unresolved findings: **0 high, 0 medium, 0 low**.

H1 is closed. The stale rq-engine requirement in
`docs/schemas/weppcloud-csrf-contract.md` now states that raw forwarded-origin
aliases must not authorize the cookie path, the legacy
`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` variable is accepted but inert, and
deployments must use explicit external host/scheme configuration. This is
consistent with the Browser Same-Origin Guard Contract, the amended session
contract, the contract-decision conflict disposition, and the required
environment-switch negative regression.

M1 and M2 remain closed. No new high or medium issue was identified. The
security/governance review gate is satisfied, subject to the other independent
review, primary-agent disposition, documentation validation, and creation of
the required standalone checkpoint ancestor.
