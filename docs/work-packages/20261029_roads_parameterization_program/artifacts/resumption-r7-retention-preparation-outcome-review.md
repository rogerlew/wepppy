# Revision-7 retention preparation outcome review

Verdict: **PASS for the actual input gate of the declared paired native pilot**.
All four default/optional pairs preserve geometry and differ only in main
horizon FC/WP. B2/B3 retain the intended deep contrast. B5 has separate
fresh-default drift that must remain explicit in subsequent interpretation.
This review establishes input comparability, not native success or efficacy.

## Evidence and method

Evidence root:
`/wc1/runs/ro/roads-parameterization-program-20261103/retention-preparation-v1`.

| Artifact | SHA256 |
| --- | --- |
| `declaration.json` | `5be61161a62c428867735328cd9b085da64473e13d26d92f8b8aae88bb87da7b` |
| `preparation-result.json` | `e24ade55e77907dc75ebc4d4e45378d53cf48483ec86366991830cec6f1e68ab` |
| `source-readback.json` | `2ec79d75fa2d61a1c8d44d216b329f262145a18567a0744c5a4876762c3e0fbc` |
| `case-readback.json` | `6c5e0797fa5795c74416087b9ba227272226d7d94feb69c89b618c20cb448fa2` |
| [Independent reader](read_r7_retention_preparation_outcome.py) | `a7d030e2a1b492434ba6aa50eba0c1899646d6f01a3f398d478e81b28f232265` |
| [Independent readback](resumption-r7-retention-preparation-outcome-readback.json) | `fd835f0e92752175e6c159376e3cbdafbaf2dba5f8fd51cada1ce36bd924b138` |

The reader ran successfully through `wctl exec weppcloud python -B` with the
ordinary installed soil parser and companion validator. It does not import the
preparation helper or reuse its comparison functions. An independent text reader
checked every numeric horizon token against the installed parser: 11 fields
for source 7778 rows and all 18 fields for 9002 rows. It independently calculated
pair differences, joined source decisions to SQLite and checked the declared
policy inverse for eligible decisions. Log:
`/tmp/roads-retention-preparation-outcome-review.log`.

All **101 retained files** matched the result inventory plus the result itself.
All 1,230 dependency bindings, 59 input bindings and 27 cohort files rehashed
successfully. Both the original cohort and preparation tree remained unchanged.
No source builds, source outcome files, network calls or native runs were made
by this review. The frozen pre-build review was not changed.

## Source and provenance checks

Both arms contain exactly the seven declared source profiles: 53949, 1718465,
1718494, 1718510, 1856573, 2711184 and 2711250. Across source copies, role
treatments, stacks and final stages, the reader parsed **62 soil files** and
**584 horizon rows**, including **40 9002 files**. All **31 optional companions**
validated recursively within their caller-owned roots. Default files had no
optional companion. Every lineage identity belongs to the declared cohort and
binds acquisition receipt
`495953db4f2850caf14d1d6f1095b41293e3a5fd807a6e717b19d9c2b4e9fa7c`.
Case source copies and their optional companions match the original source-build
bytes exactly.

All **37 original horizon decisions** joined to their actual cache horizon,
component and material. Their original fields agree with the acquired rows.
The decision set contains 23 eligible, 12 prior-exclusion and 2 fallback-unchanged
records. Eligible does not necessarily mean a changed value: zero fragment mass
can produce the same FC/WP. Every emitted default and optional FC/WP value agrees
with its corresponding rounded before/prepared decision. Excluded and fallback
decisions remain unchanged. The source cache passed SQLite integrity checking.

## Paired geometry and retained contrast

All source, road, fill, buffer, stack and final comparisons permit only main
horizon FC/WP differences. Density, rock fraction, conductivity, remaining soil
fields and all seven native hydraulic trailer fields are identical within each
pair. In particular, trailer WP/FC are distinct from the main WP/FC fields and
are unchanged. Final role order is bare/bare/forest with saturation 0.75.

| Case | Final FC/WP fields changed | Full depth per OFE | Fresh default versus frozen U12 |
| --- | --- | --- | --- |
| B2 | 6 | 1600 mm | Semantically identical |
| B3 | 6 | 1600 mm | Semantically identical |
| B4 | 18 | 400 mm | Semantically identical |
| B5 | 36 | 1600 mm | Nine deep-row fields differ |

Every ordered horizon depth equals the frozen counterpart, including the
200 mm support boundary. B2/B3 retain depths 50, 200, 230, 610, 760, 860, 990
and 1600 mm in each OFE. Their only paired differences occur in the
**990–1600 mm row**: FC **0.1851 → 0.1751** and WP **0.0823 → 0.0778**, in
all three roles. Density remains 1.5, rock fraction 12.5 and conductivity 100.8.
The lineage reaches fresh horizon 84543625 in component 28163866, with original
source bottom depth 152 cm; the existing source writer's final-depth rounding
to 1600 mm is retained in both arms and the frozen baseline.

## Fresh-default drift and native boundary

B5's **1270–1600 mm row**, in every role, differs from frozen U12 as follows:
FC **0.188 → 0.1958**, WP **0.09 → 0.0815**, and conductivity
**59.8734 → 21.3038**. This accounts for all nine fresh-default drift fields.
The fresh row has missing original retention/density inputs and follows the
recorded `rosetta2` fallback; the optional policy leaves this row unchanged.
The policy's B5 contrasts occur in the preceding six rows. This review does not
assign the historical drift to a specific source-vintage or builder change.

The fresh B5 default/optional pair remains controlled. Its later difference
cannot be described as recovery of the exact frozen B5 baseline, and native
comparisons must keep that baseline drift separate. B2/B3/B4 have no such
semantic drift after excluding comment provenance.

No unresolved input blocker was found. The parent may proceed to the separately
reviewed native declaration for the bounded pilot. That declaration still needs
to bind the exact final soils, remaining native inputs, plain/observed binaries,
runner and output checks. Native success, completeness, observation parity and
scientific interpretation remain later gates; this review admits no default,
formula, release or broader workflow change.
