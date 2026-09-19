# Cover defaults and WEPP API omission

Status: completed and validated on Forest, 2026-09-19 UTC.
Owner: requesting user; implementer: Codex. Production deployment excluded.

Correct two bounded propagation defects: configured cover defaults update MOFE
summaries after management generation, and an omitted `kslast` request field
clears the saved soil conductivity override. Preserve existing explicit-value
semantics, default precedence, RAP canopy behavior and single-OFE behavior.
WEPP compiler detection/rejection is explicitly deferred. No production deploy,
named-source repair, parameter-value change or queue redesign is authorized.

Complexity budget: local edits to `Landuse.set_cover_defaults` and
`WeppInputParser.parse`, existing test suites, and reusable validation evidence.
No new dependencies, services, schemas or transactional publication mechanism.
Security impact: low; no authentication, route, filesystem-boundary or queue
wiring change. Dedicated security review is not required for this scope.

Acceptance: reviewed contract ancestor; failing then passing regressions;
real generated/prepared management and soil readback; durable reload; failure
and retry; canonical archive/restore and normal browser/download evidence;
Forest disposable-project validation; broad suite and independent final review.
Source equestrian-bonheur remains untouched. Validation fixtures may supply
explicit configured defaults because that source has none.

Outcome: both fixes implemented; 286 focused tests and 9,079 broad tests pass
(99 skipped). Forest execution, generated/prepared readback, normal downloads,
archive/restore and independent final review pass. See retained
[validation](artifacts/20260919_validation.md) and
[review](artifacts/20260919_correctness_review.md).

See [plan](prompts/completed/execplan.md), [tracker](tracker.md),
[checkpoint](artifacts/20260919_contract_decision.md), and
[ADR](../../adrs/ADR-0070-cover-defaults-and-kslast-omission.md).
