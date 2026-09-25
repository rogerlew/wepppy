# Omni thinning canopy choices

Status: amendment accepted and 60%/70% generated-input conformance locally
validated 2026-09-25 (implementation `2d0891398`). Live browser acceptance and
deployment remain separate. Full-suite status is recorded in the work package.

## Choice and parameter contract

Omni thinning offers target canopy cover 30%, 40%, 50%, 60%, 65%, 70% in ascending order.
New rows default to 40%; ground choices remain 93% (Cable), 90% (Forward),
85% (Skidder), 75%, with 93% default. Saved choices hydrate unchanged. Canopy
means remaining target cover, not percentage removed.

30%, 50%, 60% and 70% each resolve all four ground covers in disturbed, c3s-disturbed,
au-disturbed, eu-corine-disturbed and revegetation catalogs. Each file copies the
corresponding legacy 40% ground-cover file and changes only cancov to its target fraction
(0.30, 0.50, 0.60 or 0.70). Ground fractions, LAI, other plant/management parameters, treatment
eligibility, soil lookup and RAP/explicit override precedence remain unchanged.
Existing numeric IDs, classes, files and regional availability remain unchanged.
65% remains a visible choice with its existing regional availability: removing
its supported variants would break existing projects and saved direct-path
references. No deprecation, migration or expansion of regional 65% availability
is introduced.

## Compatibility, states and errors

Preserve percent-string payloads, scenario names and saved NoDb state. Never-used
or empty scenario lists can add a thinning row with the defaults above. Populated
and legacy scenarios retain their selected values. Missing parameters and malformed
requests retain existing explicit error behavior; no new validation/fallback path.
Working, failed and completed scenario status/lifecycle is unchanged.

The existing MOFE rules remain authoritative in
[management artifacts](../../schemas/mofe-management-artifact-contract.md).
The [controller contract](../controller-contract.md) and
[NoDb persistence contract](../../schemas/nodb-persistence-concurrency-contract.md)
apply unchanged. No routes, uploads, authentication, queues or API schemas change.

## Artifact acceptance and rationale

Use existing landuse management and `wepp/runs/*.man` paths and ordinary project
browse/download/archive behavior. No new output category, hidden storage,
retention rule or archive exclusion. Check actual canopy and both ground fractions
in parsed source, serialized single-OFE, combined MOFE and prepared WEPP inputs;
confirm all legacy files and map records remain unchanged. UI evidence covers
new/default and hydrated selections. Local generated-input validation does not
claim fresh model results or deployment; those remain separate operator actions.

Eight additive assets per two new canopy choices are preferred to a template refactor for this bounded
request. Retaining legacy files protects saved direct-path references. See
[ADR-0071](../../adrs/ADR-0071-omni-thinning-30-50.md) for the original provenance and [ADR-0074](../../adrs/ADR-0074-omni-thinning-60-70.md)
for the 60%/70% addition and retained 65% decision.

## Archive and inspection evidence

Archived/restored runs are supported states: preserve new/legacy selections and
management bytes at existing landuse and prepared-input paths. Exercise the
canonical project archive/restore implementation with these files and compare
restored bytes. Run existing browse/download coverage. Live browser/download
acceptance remains explicitly unverified unless exercised; operator owns that
pre-deployment gate. Local code-delivery closure must state this limitation.
