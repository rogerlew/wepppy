# Independent legacy-soil particle audit review

Disposition: **confirmed research-audit parsing defect**, not an R4 native
regression or demonstrated legacy engine accounting defect. No native observer,
engine patch, tolerance change, or clipping is justified by these 91 flags.
This is independent AI scientific review, not institutional peer review.

## Cause and exact example

`audit_particle_closure.py` tokenizes ELEMENT lines with `split()` and reads
index 23 as sediment leaving the terminal OFE. Native ELEMENT is fixed-width.
`src/sedout.for:543` format 1000 places effective duration F7.3 immediately next
to enrichment F6.3, without an intervening separator. CONTIN format 1200 has
the same layout. When enrichment reaches 10, both fields can fill their widths
and whitespace tokenization collapses them. `src/outfil.for` declares SedLeave
in kg/m and QRain in mm; these quantities must never share a column interpretation.

In site/1718465/inbare/gravel/high on 2002 day 103, the raw text contains
`5.00017.673`: effective duration is 5.000 h and enrichment is 17.673. Splitting
produces 25 rather than 26 fields, so index 23 becomes **QRain = 1.274 mm**.
The old audit multiplies that by 3.96 m and reports the meaningless “bulk mass”
5.04504 kg. The true SedLeave field is **0.010 kg/m**, yielding 0.03960 kg.
PASS's summed class concentration times runoff volume is 0.03889976597 kg.
The absolute difference 0.00070023403 kg is inside the unchanged printed-value
bound 0.0019806849215 kg. The fixed-width parser resolves the apparent loss.

SLOSS computes class concentration from terminal export divided by runoff depth
and effective length, and WSHPAS publishes class concentrations and runoff
volume. That producer chain supports the audited kg/m-to-kg comparison. No
calendar shift, extra EVENT aggregation, width replacement, or change to EVENT
versus SUBEVENT scope is required here. The faulty column assignment precedes
that scientifically meaningful comparison.

## Complete independent readback

`review_legacy_particle_fixed_width.py` independently replays both generations
from their hash-bound raw outputs. It uses the native descriptor widths, checks
unique date/OFE keys, and preserves the prior Decimal half-last-place product
bounds, calendar conversion, terminal OFE, width and EVENT selection.

| Generation | Cases | EVENT records | Prior mass flags | Fixed-width flags |
| --- | --- | --- | --- | --- |
| r3 legacy controls | 116 | 5,887 | 91 | 0 |
| r4 legacy anchors | 116 | 5,887 | 91 | 0 |

Each generation contains 205 ELEMENT rows where whitespace loses a field.
Every one of the 91 mass flags has 25 tokens, enrichment at least 10, and the
misread sediment value exactly equal to QRain. Both generations therefore have
the same audit failure mechanism. No fraction-normalization or class/bulk flag
remains in this declared legacy EVENT panel after the field correction.

The full receipt `review-legacy-particle-fixed-width.json` retains every case,
raw-output hash, old flagged row and corrected mass/bound. The self-contained
`review-legacy-element-fixed-width-fixture.json` retains the exact native row,
PASS tokens, format descriptor, units and expected columns for a regression.

## Smallest repair and limits

Correct the research audit to read ELEMENT's native fixed-width fields, preferably
through the established ELEMENT reader; require 26 fields and preserve failure
on malformed data. Add a regression using the retained adjacent duration/
enrichment row and an ordinary separated row. Re-run the same declared panel
with unchanged thresholds and regenerate the affected verification summaries.
This reviewer did not modify the production audit, source, tests, inputs or
original verification receipt.

After that audit repair is independently validated, these 91 flags no longer
block legacy-anchor use on this particle/bulk criterion. This does not approve
parameter promotion, the unmet magnitude objective, all possible EVENT/SUBEVENT
contracts, or the separate newly reported fraction-normalization issue being
reviewed by another agent. Existing native physical evidence is not enlarged
merely because the audit parser is corrected.
