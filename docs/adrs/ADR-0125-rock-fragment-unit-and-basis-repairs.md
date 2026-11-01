# ADR-0125: Rock fragment unit and basis repairs

Status: accepted for independently reviewed development; dimensional repairs implemented and locally validated, not deployed.
Date: 2026-10-31 Pacific / 2026-11-01 UTC.

## Context and decision

The retained Roads audit reproduces a RUSLE C defect where SoilGrids per-mille values at or below100 are interpreted as volume percent. K already uses /10. General investigation also locates direct assignment of normalized volume percent to ISRICHorizon.rfg, whose serializer emits the native mass field. Repair these dimensional substitutions under the [rock representation contract](../schemas/rock-fragment-representation-contract.md).

Use fixed /10 for recognized raw/aligned SoilGrids inputs in C, preserving proxy policy and explicit overrides. Convert SoilGrids volume fraction v to mass fraction using w=v*rho_r/(v*rho_r+(1-v)*rho_f), with source fine-earth bulk density and the existing native mineral convention rho_r=2.65g/cm3. Preserve the native cap, all other soil sources, formats, defaults and 200mm boundary. Reject invalid conversion inputs rather than inventing density.

## Decision provenance

Venue: operator/Codex development thread, 2026-10-31 Pacific. Participants: operator and Codex. Decision owner: operator authorizes in-depth volumetric/surface rock investigation and development for Roads/WEPP generally; Codex selects these evidence-supported dimensional corrections. Implementer: Codex. Independent reviews required before implementation; no claim of approval for new native physics or production deployment.

## Rationale and alternatives

Data magnitude cannot identify units. Profile volume cannot be relabeled mass. Reuse the owned stack and native density convention rather than add dependencies or fit rock values to sediment. Reject global POR multiplication, direct cfvo-to-surface adoption, biomass-as-rock and rangeland switching: those change distinct mechanisms without sufficient evidence.

## Compatibility and risks

New rebuilds can change RUSLE C and SoilGrids-generated soil hydrology/erosion. Prior cached artifacts remain intact; no automatic regeneration or deployment. Corrected units do not validate the existing surface proxy, mineral-density assumption or native rock cap. Very rocky/porous materials need separate evidence. SSURGO retention heuristics remain under investigation, not revised.

## Evidence and rollback

Prior [rock audit](../work-packages/20261029_roads_parameterization_program/artifacts/rock-cover-audit-r4/findings.md); active [development plan](../work-packages/20261031_rock_representation/prompts/active/rock_representation_execplan.md). Real raster/manifest and generated soil/native interpretation regressions precede acceptance. Revert the bounded implementation commit if those contracts fail; preserve original evidence. No native binary is changed.
