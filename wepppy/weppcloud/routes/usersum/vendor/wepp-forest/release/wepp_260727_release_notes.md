# WEPP 260727 Release Notes

Status: Withdrawn from the WEPPpy vendor set on 2026-08-05.

The release remains documented for historical provenance, but its watershed
and hillslope binaries and sidecars are no longer distributed by WEPPpy. The
sidecar contract selects HBP output exclusively; those files cannot be merged
with legacy flat-file pass inputs used by workflows such as AgFields
integrated-watershed assembly. Persisted projects must explicitly select a
compatible installed binary and regenerate dependent pass artifacts.

## Summary

WEPP `260727` corrects hillslope-area indexing in direct-HBP watershed runs.
Each HBP shard's one-based hillslope metadata is now copied into the matching
one-based legacy WEPP array slot.

Previously, the legacy array's zero element received hillslope 1, every
reported hillslope received the following hillslope's area, and the final
hillslope retained an initialized zero. Hydrology, erosion equations, and the
HBP binary format are unchanged. Release metadata identifies the current
writer format as HBP schema 2.0.

## Compatibility

The watershed LOSS text and parquet schemas are unchanged. Corrected runs now
contain the intended positive area on every hillslope row. WEPPpyo3 requires no
compatibility fallback because the corrected values use the existing columns
and numeric representation.

## Artifacts

| Artifact | SHA256 |
| --- | --- |
| `wepp_260727` | `cbcfac30e484613c5314e7a91b694863d26138905fcf04947650bc2c6c148918` |
| `wepp_260727_hill` | `d79a4bfde31feab8e3aff5ea5ae5d14b898f85b5f8fae5e471bc43d4078eddcc` |

Both binaries were built sequentially with pinned `/usr/bin/gfortran` and
request `/lib64/ld-linux-x86-64.so.2`.

## Validation

- The focused one-based metadata association contract passed.
- The complete WEPP test suite passed.
- A copied six-year, 587-hillslope `mdobre-foursquare-fovea` gate regenerated
  every HBP shard with `wepp_260727_hill`, then replayed them with
  `wepp_260727`; stderr was empty.
- All 4,109 annual and average hillslope LOSS rows had finite positive areas.
- The 587 average rows matched their corresponding HBP shard metadata at
  output precision; hillslope 587 reported `0.080 ha`.
- WEPPpyo3 converted the corrected LOSS and SOIL outputs and WEPPpy report
  consumers completed without schema changes.
