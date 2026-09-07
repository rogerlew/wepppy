# Contract decision

Base revision: f587b9908abbdeefd9ce4b1e882908180cd4756e.
Operator approval: “let's do the flask only hood and defere the other service routes”.
Classification: intended behavior change, not restoration of an existing contract.
Normative delta: `docs/schemas/flask-run-config-contract.md`; no changes to
CSRF/session/project-owned config policies. Those contracts remain applicable.
The prior assessment's shared resolver is narrowed to Flask. Application-level
preprocessing covers blueprints outside the run-context allowlist. Response-stage
redirects preserve endpoint guards. No persistence mutations or new dependencies.
Compatibility: stale URL requests use stored identity; missing/corrupt identity
fails explicitly; absent optional manifests remain valid. Security: high, existing
guards retained, no generic auth substitute. Regression matrix is in the contract.
Independent reviews and their disposition follow before implementation.
