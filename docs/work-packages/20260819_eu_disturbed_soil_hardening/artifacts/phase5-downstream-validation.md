# Phase 5 Downstream Validation

**Executed**: 2026-08-19 UTC
**Test**: `tests/eu/soils/test_esdac_disturbed_downstream.py`
**Result**: 6 passed

## Matrix

| Fixture case | Base result | Downstream result | Evidence |
| --- | --- | --- | --- |
| `pilot-0001-control` | valid, version 7778 | valid, version 9002 | Reparsed file has expected `luse`/`stext`, finite parameters, and cumulative depths `[200, 1200, 1500]`. |
| `pilot-0021-missing-landuse-metadata` | degraded | degraded | `source.usedom.no_information` remains in the downstream reason codes while the transformed artifact passes structural checks. |
| `pilot-0014-zero-stu` | rejected | rejected before parse | `source.stu.mandatory_profile_empty` and `disturbed.base.rejected` are retained; no generic downstream file is created. |

The negative controls mutate the serialized 9002 artifact after writing. The
validator rejects water-content inversion, non-increasing cumulative depth,
and zero Ksat after reparsing. The implementation is an additive EU quality
boundary. Phase 6 will propagate the EU base result into the EU Disturbed
runtime path; non-EU disturbed behavior remains outside this scope.
