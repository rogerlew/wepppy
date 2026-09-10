# Contract checkpoint

Starting revision: 595816476. Intended behavior change; implementation pending.
Operator authorization: “all projects created with the config builder should
have sbs map support”; follow-up to executing the production M1 workflow.
The owner clarified “config builder projects should always have disturbed” and
then said “continue” after the response specifying normal soil adjustments and
no SBS-only guard. This authorizes the required checkpoint and implementation,
not pushing. ADR-0064 records the workflow default change.

Normative delta: canonical project-owned-config-contract.md, Builder Soil Burn
Severity support (2026-09-10). Internal Disturbed dependency for new Builder
projects, preserved user selections in manifest, narrow historical validation
compatibility, explicit fair-division runtime enable using NoDb persistence.
Existing Disturbed numerical parameters/routines, upload/controller, CSRF, RQ response, access and
NoDb lock/cache contracts are unchanged. No closed package is amended.

Compatibility/regression plan: config schema and manifest keys unchanged. New
configs include the required runtime module; older config bytes are preserved.
Existing module state is reused; new empty state can be initialized. Test
empty/default, populated, historical-empty and malformed module selections,
all exposed locales and backends, config-update provenance checks and actual
controller creation/rehydration. Confirm UI upload/classification/removal on a
disposable builder project through the existing authenticated route. No existing
WEPP inputs are rebuilt; new SBS is consumed on subsequent user-requested builds.

Security: low delta, no additional endpoint. Missing optional state is valid.
Malformed config/controller state fails explicitly; no blanket catches or
shared-config fallback. Existing map/state is never reset during repair.
No full suite; operator stopped it. Two independent read-only reviews pending.

Review finding: adding Disturbed with a plain landuse mapping raises KeyError
for missing DisturbedClass even without SBS. Select existing matching Disturbed
mappings in landuse provider writes/provenance: NLCD/EMAPR disturbed, CORINE
eu-disturbed, Australia au-disturbed, C3S c3s-disturbed. Explicitly repair
fair-division persisted default Landuse mapping to disturbed. Preserve custom
populated mappings and config bytes. No lookup contents or numerical code change.
Test every exposed source for the nine required burn classes and source-class
coverage; test historical explicit update behavior and initialization/lookup.

Both independent reviewers approve the amended checkpoint. The high mapping
finding is resolved by the canonical mapping table and ADR-0064. No unresolved
medium/high contract findings. Runtime conformance and repair evidence remain
pending; no runtime files were edited before this checkpoint.
