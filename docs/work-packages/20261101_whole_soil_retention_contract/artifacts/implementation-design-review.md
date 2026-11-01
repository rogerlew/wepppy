# Whole-soil retention audit implementation design review

Disposition: **PASS for the bounded audit design with the requirements below.** No production implementation, container execution or native model run was performed by this reviewer. Concrete helper/declaration and actual results require subsequent review. Unrelated dirty ssurgo.md remains untouched.

## Actual adapter behavior

Horizon always invokes real Rosetta2 or Rosetta3 before selecting retention values, even when both source retention values are present. Finite source bulk density selects Rosetta3; absent/nonfinite density selects Rosetta2, and density estimation occurs later without re-running Rosetta3. Therefore valid-source controls also require the real installed Rosetta dependency and model assets. Do not replace predictions, Horizon methods or dependencies with mocks.

Retention branches are independent initially: field capacity and wilting point can each use source data or Rosetta. If the resulting pair fails finite/ordered/unit-interval validation, both values are replaced by validated Rosetta values. Build notes preserve attempted branches as well as a later sanitation note; the last outcome cannot be inferred from the first note alone. Retain raw source, typed operands, initial branch choices, final pair, all notes and any constructor failure separately. Missing density, retention or rock is not measured zero.

Rock preparation uses the mass-derived fragment/sieve expression. Organic or missing-designation horizons and unavailable sieve values use the supplied rock default; absent large-fragment operands are treated as zero by existing code. Keep these default decisions visible. A finite source retention combined with unavailable rock follows Rosetta. Horizon.valid does not establish every serializer operand's validity: a horizon may survive its mask while unavailable SMR later prevents numeric formatting. Preserve such failure rather than injecting rock zero. Also distinguish finite-but-nonpositive density from unavailable density; the hypothetical physical conversion must independently require a valid positive density.

## Source and row integrity

Acquire only the four admitted mapunits 1718465, 1718494, 1856573 and 2711184. Retain exact query, request parameters, endpoint, timestamps, response status/body hash and original row identities/nulls before adaptation. Establish explicit numeric conversion consistent with the actual ingestion path: raw API strings must not be silently passed into arithmetic expecting numeric fragment fields. Keep raw and typed copies separate. Actual _get_horizons enriches its working row dictionaries; those mutations must not alter retained source payloads.

Require complete identity joins across mukey/cokey/chkey/depth, explicit duplicate rejection and a ledger of all admitted, excluded, constructor-failed and fallback rows. Full WeppSoil build selects the first component with valid horizons, masks horizons and applies restrictive-layer cutoff; record those selection outcomes rather than representing the emitted component as every source row. Retain official source-definition acquisition separately from observed local records; metadata alone does not validate each row's physical truth.

## Correct serializer boundary

Use the supported container through `wctl exec -T weppcloud /opt/venv/bin/python -B`. Retain actual imported module paths and hashes, Python and numerical-package versions, Rosetta package/model-asset identities, image/container identity and exact command. Confirm container-loaded production code equals the reviewed checkout; a host source hash alone does not prove which module executed. Preserve ordinary failures if the supported dependency/environment is unavailable.

Use actual WeppSoil 7778 serialization for retention: build_file_contents_v2006_2 does not emit FC/WP. Prefer a real collection and constructor for a complete selected profile. If unrelated material/header selection cannot be supported for a row-level diagnostic, explicitly label complete synthetic serializer context and invoke the actual production serializer; do not claim that context is an actual selected mapunit or complete native execution. Never duplicate the formatting routine, monkeypatch validation or invent missing real-source fields to force output.

The 7778 serializer revalidates FC/WP, formats retention to four decimals, bulk density and rock to two decimals, changes terminal depth, and calls ensure_200mm_boundary. That boundary can insert an identical-material layer and increase the declared count; it can also reject excess layers. Map emitted records by source ownership/depth rather than row ordinal alone. Capture prepared objects before/after serialization, actual file bytes, parsed header count and each emitted token. The public write path produces CRLF and returns a summary; read actual emitted bytes rather than treating a successful return as proof of content.

## Separate numerical projections

Keep the existing capped-mass inverse, hypothetical volume inverse and CPM-only native projection in separately named outputs. Use the actual prepared/emitted retention, density and RFG at their respective stages; retain source density, estimated density, two-decimal emitted density and any separately assumed native density distinctly. Source 50-percent and native 85-percent caps are different branches. Do not apply a hypothetical physical inverse as if it were a production-prepared value, or infer full native output from a CPM-only projection that excludes later guards/air/dry-reference operations.

Prespecify controls for zero rock, cap boundaries, high rock, source/mixed/Rosetta-pair fallback, missing inputs, finite-invalid density, duplicate ownership, formatting roundoff and 200 mm splitting. A four-decimal retention token can differ by approximately half a unit in its final place before native REAL parsing; evaluate actual emitted tokens and binary32 conversion separately. Missing or unsupported cases remain explicit unavailable/excluded outcomes. Ratios and dimensional comparisons do not establish a replacement retention law or authorize a production repair.

## Reviewed source identities

SHA-256:

- ssurgo.py: `02d3b1da89195077d32df279790314d89d19183518450ca30b9231f32390bb27`.
- horizon_mixin.py: `e803959e3281f00c6d6b60e2431bff0586a8a169972e80f7072a85feabf29d53`.
- horizon_boundary.py: `d15b596a912153d25ab8d5e938de706138f3e5ff7ec8322c128ca522aa12e170`.

The durable contract may record evidence and admission requirements; no runtime formulas, fallback policy, defaults or thresholds should change in this phase. Reviewer writers are clear after scoped documentation lint.
