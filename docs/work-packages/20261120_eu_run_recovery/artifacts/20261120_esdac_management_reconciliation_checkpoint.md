# European ESDAC management reconciliation checkpoint

Starting implementation revision is `c2854ffd4`. The operator directed
forest for class 22, row-by-row reconciliation for the nine base differences,
three severity-specific grass wildfire templates, and consistency with the
default Disturbed catalog for prescribed grass fire.

[ADR-0153](../../../adrs/ADR-0153-european-esdac-management-reconciliation.md)
gives the exact row disposition and rationale. The
[European mapping contract](../../../schemas/european-landuse-mapping-contract.md#reconciled-esdac-and-european-fire-scenarios)
defines named resolution and backwards compatibility. Existing plain ESDAC
and CORINE provider identifiers and run-owned custom map precedence apply.
The exact Disturbed ESDAC name previously matched the plain ESDAC substring
branch. A newly selected or rebuilt run can deliberately use the full named
ESDAC table. No run schema migration or new raster source is required.

Validate all three catalogs, unique wildfire destinations, native scenario
parse and serialization, unchanged plain mappings, explicit map files and
custom precedence, approved admission and representative soil and model
input generation. Confirm that key 132 resolves to the existing Disturbed
grass prescribed fire soil class and its matching management reference.
The upload uses the existing allowlist and authorization. Add the exact
named option to Landuse Options and omit it from the Treatments selector.
The catalog lacks treatment markers. Path-like upload selections still
fail existing admission checks. Confirm unsupported filenames
remain subject to the same rejection behavior.

## Independent reviews

Both reviews identified the shared Treatments selector and required it to
exclude the new land-cover option. Tests cover both selector surfaces,
exact name resolution, prior suffixed ESDAC aliases and explicit paths.
The science review verified the proposed bases and pointed out that the
bundled grass soil coefficients match across grass fire cases. The ADR
now distinguishes soil lookup identity from the management scenario
change. Update the high and moderate ESDAC grass descriptions with their
classes and templates.

Existing forest replay artifacts remain evidence for the earlier
incident workflow.

A replay of the new upload with the Es Fangar settings exposed a stale
CORINE buffer selection (42). The single-OFE page hides the buffer
control, and ESDAC does not define that code. When changing maps on a
single-OFE upload, validate explicit buffer selections and retain
compatible inherited selections. Clear an incompatible inherited selection
only on successful publication. Preserve active multi-OFE validation and
the last applied selection on admission failure.
