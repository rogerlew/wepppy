# ADR-0126: Convert BC SIFT fragment volume to native mass

Status: proposed for independently reviewed implementation checkpoint; not deployed.
Date: 2026-11-01 Pacific.

## Context and decision

The published BC BCSLF dictionary identifies COFRAG as volume percent and BD as fine-earth bulk density (g/cm3 corroborated by CanSIS). The actual SiftHorizon serializer emits COFRAG directly into native mass RFG. Prior source-bound evidence establishes the mismatch;20volume% at1.3g/cm3 is33.75796mass%, not20mass%.

Use existing rock_volume_to_mass_fraction(COFRAG/100, BD)*100 with the existing2.65g/cm3 mineral convention. Translate either None or-9 in fraction/density into an unavailable rfg (None), retaining incomplete-horizon filtering. Do not invent density even for a zero-fragment row. Present invalid/nonfinite fractions or nonpositive/nonfinite densities fail explicitly through the shared helper. No new catch/fallback.

## Decision provenance

Venue: operator/Codex development thread, 2026-11-01 America/Los_Angeles. Participants: operator and Codex. Decision owner: operator explicitly authorized the recommended SIFT repair and separate frozen-water investigation. Implementer: Codex. Independent scientific and implementation reviews precede production edits.

## Rationale and alternatives

Preserve source meaning through the mass-based native boundary. Reuse the already reviewed converter rather than duplicate arithmetic. Reject direct volume relabeling, missing-density substitution, global changes to other soil sources and native cap changes. Keep retention, surface cover and frozen-water physics separate because their assumptions and acceptance differ.

## Compatibility, risks and rollback

No format/key/schema migration. Raw JSON and source-summary COFRAG/BD stay unchanged; add a concise comment identifying source-volume and emitted-mass meanings and mineral density. Keep open-water behavior,200mm boundary, native caps and formatting. Existing soils stay historical until explicit rebuild; rebuilt BC results may change. Deployed local database contents are not certified by published metadata or synthetic fixtures. Native bounds and density evolution limit exact volume round trips.

Validate deterministic valid/missing/invalid states, actual SIFT construction and serialization, then full-period native consumer readback with zero/high-rock cases. Invalid present source values must not publish a plausible soil. Retain attempted raw JSON and diagnostics. Revert the repair commit if propagation or compatibility gates fail; do not rewrite previous outputs.

## Evidence and implementation limits

[Source study](../work-packages/20261101_rock_sources_water_accounting/artifacts/findings.md#bc-sift-the-source-definition-is-now-established), [canonical contract](../schemas/rock-fragment-representation-contract.md), and [current package](../work-packages/20261101_sift_rock_frozen_water/package.md). Generated/native validation is pending. The separate FRWATC campaign changes no model formula and confers no capacity-correction approval.

Compatibility clarification: missing None/-9 in either input takes precedence over an invalid value in the other input. Preserve the established canned open-water path by checking soil.is_water before mineral soil.valid; open water does not require mineral conversion. Include real writer regressions for water rows with invalid and missing mineral values.

Confirmed builder-boundary amendment: the supported container lacks prettytable and requirements-uv does not declare it; the actual writer fails before emitting a mineral soil. Render the same raw source columns/values as a commented fixed-width table with standard-library string formatting, eliminating this undeclared dependency without a fallback or new dependency. Exact comment whitespace may change; native data formatting is preserved. The existing mineral OFE header has seven tokens, missing mandatory SAT. Emit SAT0.75 between SALB and KI, matching the existing generated-soil initial-saturation convention (ISRIC default and SIFT canned-water header). This is an explicit missing-field repair, not sediment fitting. Retain isolated parser-failure evidence, require canonical soil-parser plus actual native acceptance, and keep other coefficients unchanged.
