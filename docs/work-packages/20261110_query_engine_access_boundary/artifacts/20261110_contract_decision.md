# Contract decision - Query-engine HTTP access boundary

Status: exact proposal prepared; independent M0 reviews passed; operator
ratification and standalone checkpoint pending. No implementation changes.

Remediation ID: `QE-AUTH-F1-20261110`. Starting implementation:
`b3786ae7e771f686bca3c2c2b695878bcdc0ccbd`. Fetched origin:
`ef5b4e2890cd7d860ee01bcc37e67fff41be4f87`. Prepared 2026-11-11 UTC.

## Authority and discrepancy classification

The operator requested execution of this package on 2026-11-11 UTC. That
request authorizes preparation and independent review. The scaffold left exact
scope/activation decisions unresolved; the revised choices below are submitted
for exact ratification before implementation under the contract-first standard.
No production action is authorized by this checkpoint. No branch was switched.

This is an intended behavior amendment, not a conformance-only repair. Existing
HTTP routes accept filesystem-shaped targets and lack ordinary-run access
checks. New browser transport and activation/origin rules need explicit intent.
The initial draft also missed established ownerless/PCV visibility and resolver
side effects; those must be reconciled rather than silently redefined by code.

## Applicable canonical contracts

- New `docs/schemas/query-engine-http-access-contract.md`: exact proposed rules.
- `docs/composite-runid-slugs.md`: layouts, parent identity, shared inputs.
- `docs/schemas/weppcloud-session-contract.md`: session/marker lifecycle.
- `docs/dev-notes/auth-token.spec.md`: audience, class, scope, revocation.
- `docs/schemas/weppcloud-csrf-contract.md`: shared browser origin guard.
- `docs/schemas/feature-access-governance-contract.md`: grouped admission and
  shared retained results; explicit bounded cross-link added.
- `docs/ui-docs/contracts/combined-watershed-viewer-contract.md`: existing
  ownerless/PortlandGroup grants and real multi-run entry; cross-link added.
- `docs/schemas/query-engine-catalog-refresh-contract.md`: unchanged readonly,
  automatic repair, source-selection and parent-backed catalog behavior.
- `docs/schemas/weppcloud-browse-auth-contract.md`: unchanged browse defaults;
  reuse of shared helpers must preserve them.
- `wepppy/query_engine/README.md`: public HTTP/MCP surface and direct transport.

## Exact delta and rationale

The new query HTTP contract contains the complete route, resource, operation,
credential, error and origin matrices. The material decisions are:

1. HTTP requires `runid/config`, never a filesystem path. MCP retains its bare-ID
   API. Use side-effect-free canonical resolution; no pre-auth Omni fixups,
   cache mutation, catalog or log writes. Every auth/recheck uses the same
   checked parent/root, and body-selected scenarios are checked before activation.
2. Preserve PUBLIC and existing ownerless ordinary retained-result reads, including
   the PCV-01 historical catalog. Ownership lookup failure is never ownerless.
   Require existing readable `ron.nodb` for ownerless admission. Private owned
   runs require current owner/Admin/Root or an existing exact PCV catalog grant;
   bound service grants remain independently valid. Group/profile roots do not
   inherit the ordinary ownerless exception.
3. Use existing JWT machinery with exact `query-engine` audience. Authenticated
   discovery requires `runs:read`; POST query also requires `queries:execute`.
   Explicit bearer credentials take precedence; public anonymous reads have a
   documented scope exception. Parent-bound credentials admit Omni children;
   child credentials do not admit siblings/parents. Preserve grouped aliases.
4. Hash cookie names for every run/config under `/query-engine/runs/`, with
   HttpOnly, production Secure, SameSite=Lax, no Domain, distinct jti, exact
   signed resource/config binding and existing four-day bridge/marker lifetime.
   The original ordinary per-run path cannot reach private Omni URLs. No query
   token enters JS/HTML/URLs/logs. Cover actual direct dashboard/report/viewer
   entry points, not only the no-config bridge. Test 100-run browser/ingress
   limits before any transport expansion.
5. Forced activation is POST-only. Bearers require `runs:read runs:activate`.
   Cookies require read/query scopes, verified current human owner/Admin/Root
   or grouped inspection authority and the canonical same-origin guard. PCV
   membership and anonymous sessions grant no forced activation. This explicit
   cache-only exception preserves least-privilege page scopes.
6. Cookie POST query also uses the existing same-origin guard. A present Origin
   must be in `QUERY_ENGINE_ALLOWED_ORIGINS`; CORS permits only exact configured
   origins and required methods/headers. Public non-browser query clients may
   omit Origin. Deployment must configure its exact public origins.
7. Preserve authorized cache creation, repair, readonly behavior, parent-backed
   landuse/soils inputs and existing SQL containment. No new feature entitlement,
   datastore, service, protocol, dependency or deployment topology is introduced.

Rejected alternatives: Flask response proxy (violates direct-query architecture),
JavaScript-readable token (unnecessary exposure), ownerless lockdown (conflicts
with PCV), parent-only narrow cookie path (breaks Omni transport), and applying
mandatory HTTP config parsing globally (breaks MCP callers).

## Compatibility, security and regression evidence

Security impact is high: public auth, path resolution, cookies and CORS. No model
parameterization or scientific data/schema mutation is proposed; no ADR required.

Compatibility obligations include direct private entry, Omni selection,
multi-run collection entry, legacy ownerless/public runs, authorized private
owners/roles/services, grouped aliases, profile roots, readonly/malformed cache
states, current owner/group removal, and stale/revoked credentials. The failure
matrix records both request and stored-state coverage. Run catalog/log/link
hash/absence checks for denials; use real JWTs, filesystem and browser ingress.
Unmocked MCP resolver coverage is required because its route tests can otherwise
mock the changed boundary away.

## Approval and reviews

- Operator exact ratification: pending for this revised proposal.
- Independent correctness contract review: passed 2026-11-11 01:26 UTC, `/root/contract_correctness`.
- Independent security contract review: passed 2026-11-11 01:26 UTC, `/root/contract_security`.
- Review disposition: see `20261110_contract_reviews.md` (both passed; no medium/high contract findings).
- Canonical amendments: prepared with explicit proposed/conformance-pending status.
- Standalone ancestor: pending ratification and review closure.

After ratification, mark the proposal accepted, commit only this package and its
canonical amendments as a standalone checkpoint, and record the SHA before tests
or source edits. Existing unrelated edits must not enter that commit.

## Operator ratification, 2026-11-11 UTC

The operator explicitly approved: "I approve the revised contract. please commit
and proceed". This ratifies the reviewed exact matrix and authorizes its
standalone checkpoint and implementation. Production actions remain separately
gated. Prior pending statements above record the preparation state.
