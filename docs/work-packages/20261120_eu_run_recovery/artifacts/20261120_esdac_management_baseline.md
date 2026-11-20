# ESDAC management audit baseline

This read-only inventory used the package starting revision `c2e6f4d1a`. It records catalog contents and reference existence. Scientific suitability and runtime validation remain open.

| Catalog in `wepppy/wepp/management/data/` | Rows | Rows with a `DisturbedClass` field | Missing local management file references |
| --- | ---: | ---: | ---: |
| `esdac_map.json` | 23 | 0 | 0 |
| `eu-esdac-disturbed.json` | 43 | 43 | 4 |
| `eu-corine-disturbed.json` | 80 | 80 | 0 |

The plain and Disturbed ESDAC tables share base keys 0–22 and list the same base descriptions. They assign different management files for keys 1, 2, 3, 4, 5, 9, 13, 19 and 20. The Disturbed ESDAC table includes a blank disturbance class for key 0 and 20 additional disturbance and treatment entries.

The four absent references in the Disturbed ESDAC table are keys 115, 116, 117 and 124. They point to `Cable_Thinning_93_Cover.man`, `Forward_Thinning_90_Cover.man`, `Skidder_Thinning_85_Cover.man` and `Thinning_75_Cover.man` under `UnDisturbed/`. The audit must establish the intended templates and coverage mechanics before changing them.

`load_map('esdac')` loads the plain map. The named resolver uses a broad `esdac` match and resolves the name `eu-esdac-disturbed` to the same plain map. The separate JSON can be loaded by an explicit file path. The audit must trace any additional consumers before assigning catalog ownership or changing aliases.

Class identifiers are source-specific. CORINE class 25 is Mixed forest and has no ESDAC counterpart under the same number. The scope includes an explicit crosswalk only where source legends and approved management rationale support it. No code, assignments or templates were changed for this inventory.

The [row inventory](20261120_eu_management_inventory.csv) records all 146 catalog rows and native parser results. All 142 present references parsed. The bundled ESDAC ESDB `USE-DOM` legend confirms base keys 0–22 and their source meanings. It provides no model-management assignments. Key 22 is particularly important to reconcile across consumers. Its source definition mentions wildlife refuge and land above timberline. The Disturbed ESDAC catalog labels it bare while both management catalogs point to a forest template, and the ESDAC soil builder also treats it as forest for albedo and saturation. Any change needs an explicit scientific decision and a downstream readback.

## Traceable treatment and fire mapping candidates

Git commit `fc183b0a6` renamed the four missing thinning files. Comparing the blobs immediately before the rename with the current templates proves byte identity for all four replacements. This establishes a reference-only repair for keys 115, 116, 117 and 124, mapped respectively to `Thinning_40_93.man`, `Thinning_40_90.man`, `Thinning_40_85.man` and `Thinning_40_75.man`. The corresponding treatment-class labels still need review because they control the soil lookup as well as the presentation.

Disturbed requires distinct low, moderate and high entries for forest, shrub and grass. The separate ESDAC table lacks forest moderate, shrub moderate, grass moderate and grass high destinations. Keys 118 and 120 already name and reference moderate templates but are labeled low. Keys 129–131 all point to the same shrub template and use the same grass-low label. The shared extended land/soil lookup identifies all three grass severity templates and distinct soil rows. The European CORINE map separates the grass severity labels but still shares a shrub template. Reconciliation therefore has a confirmed peer consumer and a scientific choice for the appropriate grass templates.

The extended land/soil lookup gives explicit class-to-scenario reference candidates for both catalogs. For any changed pair, validate the prepared management and soil files independently. The four texture rows use equal soil parameters across the three grass wildfire severities in that lookup. The severity-specific management files still differ. Grass prescribed fire requires a separate disposition because both European maps use `Prescribed_Fire.man` for key 132, while the extended lookup specifies `Grass_Low_Severity_Fire.man`. Both assignments have the same `grass prescribed fire` class.

| Key | Class in the extended lookup | Management in the extended lookup |
| --- | --- | --- |
| 118 | forest moderate sev fire | `UnDisturbed/Moderate_Severity_Fire.man` |
| 120 | shrub moderate sev fire | `UnDisturbed/Shrub_Moderate_Severity_Fire.man` |
| 129 | grass high sev fire | `UnDisturbed/Grass_High_Severity_Fire.man` |
| 130 | grass moderate sev fire | `UnDisturbed/Grass_Moderate_Severity_Fire.man` |
| 131 | grass low sev fire | `UnDisturbed/Grass_Low_Severity_Fire.man` |
| 132 | grass prescribed fire | `UnDisturbed/Grass_Low_Severity_Fire.man` |

Keys 108, 115–117, 123, and 124 have no identical numeric key in the extended lookup. CORINE supplies matching reference and class pairs for the four renamed thinning templates. Verify their effective soil parameters under `thinning_40_93`, `thinning_40_90`, `thinning_40_85`, and `thinning_40_75` against the old catalog class `thinning` before any class reassignment. The byte-identical files support a reference-only repair.

The European Commission [ESDB attribute legend](https://esdac.jrc.ec.europa.eu/content/sgdbe-attributes) supplies the source classes. It does not supply WEPP management scenarios. The Commission [derived data notes](https://esdac.jrc.ec.europa.eu/content/european-soil-database-derived-data) also describe scope limits for subsoil organic carbon and bulk density. The [SPADE-2 profile collection](https://esdac.jrc.ec.europa.eu/content/soil-profile-analytical-database-2) is a candidate for evaluating source-backed profiles if the soil decision authorizes that path. Verify linkage, depth, fields, and applicability before using it.

## Reconciliation review queue

- **Plain ESDAC base keys 0–22.** Preserve the current source assignments for existing plain-map consumers while tracing project and upload provenance. Disturbed consumes complete fire destination classes, so plain ESDAC cannot satisfy Disturbed admission.
- **Separate Disturbed ESDAC base keys 0–22.** Fourteen reference the same template as plain ESDAC. The nine differing templates need an explicit use-case rationale before exposing this catalog by name. Class 22 also requires agreement among the modeled cover, template and ESDAC soil forest switch. Keep the official base class descriptions and distinguish model assumptions in the UI and provenance. Review whether the blank class for no-information key 0 is deliberate for the selected workflow.
- **Fire keys 105, 106, 110, 118–122 and 129–132.** Establish one destination per forest, shrub and grass severity, plus the existing prescribed-fire variants. Keys 118 and 120 have a mismatch between the intended moderate labels/templates and low-severity lookup classes. Resolve keys 129–131 against the shared severity-specific managements and soil lookup before publishing the ESDAC catalog or changing the CORINE peer rows.
- **Treatment keys 108, 109, 111, 115–117, 123 and 124.** Confirm the intended mulch, tilled mulch, skid and thinning behavior in the effective lookup and serialized model deck. Four thinning filenames have exact historical replacements. Do not infer the corresponding lookup class from file existence alone.
- **Consumer binding.** Keep existing plain ESDAC and CORINE workflows tied to their own source code namespaces. Compare named catalog routing, user upload selection, custom-map path resolution, archive/fork compatibility, disturbed soil lookup and WEPP input preparation. Specify how an existing run with an alias resolves after the change, before using an exact-name resolver to expose the separate Disturbed catalog.

## Post-reference audit

The four legacy filenames have been corrected in the Disturbed ESDAC catalog
and three peer catalogs. Native readback passed all 16 references. The
enclosing `ManagementSummary` hydration independently rejects the generic
class `thinning` for ESDAC keys 115–117, 123 and 124. The two base reference
catalogs passed hydration for all 23 ESDAC and 80 CORINE rows. Generic
thinning class values require a parameterization decision and effective
management and soil readback. Key 123 has a distinct 96% template.
