# SSURGO JSON integration and source provenance

Operator authorization: "proceed with wepppy json integration. the wepppy integration
should also implement provenance tracking so we know what server is being queried
for soils data" (2026-11-18 UTC).

Target: faithful transport migration behind explicit selection, with persisted
source identity and unchanged scientific outputs. Complexity budget: existing
requests/SQLite/NoDb, one small transport/provenance collaborator, additive metadata
and base-soil sidecars. No new service/dependency, UI, environment-global switch,
parameterization change, deployment or upstream spatial replacement.

Canonical authority: docs/schemas/soil-data-source-provenance-contract.md,
docs/schemas/nodb-persistence-concurrency-contract.md, and
 docs/schemas/soil-horizon-boundary-contract.md. Preserve all current scientific
contracts. Scope includes SurgoSoilCollection, six Soils call sites, stubs and tests.
Security delta: operator-selected endpoints and persistent cache binding require
explicit URL/redirect validation and source separation; review artifact required.

Generated artifacts: compare fresh-cache base soils, paired treated/model inputs,
cache rows/identity/events and base .sol.provenance.json using the real HTTP/database
path. Implemented versus wired status is recorded separately in tracker.md.
Full project fallback/treatment coverage and public service deployment remain outside
this bounded integration's completion claim and tracked in soil-data-access.
