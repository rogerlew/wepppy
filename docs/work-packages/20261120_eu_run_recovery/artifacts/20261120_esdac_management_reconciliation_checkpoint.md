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

## Verified candidate

The [final inventory](20261120_eu_management_reconciled_inventory.csv)
records the disposition of all 146 rows. Each management summary resolved,
serialized to a native WEPP file, and could be read back. Each Disturbed
catalog has one destination per forest, shrub and grass wildfire severity.

Forest restarted the Web, RQ engine and three RQ worker services with
`00c81ee0a` after checking that all queues were idle. The full earlier
development deployment and original replay are recorded in the
[deployment receipt](20261120_forest_deployment_replay.md).

A signed-in browser selected the named ESDAC map and uploaded a synthetic
20-code raster on the original 58-hillslope geometry. The separate
[forest verification run](https://forest.tail305ec9.ts.net/weppcloud/runs/unsinkable-succinylcholine/eu-disturbed/)
started from the earlier E-OBS and gridded-soil replay. The single-OFE
buffer control was hidden. The browser showed applied class 132, and the
published state cleared the incompatible inherited CORINE code. Actual
land-use Parquet agreed with the catalog for all hillslopes.

The soil rebuild accepted 58 profiles, including 37 using the approved
project subsoil defaults. Readback verified forest at key 22 and the
expected canopy, interrill and rill cover in the prepared WEPP files for all
13 hillslopes assigned keys 22 and 129–132. Key 132 selected its distinct prescribed grass soil lookup.
The prepared soils were format 7778. The WEPP parent and 17 descendants
finished. Native output includes 58 hillslope pass files and a 619,126-byte
watershed loss file. Watershed event Parquet has 10,957 rows, and hillslope
pass Parquet has 635,506 rows. [Job IDs, artifact hashes and model input readback](20261120_esdac_reconciled_forest_artifacts.json)

The synthetic fixture verifies the chosen ESDAC classes under the real
workflow. The previous original-workflow CORINE runs provide the historical
input replay. The original second-incident upload remains unavailable.

## Quality gates

The focused Python gate passed 532 tests. Frontend lint and all nine
frontend tests passed. Stub completeness passed. Stubtest reported the
same 143 diagnostics against the parent and candidate snapshots.

The 99-test Disturbed matrix gate passed. Retained native outputs and the
regenerated report matched the published benchmark exactly. The generated
soil inputs differ only in the Build Date comment. [Matrix parity receipt](20261120_esdac_reconciliation_matrix_parity.json)
