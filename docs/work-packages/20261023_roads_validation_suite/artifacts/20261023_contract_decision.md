# Roads validation suite contract checkpoint

Starting implementation revision: `a7ea23927`. Operator authority: Roger explicitly
requested a site-based Roads parameter validation suite comparable to disturbed,
with a generated report vendored and linked in Usersum. Task-scoped commit
permission persists from this conversation.

Applicable authorities: new roads-validation-suite-contract; existing
roads-segment-loss-summary-contract, roads-water-accounting-contract, roads-preparation-lifecycle-contract, output-scope-contract,
and Usersum specification. Existing numerical, lifecycle and publication machinery
is reused. No formula/default/schema or user-access behavior changes are proposed.

Normative delta: define 504 canonical profile combinations, bounded sensitivity
controls, four full-project design checks, scientific fixture/provenance/report
requirements, and one additive user-readable Usersum vendor/nav entry. Source
fixtures exclude private controller/account state. Scratch runs cannot target the
source. Report scope distinguishes full-profile detachment/export from road-only
and watershed quantities. No universal monotonicity test is permitted.

Valid states: fresh complete matrix publishes; incomplete/empty matrix rejects;
malformed/nonfinite/duplicate-calendar sources reject; old report identities fail
freshness or are explicitly marked stale. Missing optional local full-site fixture
may skip that explicitly opt-in test, but cannot satisfy package acceptance.
Portable profile tests need only committed scientific inputs and installed model
libraries. Legacy beta project outputs never become fresh matrix evidence.

Compatibility: additive tests and documentation, existing outputs and defaults
unchanged. Security impact low: scientific data and curated public docs; no new
auth boundary or service. Independent correctness and publication/security review
must confirm source containment, no secrets, vendor equality, and ordinary
Usersum access. Proposed regression covers fresh artifacts, prepared parameters,
source hashes, partial-report rejection, Usersum registration/rendering, and
isolated full-project execution. Implementation awaits this committed checkpoint.
