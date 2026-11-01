# Revised reset reader and completed readback

Disposition: **PASS for the completed retained-v2 readback.** The initial reader/declaration/results and demonstrated findings remain preserved. No model invocation or old-root write was performed by this reviewer.

Reviewed additive reader SHA-256 `c035b0698573508cfa7e84f34c6db5d864ce81f584efce05e6a91e133dc521aa`, bound by retained declaration SHA-256 `a1f4679fe52dd8b189e73f3108553ffb2fe2e803b04fa9485ac6c6c0cd7bb8ee`. Actual declared dependency hashes match. Full branch identity and duplicate rejection close the marker-join finding. Component-level signs, geometry flags, explicit unavailable records, primitive/derived finite checks and strict result serialization close the reporting findings. The bound now uses absolute primitive terms. Nonzero comparison rows are retained and both branch totals reconcile to the original accepted reader. Clearing starts and initialization endpoints now require full observed identities. Revised controls exercise duplicate markers, every branch identity field, NaN, negative cells and invalid geometry in addition to reset assignment failures.

Independently checked actual output hashes, row counts, unique and disjoint map/layer identities, exact dry-target assignment and unchanged ice, decomposition identities, and every clearing's next-initialization identity against the original supplement:

| Scenario | Zero-ST layers | Nonzero comparisons | Clearing chains |
| --- | ---: | ---: | ---: |
| zero-ks1 | 2,936 | 35,984 | 20 |
| normal-ks1 | 4,246 | 35,704 | 19 |
| high-ks1 | 9,571 | 35,349 | 19 |

All branch counts agree with the accepted original trace receipts. No zero-ST layer is unavailable. Every reset assignment error is zero; every nominal residual equals its inherited reference mismatch within the declared reconstruction bound. All 58 clearing IDs appear and close at the exact previously observed initialization endpoint. This verifies accounting and joins, not an intervening internal flux producer or causal recovery.

Completed receipt SHA-256 values:

- Zero: `fda7ff505a9d9edcfddb0a043b1e7dba5ac15cde72bfa37558d2dcebae9a6e2d`.
- Normal: `ca0d1c5f6a888d0a0c8ec54651996026d6b32ea651dfb1415707cbbeacea8365`.
- High: `4c3fe6354b2a4b2c2f9432a069bb5c805414a7aa03ec2f2de3b701f21ccbf4e5`.

The review reuses previously accepted trace framing/hash provenance and checks the additive results; it does not repeat the full native campaign. No implementation blocker remains for this readback. Reviewer writers are clear after scoped documentation lint.
