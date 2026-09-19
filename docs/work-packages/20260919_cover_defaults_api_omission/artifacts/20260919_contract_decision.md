# Contract decision: COVER-DEFAULTS-KSLAST-01

2026-09-19 UTC; starting implementation `1b4f9af72`.
Operator: "scaffold and execute work-package for cover-defaults and api ommission.
let's defer the wepp exec work for now". This authorizes the bounded fixes
discussed immediately beforehand, not compiler work or broader API redesign.

Authority: `docs/schemas/mofe-management-artifact-contract.md`, Configured cover
defaults; `docs/schemas/wepp-run-input-contract.md`, kslast omission;
`docs/schemas/nodb-persistence-concurrency-contract.md` remains unchanged.
Classification: intended behavior amendment; implementation conformance pending.

Delta: apply all applicable configured covers as today, then regenerate MOFE
managements once using saved segment assignments. No defaults/no matching class
is a no-op. Reapply and regenerate on retry even if saved values already match:
a prior writer failure may have persisted intent but left incomplete files.
Keep current default-overrides-user precedence during default application;
do not reinterpret defaults as absent-only or alter RAP canopy precedence.

For WEPP requests, absence of `kslast` preserves durable state, including None,
zero and supported legacy absence. Explicit blank/null and existing none-prefixed
strings still clear; numeric/list coercion and malformed-value behavior stay
unchanged. No generic PATCH conversion of other fields is included.

Compatibility/regression plan: no field, schema or unit change. Existing files
change only on supported rebuild; clients wanting to clear kslast must send an
explicit clearing value. Test missing/empty/populated/legacy states separately
from payload encodings; retain existing errors for malformed defaults and
assignments. No silent fallback or swallowed writer failure. Read actual combined
and prepared managements and soil conductivity, durable NoDb reload, failed
writer retry, canonical archives, and normal project downloads. Exercise on a
disposable Forest project with explicit test defaults; preserve source hashes.

Security: low, existing locks/authorization/path rules unchanged. Source boundary
is two NoDb methods; route tests may exercise existing transport without editing
handlers. Model/compiler changes, defaults values, queue topology and production
deployment excluded. Both independent reviewers (`defaults_contract1` and
`defaults_contract2`) approve with no blockers. Their shared implementation
watchpoint is explicit nonempty saved-assignment validation before mutation
when defaults apply; added to the canonical section. No-op default cases remain
no-ops even without assignments. No implementation edit before checkpoint.
