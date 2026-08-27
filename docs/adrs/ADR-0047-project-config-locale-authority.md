# ADR: Project Config Locale and View Authority

Status: Accepted
Date: 2026-08-27

## Decision Provenance

- **Decision Venue**: active Codex development session, 2026-08-27 06:12 UTC.
- **Participants Present**: project operator and Codex.
- **Decision Owner**: project operator.
- **Implementer**: Codex.

## Context

WEPPcloud currently spreads locale-dependent availability across Builder TOML,
climate and landuse Python catalogs, templates, and route handlers. The first
Builder family covers only continental United States, while runtime catalogs
know about additional regions and methods. Fixed template radio lists can show
methods that a selected dataset or locale does not support.

## Change Summary

Previously, Builder had one partial locale family and flattened capabilities
used coarse dataset lists. After WP12B, every shipped runtime locale token is
classified by a canonical typed profile, supported Builder profiles resolve a
complete dependency closure, and generated configs store separate stable
dataset and method capability axes. Runtime views and paired mutation endpoints
consume the stored per-project authority.

## Decision

Retain `continental-us` as a durable profile ID and normalize it to the same
schema as every locale profile. Map profiles to existing runtime locale tokens;
do not rename stable IDs to tokens. Use the current registry for Builder views
and the flattened config for created-run views. Do not migrate existing runs.

Only explicitly supported and Forest-validated profiles are Builder-selectable.
Inventory-only or specialized profiles remain explicit but unavailable rather
than being silently treated as continental United States.

## Rationale

One typed graph makes dependencies reviewable and prevents presentation from
drifting away from server acceptance. Per-project capability snapshots preserve
reproducibility. Separating datasets from methods lets climate station/spatial
radios and landuse/soil workflows accurately follow their selected inputs.

## Alternatives Considered

Keeping template conditionals was rejected because hidden controls and server
acceptance can diverge. Reading the live registry from run pages was rejected
because registry revisions would retroactively change existing projects.
Treating every shipped config token as a supported Builder locale was rejected
because presets demonstrate deployed behavior but not a validated cross-product.

## Evidence

- WP12B active ExecPlan and locale inventory.
- Generated profile/component/capability matrix.
- Paired template and mutation-route regression tests.
- Presence/health evidence for every advertised provider and every
  Builder-exposed base/overlay, plus representative real execution for each
  distinct provider/method family.

## Risk and Rollback Notes

Incorrect locale dependencies can expose unavailable datasets or hide valid
workflows. Atomic registry validation, fail-closed required axes, paired server
enforcement, Preview maturity, and Forest provider evidence mitigate that risk.
Before the first schema-v2 project exists, rollback may restore prior catalog
filtering and the one-locale Builder. After the first v2 project exists, every
supported rollback revision must retain or redeploy a v2-aware, fail-closed
reader and enforcement path; v2 writers and new views may be disabled, but a
pre-v2 reader is no longer a supported target. Existing flattened projects
remain self-contained and unchanged.

## Consequences

Adding a locale or dataset now requires a stable profile/component definition,
dependency validation, generated capability evidence, and deployed-provider
acceptance. This is more deliberate than editing a template, but it gives views,
APIs, manifests, and Builder review one consistent authority.
