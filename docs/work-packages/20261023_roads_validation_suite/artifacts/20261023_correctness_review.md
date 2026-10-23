# Independent final correctness review

Date: 2026-10-23 UTC. Reviewer: `accounting_contract_review`.
Runtime, harness and report sources were reviewed read only.

**Approved for the scoped production repair, numerical evidence and scientific
interpretation. No unresolved high or medium correctness finding remains.**
This verdict does not substitute for the separate publication/access review or
the package's final broad regression gate.

## Findings resolved

- **Medium: production grade fidelity.** The doubled-grade control previously
  bypassed the production 40% cap. `tests/roads/roads_matrix.py::prepare` now
  applies the production clamp and retains requested/effective geometry and
  clipping flags. The fresh emitted road has 0.400000 at both slope points.
- **Medium: executed input identity.** The original identity inventory did not
  bind staged shared files. Initialization now records those files; analysis
  compares both their bytes and fixture identities. Required per-case run,
  slope, soil, management, climate, PASS and WAT identities cannot be omitted.
- **Medium: valid zero ratios.** Report rendering no longer calls min/median/max
  on an empty ratio set. The zero-detachment regression verifies unavailable
  contrast statistics instead of rejecting a valid complete experiment.
- Scientific wording now distinguishes WAT local accounting from PASS runoff,
  explains the requested-to-emitted rock-fragment mapping, and identifies the
  limited unrutted positive coverage. The extreme no-traffic/low-traffic ratio
  includes absolute quantities, the nearly zero denominator and different
  legacy management inputs.

The production diff preserves all three original plant definitions and original
`iresd`/`itype` references while selecting the required initial/yearly/OFE
assignments. It matches checkpoint `5ebc3b0ff`; the sole soil-template edit
removes the stray final `k` from `3psand10.sol`. No parameter value or formula
changes. Generated management readback checks the exact source sections,
selected assignments and all 200 scheduled years across the seven arrangements.
Independent comparison confirms all 14 previously executable pilot PASS files
remain byte-identical.

## Independent numerical evidence

The final source-bound root is
`/tmp/roads-matrix-verified-oct23/roads_matrix0`; its native test invocation
completed **516 passed** in 361.05 seconds. The retained
[read-only audit script](20261023_independent_native_review.py) and
[results](20261023_independent_native_review.json) establish:

- All 516 profiles have complete 2000–2015 calendars: 3,015,504 PASS rows and
  6,942,672 WAT OFE rows. Every OFE has a positive stationary area.
- Independent DuckDB daily sums divided by 16 match the produced detachment,
  signed deposition, sediment export, runoff, lateral and baseflow annual
  metrics with **zero absolute difference**.
- Full-profile WAT area agrees within floating reduction error
  (maximum 1.82e-12 m²). Density uses that area. Maximum WAT versus rounded slope
  area difference is 0.004 m², supporting the documented 0.0051 m²/OFE
  serialization allowance.
- The maximum is 92.5338443 kg/m²/year, from 215,859.25063 kg/year over
  2,332.76 m². There are 328 negative-deposition and 188 zero-deposition cases,
  187 export/detachment ratios above one (maximum 1.000037673), and zero
  nonzero PASS lateral profiles. These match the report.
- Execution-time model/builder/native identities still match the current
  inspected inputs. The native extension SHA-256 is retained in the audit.

The four retained project receipts and refreshed publication evidence show three
full-upload additive checks (34 completed road profiles each) and one explicit
54-of-55-feature unrutted subset (one road replacement plus one remainder on
WEPP target 28). The full-upload negative control retains two non-positive
upstream-OFE failures and no current receipt. The published evidence records
911 unchanged baseline files and 2,383 unchanged source files per project.
Source inspection confirms daily local WAT weighting, canonical PASS runoff
and streamflow-component reconciliation. This is not an independent rederivation
of the groundwater reservoir or a claim of complete watershed mass closure.

The final prose-only refresh is explicit and bounded: its helper rejects any
changed source except `analysis_context.md`, verifies the previous report and
numeric-result hashes, and records `interpretation_revision`. Numeric results
and native execution evidence were unchanged. Independently running
`wctl run-pytest tests/roads/test_roads_publication.py -q` after that refresh
gave **3 passed**; source freshness, exact render, vendor equality and unavailable
zero ratios are covered.

## Reviewed identities

The provenance below also binds the individual harness, analyzer, runner,
template and native identities; hashes here are SHA-256.

| Artifact | SHA-256 |
| --- | --- |
| `wepppy/nodb/mods/roads/roads.py` | `c902e86fd2c2cef162deef7231da159939458b137c7498c6054f7e6e96517aec` |
| `3psand10.sol` | `c37870ab65aa917be188d2e591323bf4973292cd26f066b30c1337dcc277954b` |
| `matrix_results_current.json` | `f8fed5c145c507548db0c331e1d7e603a9f54cd72e399db5bef930b6203dab11` |
| `analysis_results_current.md` | `69ac12140d779b92ed06c383adeb671a0ab4ab5f81b1dfd23541040d59bdc32b` |
| `analysis_provenance_current.json` | `eec985dfbc4d2bec1f6ad03fc384b0206666a4bccf0a632c7a7847ceab53a5a7` |

## Residual limits

This is one site's climate and prescribed geometry experiment, including an
8.6 mm segmentation stress case. High detachment, non-monotonic contrasts and
zero PASS lateral flow remain observed model behavior, not calibration evidence.
The positive unrutted fixture exercises only one replacement target and cannot
certify the original full upload or geographic routing generally. Historical
project artifacts were not migrated or repaired. Future regeneration still
requires scientific review of the manual interpretation; passing freshness
checks alone cannot establish its truth. Actual Usersum HTTP/navigation and
the broader regression result remain separate package acceptance evidence.
