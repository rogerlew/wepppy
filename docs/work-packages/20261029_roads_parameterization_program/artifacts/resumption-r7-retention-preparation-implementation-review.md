# Revision-7 retention preparation implementation review

Verdict: **PASS for the bounded preparation step**, with no blocking finding.
This is an independent review of the scope reviewer's helper, not approval of
native execution, policy efficacy, default adoption or a full project workflow.
No source build, network request or native call was made during this review.

## Exact reviewed boundary

| Artifact | SHA256 |
| --- | --- |
| `retention-preparation-v1/declaration.json` | `5be61161a62c428867735328cd9b085da64473e13d26d92f8b8aae88bb87da7b` |
| [Preparation helper](resumption_r7_retention_prepare.py) | `32d324d9ad5bdbb007fc3c1b085e0cfc0ccc7fbe1e3b6ae5f3b13b33a6ce5b8b` |
| [Preparation protocol](resumption-r7-retention-preparation-protocol.md) | `c318f61a886a98563528f2bfff93729e0d65838c922a7e9b66d24662f34f9f7a` |
| `retention-source-v1/acquisition.json` | `495953db4f2850caf14d1d6f1095b41293e3a5fd807a6e717b19d9c2b4e9fa7c` |
| [Read-only staging evidence](resumption-r7-retention-preparation-prebuild-readback.json) | `7d78cb2f88c4eceee1723c5747acc8c6ad28c88b9cd326002a4c9178c3be2cf5` |

Evidence roots are under
`/wc1/runs/ro/roads-parameterization-program-20261103/`.
The installed-container readback rehashed all **1,230 dependencies, 59 input
bindings and 27 cohort files**, checked helper/protocol snapshots and reproduced
the declared UID 1000, GID 993 and interpreter identity. The preparation root
contained only its declaration and two snapshots. Recomputing case bindings
matched the declaration exactly.

## API and scientific comparability review

The four cases are the declared B2/B3 small-failure, B4 passing and B5
opposite-direction controls. Their twelve native input names, reference soil,
matched legacy road prior and bare/bare/forest role order are bound. All seven
development materials are required in both source arms; the withheld set is
excluded. The seven-material source build is broader than the three materials
used in these four paired cases, as explicitly declared.

The direct worker call uses the owned read-only worker-view factory and the
same source worker/defaults used by `makeWeppSoils`. Inspection of
`WeppSoil._get_horizons` found only deterministic fragvol/texture/reskind additions
to shared layer dictionaries; subsequent horizons copy values into separate
objects. Reusing the view does not apply the optional policy to the default
arm's horizon objects. Cache joins, selected component, horizon mask, restrictive
layer and optional decision before-values are checked before source publication.

The role, stack and staging calls match the installed
`_build_disturbed_mofe_soil`, `SoilMultipleOfeSynth.write` and `prep_soil`
contracts. No density override, organic-row removal, clipping, minimum-depth
extension or final conductivity override is enabled. The positional staging
arguments were checked against the actual implementation. Recursive optional
companions keep their parents within each case root and bind the actual
acquisition receipt. Default artifacts remain unmarked.

Pair comparisons parse the actual serialized source, role, stack and final
artifacts. Only main horizon FC/WP paths are allowed to differ. Read-only guard
checks confirmed that density, fragment fraction, depth, conductivity and
**native hydraulic trailer FC/WP** paths are rejected. The preserved-format
parser requires all seven 9002 trailer fields. Every frozen case parsed as
three 9002 OFEs with 200 mm support. B2/B3 have the full ordered depths
50, 200, 230, 610, 760, 860, 990 and 1600 mm in every role; B4 ends at 400 mm
and B5 at 1600 mm. Fresh artifacts must match the complete ordered depths,
not only the final depth. B2/B3 must also contain an actual final FC/WP contrast.

Fresh default versus frozen U12 differences are recorded separately from
default versus optional differences. Fresh-source identity or material drift
cannot therefore establish recovery of the old baseline. Those actual drift
records remain required review evidence before a native campaign.

## Acquisition readback and independence limit

The finalized cache passed SQLite integrity checking and contained 12 components,
53 horizons, 7 restrictions, 33 fragment rows and 53 texture rows. The retained
raw-response/cache comparison exactly reproduced `cache-association.json`;
all source-root hashes remained unchanged. The preparation helper's cohort
binding also matched the exact receipt and complete inventory.

This reviewer authored the acquisition observer. Replaying that parser is a
repeatability check, **not an independent parser implementation or independent
approval of its own source-acquisition code**. Parent acquisition review and
independent inventory/cache inspection remain separate evidence. No request
headers or cookies were printed in this review.

## Quality, residual debt and next gate

The helper separates declaration, source construction, role preparation and
readback clearly. Exclusive root/start receipts, post-build hash checks and
retained failure artifacts make interruption and failed gates observable.
The broad exception handler is a documented experiment boundary and re-raises.

Non-blocking debt: the preparation helper has no dedicated automated negative
test module. The read-only checks cover the concrete bindings and allowed-diff
classification; they do not exercise every failure path. Before promoting this
bounded helper into reusable tooling, add focused tests for missing trailer
fields, structural/depth drift, source-inventory drift and partial preparation.
Its duplicated source defaults and positional staging tuple are intentionally
small and pinned; reuse would benefit from explicit contract tests, not a new
abstraction in this experiment.

Actual source and prepared artifacts have not been produced by this reviewer.
The next gate must independently inspect `source-readback.json`,
`case-readback.json`, companion chains and `preparation-result.json`, including
fresh-default drift and exact final 9002 rows. This pre-build verdict does not
substitute for that artifact gate.
