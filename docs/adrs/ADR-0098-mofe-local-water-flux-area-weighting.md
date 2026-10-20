# ADR-0098: Weight MOFE local water fluxes by contributing area

- Status: accepted for implementation; conformance pending
- Date: 2026-10-20
- Decision authority: operator request to fix audited consumers 1-3, followed by execution authorization

## Decision and rationale

Use the [hillslope water aggregation contract](../schemas/hillslope-water-aggregation-contract.md)
for report, event map and Features Export ET/Dp. OFE depth is not a hillslope
volume. Weighting by local area conserves represented volume and is invariant
under segmentation. Sum daily weighted depths over time. Preserve routed fields
and temporal conventions to bound the scientific change.

Reject unweighted sums (depend on OFE count), equal averages (ignore unequal
area), terminal OFE selection (drops other local fluxes), and cumulative upstream
area (counts contributions twice). Require valid local area rather than inventing
weights. Retain explicit historical cache access but distinguish it from current
corrected results. Version caches and verify native metadata to prevent a stale
binary from publishing falsely corrected results. No raw schema or new dependency
is needed. Native daily state scales with hill-days rather than full source rows.

## Decision provenance

- Venue: operator/Codex workspace conversation, 2026-10-20, America/Los_Angeles; exact message time not retained. Checkpoint authored 18:56 UTC.
- Participants: requesting operator and Codex; no meeting participants inferred.
- Decision owner: requesting operator, through explicit correction and execution requests.
- Implementer: Codex in WEPPpy and wepppyo3.
- Old/new delta: native summed OFE depths, event ET summed components across OFEs, exports selected terminal OFE. All now require daily local-area weighting for ET/Dp only.
- Evidence: [consumer audit](../work-packages/20261020_mofe_et_dp_area_weighting/notes/consumer-audit.md), [execution and regression plan](../work-packages/20261020_mofe_et_dp_area_weighting/prompts/active/mofe_et_dp_area_weighting_execplan.md).
- Risks: old caches/binaries can mask correction; malformed daily keys or Area now fail explicitly. Existing mixed-source export cardinality rejection is preserved.
- Rollback: pair native and Python consumers, restore compatible code/cache semantics through existing release procedures if regression evidence fails; do not relabel historical rows corrected. No original run or production deployment is authorized here.
