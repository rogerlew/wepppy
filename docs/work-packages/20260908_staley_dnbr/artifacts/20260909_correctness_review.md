# Correctness review — dNBR backend

## Metadata

Reviewer: independent `/root/dnbr_correctness` agent. Date: 2026-09-09.
Scope: `dnbr.py`, focused tests, backend contract and ADR-0054; working-tree
changes on master based on `52f056eaa`. This record summarizes the read-only
review and follow-up disposition, recorded by the implementing agent.
Related review: [security](20260909_security_review.md).

## User outcome and state matrix

User receives normalized local artifacts and explicit coverage/mean values.
No browser upload, active NoDb pointer, or queue behavior is represented.

| State | Required behavior | Direct evidence |
| --- | --- | --- |
| Output absent | Create completed artifact after successful validation | Synthetic and real-fixture tests |
| Output empty or populated | Explicit output_exists; retain existing content | test_existing_empty_and_populated_outputs_preserved |
| Source partial | Mean over observations; partial warning | test_partial_mean_and_no_data_catchment |
| Catchment without dNBR | Unavailable summary, no zero-risk inference | Same test |
| Legacy external mask | Reject and require self-contained input | test_external_mask_rejected_instead_of_silently_discarded |
| Internal TIFF mask | Preserve support and mean | test_internal_mask_is_retained |
| Malformed encoding/grid/VRT | Explicit stable input error | Parameterized focused tests |
| Writer failure/source changes | Clean staging/reservation; no completed output | Writer-failure and source_changed tests |

Invalid source/encoding/grid/mask/date errors are expected input failures under
the canonical contract. No valid target overlap is an explicit resolution or
coverage failure. Storage errors are exceptional OSError. Output-exists is an
intentional nonreplacement contract. Coverage is not claimed exhaustive for all
GDAL file variants; restricted local formats are explicitly documented.

## Findings and disposition

COR-01, medium, resolved: detached MemoryFile decoding silently ignored external
TIFF masks. Reviewer reproduced normalized mean 0.55/full coverage instead of
0.1/half coverage. Recognized adjacent sidecars now cause invalid_raster before
decoding; reviewer reran the exact reproduction and confirmed rejection with no
output. Internal-mask positive control still succeeds.

Coverage requests, resolved: both public Arizona inputs now test native 30 m
and explicit 10 m targets. Added actual source mutation during normalization
and injected operational write failure to verify cleanup, plus internal masks.
Reviewer confirmed these additions and the final focused log: 45 passed.

## Verdict

Pass for scoped backend. Independent reviewer reports no unresolved findings.
Full-suite gate tracked separately in validation evidence. Future browser and
NoDb/RQ publication need their own valid-state and contract-first review.
