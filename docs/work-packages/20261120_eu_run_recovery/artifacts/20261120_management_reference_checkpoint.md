# Historical thinning reference checkpoint

Starting implementation `fd42a025d`. The operator asked for a complete
ESDAC management and mapping reconciliation. The archival baseline
identified four missing files in the Disturbed ESDAC table. Repository
history proves they were renamed with byte identity. Current references
in three peer regional tables share each same missing file under
`UnDisturbed/`. Correct all four tables through the same mechanical path
replacement. The [mapping contract](../../../schemas/european-landuse-mapping-contract.md#management-reference-compatibility)
records the exact keys and paths. The literal correction changes no model
parameter, class or existing resolver routing and does not require a
parameterization ADR. Similar names in the Tahoe directory refer to a
different asset family.

Check the four old Git blobs against current files. Parse every corrected
reference through the actual management loader and round trip the native
scenarios under the historic file format used by each. Preserve all other
rows and files. Separate scenario and classification changes, including
the known grass and moderate fire mismatches, require their own parameters
and generated-artifact test matrix.

## Independent review

Both reviewers confirmed the four byte-identical Git renames and all 16
live references in the four tables. Both cleared the bounded reference
repair. Use the ESDAC table by explicit file path for validation and preserve
all Tahoe assets. Previously serialized summaries and run-owned copied tables
retain their references. Land-use rebuild can regenerate summaries from
a repaired catalog, while run-owned copied tables require their normal
editing workflow.
