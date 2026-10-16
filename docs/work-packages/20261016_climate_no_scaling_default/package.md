# New-project NoScaling default

Scope: explicitly initialize otherwise unset scaling to NoScaling after existing
configuration resolution. Existing projects, getters, templates, configured
precedence, numerical operations and the prior EDDE fix are outside this change.
Complexity budget: one constructor assignment branch, focused tests and docs;
no new infrastructure or dependencies. Security impact: none; no dedicated
security review required. Completion requires constructor/reload and rendered
radio evidence, existing EDDE regression, and independent correctness review.

The [checkpoint](artifacts/20261016_contract_decision.md) records the approved
behavior. Implementation followed authorized checkpoint `88c8c9fdc`.
Focused validation passed 291 distinct tests. The broad suite and final review are
recorded in the tracker; no production deployment is claimed.
