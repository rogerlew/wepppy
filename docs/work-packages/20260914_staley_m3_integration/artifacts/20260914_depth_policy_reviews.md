# Depth replacement preliminary reviews

2026-09-14. Independent read-only reviewers: `source_contract_review`
(correctness) and `source_boundary_review` (security/source integrity).
Scope: replacement assessment, research script and retained JSON. These are
not final contract checkpoint or production implementation reviews.

## Findings and disposition

Both reviewers identified a medium research defect: temporary H/Cr rewriting
and suppression of the separate thickness field could erase a raw duplicate-ID
conflict. Fixed by retaining the original component rejection before every
transformation. Added all-policy cases where the conflict occurs only in those
rewritten fields, with normalized keys and duplicate source records.

Correctness identified a medium attribution error: all-recorded versus strict
bundled several policy effects. Corrected the hard-R contrast to all-recorded
versus depth-no-R. It changes 34 az_ponderosa map-unit means, maximum
+155.05882352941177 cm, five Topanga means, maximum +25 cm, and none in Moscow.

Source review identified missing pair provenance. The experiment now records
both canonical source IDs, source-row count, physical interval and explicit
`legacy_combination_pair` reason. Identical stable IDs are deduplicated before
pair recognition; their presence does not fabricate a second physical horizon.

## Independent rechecks

Correctness regenerated output exactly matching retained JSON and passed all
16 analytical cases. An additional 24 checks covered reversed record order and
normalized ID aliases. The reviewer closed both findings with no remaining major
finding in this correction scope.

Source review independently reproduced all 16 analytical cases and all three
frozen-fixture summaries. Original duplicate-conflict reproductions remain
unavailable across all policies, and input dictionaries remain unchanged.
The reviewer closed both source-boundary findings without opening the live DB.

## Remaining gates

H eligibility has direct NRCS support. Cr inclusion, endpoint-field precedence
and the bounded legacy-pair rule are proposed scientific choices. Authentic
paired records remain absent from the panel. Production-boundary validation,
WAL noninterference, soil-builder parity, lineage/source delivery and final
checkpoint reviews remain required. Earlier reviews of the strict proposal
do not constitute approval of this replacement.
