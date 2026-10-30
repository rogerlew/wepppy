# Study correctness review

Self-review; no independent-agent or field-validation review is claimed.

## Scientific controls

The diagnostic selection was frozen before held-out results. No treatment passed
all diagnostic profiles; the broad roles/raw run is explicitly confirmation,
not accepted calibration. No climate-specific fitting or denominator floors.

Primary preparation uses current owned 9002 conversion and prep functions, with
intermediates and consumed soil readback retained. The retained project example
uses a historically customized lookup; it is not mislabeled as exactly reproduced
by the current default-lookup treatment. This is function-level preparation, not
full-project Roads integration. Management is fixed to isolate soil changes.

Equivalent split/unsplit 7778 profiles preserve all material properties and
non-layer parameters, checked across the union of their depth boundaries for
all five diagnostic profiles. Unsplit 9002 reproduces the sandy-loam 7778 result.
Exact-release source provides an explanation for the observed subdivision
sensitivity. Source reasoning is distinguished from internal-array instrumentation,
which was not performed. No native code or binary was modified.

## Artifact and metric checks

The analyzer requires declared case identity, successful status, every retained
input/output SHA-256, complete WAT calendar/OFE rows, finite values and consistent
annual/common-report results. Comparisons require identical climate, management,
slope and run prompt hashes. Fresh validation reference runs cover the new soil
class assignment. Reused prior references are revalidated before comparison.

Native modern PASS metrics are separately named and are not used as denominators
for detailed-report comparisons. Spatial net loss is not mislabeled as road-only
detachment. Zero-reference exports and absolute differences remain visible.

Serial and parallel diagnostic revalidation produced identical summary results.
Tests cover treated-layer splitting, unchanged deeper material and other OFEs,
existing boundaries and invalid inputs; the previous common-report and calendar
regression tests also pass.

## Final disposition

Scientific and repository closeout complete: 1,615 study cases and two minimal
replays validated; 12,083 repository tests passed, 298 skipped, no failures. No production parameter candidate is accepted; promoting
one would require an ADR, contracts and actual project Roads preparation evidence.
