# Independent correctness and user-experience review

Reviewer: `/root/rock_contract_impl`, 2026-11-01 UTC. Contract ancestor: `b2011d9fb`. Canonical intent: `docs/schemas/rock-fragment-representation-contract.md`, ADR-0125 and unchanged RUSLE SoilGrids /10 meaning. Security impact:none; no new attack surface.

Disposition: **PASS for the two bounded unit/basis implementations and local generated-artifact validation**. No medium/high code finding. Broad-suite execution is still pending at this review; this receipt does not assert a green full suite or authorize omitting its disposition.

## User outcome and changed surfaces

On rebuild, supported SoilGrids cfvo inputs retain fixed per-mille scaling in RUSLE C, and SoilGrids-generated native soils encode coarse-fragment dry mass rather than volume. Existing products, explicit cover choices, other soil sources, native cap, field normalization and UI remain unchanged. No native equation or binary changed. User-facing rebuild/proxy warnings are documented in RUSLE and WEPP soils README sections.

## Failure-class coverage

C RAP and SBS share the corrected loader, and both supported source paths are covered. K's recognized SoilGrids path already uses the correct scale and existing K tests pass. ISRIC extraction, horizon construction, serializer and actual native initialization are traced. SSURGO mass RFG is unchanged. Its retention heuristic and BC SIFT COFRAG basis remain explicitly unresolved in the investigation rather than silently certified. No class-wide rock-physics claim is made.

## Valid-state and error evidence

| State | Intended result | Evidence |
| --- | --- | --- |
| No optional C rock source | existing computational zero fallback | existing C tests |
| All-nodata cfvo | existing fallback with source metadata | real raster regression in both modes/paths |
| Populated supported raw/aligned cfvo | fixed /10, actual C raster/manifest | 20 parameterized cases;16 retained populated cases |
| Explicit user fraction | bypass auto-source behavior | existing C user partition tests retained |
| Old cached soil/output | unchanged until explicit rebuild | no migration/automatic rewrite path added |
| Valid ISRIC density/volume | mass conversion and native soil serialization | conservation/endpoints plus actual raster-to-builder test |
| Nonfinite/out-of-domain mandatory volume or nonpositive density | explicit ValueError before serialization | converter/ISRICHorizon regressions; builder publishes only after constructing horizons |
| Malformed optional raster | existing unavailable/error behavior | unchanged existing exception boundary; no broader malformed-input claim |

Input matrix and state matrix are finite, not exhaustive across all geospatial/provenance configurations. A filename carrying misrepresented custom units is outside the recognized SoilGrids source contract. Source priority, cover proxy interpretation and clipping are unchanged.

## Generated-artifact chain and independent readback

1. Stored SoilGrids synthetic rasters carry cfvo200 and bdod130; actual extraction yields20volume% and1.3g/cm3.
2. Actual builder emits seven7778 horizons with the200mm split and RFG33.8mass%. Builder log records volume and density assumptions.
3. Sixteen retained C cases span both modes, both paths and stored20/100/101/800. Independent receipt verification checked239 file hashes and expected proxy/C values.
4. Fresh declared native fixture repeats the generated complete OFE block three times. Before-execution receipt establishes only p1.sol changed and no historical outputs copied. The pinned observer/build provenance is retained.
5. Actual native execution completes its configured16years; stdout reaches year16. Independent readback verifies30 initialization layers, all three OFEs, unique trace keys, every input/output hash and CPM reconstructed from actual native density. Consumed mass0.3379999995 produces volume0.2003008723, consistent with one-decimal emitted RFG and native arithmetic.
6. Seven native outputs are nonempty; independent scan finds no NaN/Inf or numeric-adjacent overflow markers. This is not full physical water/particle closure or field validation.

The reviewer independently read artifact receipts, soil/trace values and output hashes. Real raster/output generation is executed through current code, not mocked at the failed boundary. Inputs are finite local fixtures, not a production watershed; no deployment or old-project recovery is claimed.

## Validation status

Focused final run:102passed,2warnings. Earlier failing-before implementation evidence and intermediate correction attempts remain retained. Test-stub gate passes. Broad suite is still running and must receive explicit final disposition before handoff. Highest supported claim: implemented and locally validated with real generated artifacts and executed native interpretation.

## Reviewed implementation identities

- `wepppy/nodb/mods/rusle/c_integration.py`: `7f728d89002cc691ef540d02b45281fa4ba7779a980c965eabc405cbcc0a64c2`
- `wepppy/locales/earth/soils/isric/__init__.py`: `e935529372fb3a925680785982d0130782e4b829e32d91af1c3052271b3e9f7f`
- `wepppy/wepp/soils/rock_fragments.py`: `2aedbecbf6cbd1c4b2e91558b859a4c5957f17b972b7861d2866710a910973ca`
- `tests/nodb/mods/test_rusle_c_integration.py`: `80ad60cbca4d507ec39db6129ca4387970bf099a24d754e72edf62f286dd7409`
- `tests/locales/earth/soils/test_isric_rock_basis.py`: `219ef22f5e7bd3975d372874be3bd58fb8027a09ae77b6eb5f8b8da0789aa971`
- `tests/wepp/soils/test_rock_fragments.py`: `66a6d852918b5ba8ba2aaecab5499b3ec8dbea531a348776b8bc30426b1e1691`
