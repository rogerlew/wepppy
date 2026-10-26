# Contract checkpoint decision

Starting implementation revision: `e5e59e83256a19ba5fc9b5f5c8401f3848e11e73`. Operator authorization: “scaffold and execute work-package to implement with systemd timer ... test it end to end through systemd and validate the JWT is updated on wepp2 ... documented in ... docs/culvert-at-risk-integration”. This authorizes the bounded implementation, checkpoint commit, delivery key, live installation and tests described in the plan; no unrelated deployment.

Applicable contracts: docs/schemas/culvert-jwt-renewal-contract.md; docs/schemas/feature-access-governance-contract.md (Culvert client registration); docs/dev-notes/auth-token.spec.md (unchanged JWT validation); docs/schemas/rq-response-contract.md (unchanged HTTP responses).

Normative delta: automatic operator-managed renewal for registered submit-only identity, file-based per-submission consumption with env compatibility, restricted delivery and verified atomic replacement. Implementation conformance pending. This repairs an expired-credential lifecycle failure; it does not claim the TLS symptom is solely JWT-related.

Rationale: manual 90-day renewal repeatedly failed. Reuse issuer/SSH/systemd before introducing mTLS/issuer API. Security impact high; preserve principal, scope, expiry policy, signing-key boundary and rollback overlap. Compatibility: env-only clients retain behavior; configured file missing/empty raises an explicit credential error. Regression evidence: actual filesystem, TLS, restricted SSH, systemd, container and consumer boundaries plus focused tests. Independent reviews pending.
