# Historic PRISM downstream eligibility

## Authority and scope

Amendment PRISM-DOWNSTREAM-01, approved by the operator on 2026-10-08:
“my gut is prism should be fine for bot of these. run the follow up check and alignment.”
This authorizes historic PRISM eligibility for OpenET and AgFields and verification
of calendar alignment and parent climate consumption. Implementation conformance
is pending. This contract supplements `prism-historic-climate-contract.md`.

## Intended behavior

`ClimateMode.Prism800m` (16) is an accepted climate mode in OpenET climate
validation and AgFields observed-climate readiness. This applies to single,
Multiple (monthly PRISM revision), and MultipleInterpolated (nearest native
PRISM cell) forcing. All previously accepted modes remain accepted.

OpenET acquisition uses the existing observed-year bounds and existing 2016
start clamp. Results remain monthly ET in millimeters, keyed by hillslope
Topaz ID, year and month. Comparisons with WEPP use matching hillslope and
calendar month, including February in leap years. Missing satellite months
must not be interpreted as zero ET. This amendment does not extend external
data availability, alter acquisition range rules, or change authentication.

AgFields uses observed start/end years for annual crop schedules and references
`wepp/runs/p<wepp_id>.cli` from each subfield run. Thus a subfield inherits its
parent hillslope's already prepared PRISM forcing, including the selected spatial
method and any existing preparation transformations. It does not resample PRISM
at the subfield centroid. Readiness continues to require valid observed bounds,
watershed abstraction and each required parent soil/climate pair independently.

## State and error matrix

| State | Required outcome |
| --- | --- |
| PRISM with valid observed bounds | OpenET climate validation accepts; AgFields observed readiness is true |
| Missing optional downstream outputs | Existing acquisition/setup creates outputs; no new prerequisite |
| Empty or missing subfields | Parent WEPP readiness remains false; climate eligibility may be true |
| Populated outputs | Existing cache and stale-state rules remain authoritative |
| Supported legacy mode | Existing result and year behavior preserved |
| Unsupported mode | Existing OpenET ValueError and false AgFields observed readiness |
| Missing/reversed/malformed bounds | Existing year validation failures/readiness retained |
| Missing parent soil or climate | Parent WEPP readiness false with missing IDs |
| Unauthorized caller | Existing feature/run/token checks reject; climate eligibility grants no entitlement |

## Compatibility, security and rationale

This is an additive eligibility change, with no persistence/schema migration,
new service, dependency, queue edge, grant or parameterization change. Existing
feature access is governed by `feature-access-governance-contract.md`; output
scope remains governed by `output-scope-contract.md`. Native PRISM has actual
calendar years, and the downstream consumers operate on calendar bounds and
prepared parent files rather than requiring a particular gridded source.

Regression evidence must exercise acceptance and invalid states, inspect actual
PRISM CLI calendars for both spatial methods, verify an AgFields-generated run
resolves the intended parent CLI, and align a bounded real OpenET monthly sample
with WEPP output dates. External acquisition failures must be reported rather
than replaced with fabricated satellite data.
