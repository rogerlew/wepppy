# Warming roughness experiment validation

## Disposition

Completed research experiment on forest, 2026-10-06 UTC. All execution and input
isolation gates pass. This does not certify physical calibration, a new roughness
default, or conservation between the routed hydrograph and volume ledger.

## Evidence

The [execution summary](evidence/execution-summary.json) records 864 successful
hillslopes in each of three cases, three successful watershed executions, and
the successful output-only control: 2,596 model executions total. Source inputs
were SHA256-verified before staging, after staging, and after execution. The
[binary manifest](evidence/binaries.json) identifies the exact corrected pair.

The [post-run audit](evidence/validation.json) verifies every original consumed
file hash, every management-file reference in the hillslope run controls, and
byte-level mutation boundaries. Exactly 1,885 fourth-field roughness tokens
change per treatment; every other management byte is preserved. All 98 outputs
from the 14 untreated hillslopes match the baseline. Each case has 865 successful
terminal records, no stderr content, and no stdout lines matching warning, NaN,
floating-point, or SIGFPE signatures. Raw logs and terminal records remain on forest.

The [output-mode parity record](evidence/output-mode-parity.json) confirms exact
equality of chanwb.out, chnwb.txt, ebe_pw0.txt, loss_pw0.txt, pass_pw0.txt,
plot_pw0.txt, and soil_pw0.txt. chan.out intentionally differs because one replay
prints daily peaks and the other prints all 600-second samples.

The [analysis summary](analysis/summary.json) verifies 8,766 complete dates and
1,262,304 finite, nonnegative hydrograph samples per case. Peak comparisons agree
within printed precision. EBE and channel-ledger daily volumes match exactly.
Figures 1–3 were visually inspected; the Figure 2 legend was moved clear of the
hydrographs, and difference panels expose otherwise overlapping curves.

## Tests and retained failed staging attempts

Token mutation self-tests, Python compilation, repository diff whitespace checks,
and local Markdown-link checks pass. The actual input parser independently
checked every initial roughness value before execution. No production application
code changed; a repository-wide application test suite was not run for this
offline research harness. No claim of broad application regression coverage is made.

Two staging-only attempts are retained with suffixes staging-attempt1 and
staging-attempt2. The first was interrupted before modeling to tighten record
selection. The second failed semantic readback because an initial selector
incorrectly limited residue indices to 1–3, missing OFE 4. That restriction was
removed and a residue-index regression check added. Neither attempt produced
model results or contributes to the figures.

## Scientific limitation retained

The integrated printed hydrograph is approximately 1.3% below the reported
volume ledger in every case. This exceeds printing-roundoff alone and is not
resolved by the small ledger residual. The comparison preserves both measures
without rescaling. Investigating routed q1 integrals versus chvol bookkeeping
is separate work; no channel formula, parameter, or storage correction was made.
Small centroid changes in the selected events also fall below conservative paired
discharge-rounding bounds, so precise timing shifts are not established.
