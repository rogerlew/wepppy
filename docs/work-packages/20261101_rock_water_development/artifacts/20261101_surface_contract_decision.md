# Surface proxy support contract decision

Starting implementation: WEPPpy c6345fd58. Scope: existing RUSLE cosurffrags loader
and its RAP/SBS source manifest report. Operator explicitly executed the broad
rock/water program authorizing supported source/provenance development; this is
within that authority and does not implement the gated Roads UI.

Canonical amendments: wepppy/nodb/mods/rusle/specification.md surface proxy policy
and docs/schemas/rock-fragment-representation-contract.md run-scoped reporting.
The exact additive `support` keys and denominators are defined there. Normative
intent is to expose conditional aggregation support without changing numeric
outputs, source precedence, clipping or defaults. No formula/parameter changes;
an ADR is not required for this metadata-only behavior.

Confirmed discrepancy: the existing query filters NULL before retaining rows and
reports only usable row_count. It hides missing and unusable support. Unknown-area
records cannot be treated as complete mapped footprint. Existing finite out-of-
range values are still included numerically; flag them without silently changing
that established behavior in this change.

Compatibility and propagation: additive manifest object only, no renamed/deleted
keys or changed NoDb/input/parquet schema. Existing manifests remain valid and only
explicit recalculation adds metadata. Both actual RAP/SBS artifact paths must
preserve C raster values for identical existing inputs; retain current auto/manual
fallback semantics. No native WEPP input changes are caused by this C manifest.
No auth, locking, storage boundary or queue behavior changes.

State matrix: absent parquet, absent recognized column, empty table, all-NULL,
finite measured zero, mixed valid/NULL/nonfinite/out-of-range, area absent, valid
positive/NULL/nonfinite/nonpositive area, and malformed nonnumeric data. Existing
expected optional-absence outcomes remain unavailable/fallback; malformed inputs
retain existing error-report contract. Never invent area for unknown records.

Validation: actual DuckDB parquet reader and generated RAP/SBS GeoTIFF/manifest
readback; independent frozen numeric mean/clamp expectations, exact zero/absent
semantics and incomplete support. Existing focused RUSLE tests plus required broad
suite. Obtain two independent contract reviews and commit this ancestor before
editing production code.

Review clarification: retain original short-circuit behavior for NULL cover with
unparseable area, unparseable cover with NULL area, and nonfinite cover with
unparseable area. Diagnostic parsing is tolerant of these excluded fields; an
explicit unparseable_cover_rows counter distinguishes unknown strings from numeric
nonfinite. Original numeric aggregation still determines whether an input error
occurs, before diagnostics are attached. Add real-parquet controls for these states.
