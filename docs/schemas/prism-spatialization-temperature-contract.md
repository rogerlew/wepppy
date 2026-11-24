# PRISM spatialization temperature ordering

## Authority and status

[ADR-0092](../adrs/ADR-0092-prism-temperature-inversion-midpoint-proposal.md) is accepted. Development-stack implementation conformance is verified in [the implementation report](../work-packages/20261013_prism_temperature_ordering/report.md); deployment remains separate. This contract governs the Rust daily writer, NoDb Python breakpoint writer, public Python PRISM writer, and EDDE adapter. It does not alter other climate modes or retroactively rebuild projects.

## Numerical rule

Apply each writer's existing monthly normal offsets and precipitation calculation, preserving its operation order and serializer. Require finite source temperature extrema with Tmin <= Tmax and finite temperature normals/adjusted extrema. A malformed or nonfinite source is an input error, not a spatial inversion to repair. Do not broaden precipitation, dates, auxiliary-field, or input-format validation beyond existing contracts in this change.

For adjusted Tmax a and Tmin b, if b > a set both to a/2 + b/2; otherwise leave both unchanged. Equality and zero range are valid. Apply before serialization, without a tolerance, positive range floor, swapping, one-sided preference, or alteration of other days. The arithmetic midpoint of the extremes is preserved before output rounding; this is not a claim about observed/time-integrated mean temperature. Serialized extrema must remain finite and ordered. Monthly means and future signals may change slightly where repairs occur; measure the differences, do not force exact aggregate preservation by changing valid days.

## Compatibility and errors

Preserve existing positional calls, return shapes, precipitation behavior, breakpoint timing/depth records, NoDb persistence keys, path ownership, and build-stage finalization. Valid adjusted records must retain the same writer's previous serialized values. Existing serializers can differ at rounding ties; across writers require numerical agreement within their existing 0.1 C output precision, not byte-identical formatting. New temperature validation uses ValueError in Python and the native wrapper's existing OSError translation of InvalidData I/O errors in Rust; EDDE retains DataQualityError. A failed generic streaming write may retain a partial destination, as before; it is never successful. Existing EDDE new-output/companion ownership and incomplete-attempt behavior remain authoritative.

## Diagnostics and provenance

Each completed Python revision logs source/output context with `method=midpoint_if_inverted`, `corrected_days`, `maximum_inversion_c`, and `maximum_adjustment_c`. The native writer emits the same scalar fields and source/output context on its existing process-output channel; public return values remain unchanged. A zero-correction result reports zero counts/magnitudes. Maximum adjustment measures actual pre-serialization floating-point movement; mathematically it is half the inversion, but rounding can differ at machine precision. Nonfinite/unrepresentable diagnostic magnitudes or monthly adjustments fail through the established error family before completing the output.

EDDE's existing `.prism.json` gains additive `temperature_ordering` containing these four fields plus `monthly_mean_adjustment_c`: twelve objects in calendar-month order, each with `month`, `days`, `tmax`, and `tmin`. Values are mean pre-serialization changes relative to raw offset temperatures; an absent month has days=0 and null adjustments. Existing `maximum_rounding_error` is measured against repaired expected values. Existing manifest keys remain unchanged. Legacy manifests without `temperature_ordering` mean diagnostics unavailable, not zero corrections; no migration is required. Source/output hashes and the normals remain retained.

## Required evidence

Compare valid, equal, inverted, negative-temperature, near-equality, month-transition, rounding-tie, invalid-source, and nonfinite states through real daily and breakpoint writers. Exercise occupied/new EDDE output ownership and legacy metadata separately. Retain correction magnitude and mean/signal drift. Verify the rebuilt native extension actually imported by WEPPcloud, normal climate preparation into `wepp/runs/`, exact consumed values, and fresh WEPP output. Existing logs and visible climate artifacts remain inspectable via their established workflow surfaces. This numerical fix does not authorize deployment, permissions changes, a Python replacement for the native writer, or new project-artifact exclusions.

## Artifact visibility and downstream scope

Revised climate files are published through the existing staged build. The operator retired the standalone temperature-ordering log on 2026-11-21 after confirming its original analysis had ended. Build status and errors follow the existing completion and failure paths. EDDE retains its JSON companion. Historical files remain accessible through the ordinary browse and archive paths.


Preserve auxiliary fields except for the historic PRISM opt-in dew-point derivation below. The existing Historic PRISM downstream dewpoint floor remains `max(raw tdmean, final Tmin)` under `prism-historic-climate-contract.md`; a repaired lower Tmin can therefore change that floor legitimately. Do not freeze the pre-repair dewpoint or alter the floor rule. Add a repaired-day regression for that existing downstream behavior.

For historic PRISM 800 m Multiple mode, the optional native dew-point floor consumes the final serialized Tmin after the temperature-order repair. The enabled and omitted argument contracts are defined in [Historic PRISM climate integration](prism-historic-climate-contract.md#native-hillslope-dew-point-revision).
