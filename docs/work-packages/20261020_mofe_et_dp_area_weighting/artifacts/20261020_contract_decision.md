# MOFE-ET-DP-01 Contract Decision

## Authority, baseline and classification

Operator first requested scaffolding fixes 1-3 and inactive R removal, then
explicitly requested "execute the work-package" on 2026-10-20. This authorizes
the bounded numerical corrections and necessary local checkpoint. No deployment
or original-project mutation is included. Baselines: WEPPpy
`fc67fcad6622202955c18635dd7a0b053ee875a2`, wepppyo3
`0515272453e36fe071c7812fb9d8ca2cf1642d08`.

This is an intended contract amendment, not conformance to old contracts:
output-scope prescribed sums and export specification prescribed terminal OFEs.
Amended canonical authorities: hillslope-water-aggregation-contract.md,
output-scope-contract.md, report-cache-freshness-contract.md, Features Export
specification section 8, ADR-0098. Their exact bounded delta is daily area
weighting of local fluxes, ET derivation, valid-area policy and cache versioning.
Read these documents together. Implementation conformance is pending.

## Input matrix

| Dimension | Cases and expected evidence |
| --- | --- |
| Geometry | single/equal/unequal OFEs; subdivision; multiple hills; merged IDs |
| Time | two days/year, multiple years, sparse day; preserve annual divisor |
| Identity | baseline/Roads/AgFields H.wat; canonical/legacy OFE spelling |
| Selection | event/current/comparison; export event/yearly/annual; hidden Area |
| Invalid | missing daily key or native OFE ID: error; nonpositive/nonfinite Area: error or dashboard null; infinity: error |
| Null flux | zero contribution; no fabricated area |
| Duplicate | malformed upstream; existing duplicate checks retained, no general deduplication redesign |

## Runtime state matrix

| State | Required outcome |
| --- | --- |
| Absent required source, no cache | existing missing-source failure |
| Empty source/selection | empty report or null metrics with geometry retained |
| Populated cold | fresh corrected artifact, independent 5/7 mm oracle |
| Warm marked cache | verified current only with matching dependencies |
| Legacy unmarked with source | rebuild, even if hashes/timestamps match |
| Historical missing dependency | explicit historical_unverified with warning |
| Failed build | attempt failure visible, prior published bytes preserved |
| Archived/restored | preserve historical bytes, same freshness rules on use |
| Native API unavailable, old cache | historical warning only under existing source-newer guard; newer source fails |
| Old native binary | marker verification fails before publication |

## Compatibility, security and evidence

Signatures/raw schemas/labels and unrelated numerical fields remain stable.
The corrected report requires canonical sim_day_index; malformed legacy sources
without daily identity fail explicitly. Cache provenance adds a semantic marker;
export cache identity changes. Security impact is low: no auth, transport,
permissions, queue, path, or topology changes. Existing atomic publication and
run-scoped selectors remain in force. No dedicated high-impact security review
is required. Two independent contract reviews must check these boundaries.

Tests use unequal 250/750 areas, ET 2/6 and Dp 4/8 (expected 5/7), two-day
10/14 totals, unchanged routed fields and independently executed SQL. Generated
artifact readback, exact native binary identity, stale/warm caches, report HTML/
CSV, serialized exports and a real MOFE copy are completion gates. Broad test
failures or unavailable runtime evidence must remain explicit limitations.

Review clarification: AgFields unresolved mixed-source many-to-many joins retain
existing explicit failure. Null dashboard ET stays unavailable through ranges,
comparison, color and tooltip consumers. Native-unavailable legacy access remains
a historical exception; a callable old writer cannot publish unmarked results.
