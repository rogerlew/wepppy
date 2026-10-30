# Boundary consistency validation

Status: complete. **12,135 passed, 298 skipped; no unresolved failures.**
Counts include the corrected and revalidated developer-mode assertion.

## Native consumed-artifact evidence

Final replay root: `/wc1/runs/so/soil-boundary-consistency-20261029-v4`.
The [replay](replay.py) reads immutable split/unsplit study inputs, uses ordinary
`WeppSoilUtil.write` and actual `prep_soil`, then executes the pinned
`wepp_261026` binary. It refuses an existing destination root. Exact source,
binary, consumed-input and output hashes are retained in
[native-evidence.json](native-evidence.json).

Both cases emit 150/200/400 mm in all three OFEs, preserve copied material fields
and original input hashes, and produce identical model records. Source provenance
comments intentionally remain different. Every native output file has the same
hash across the pair. Both pass all 17,532 expected daily OFE WAT records for
2000–2015 and complete 16-year report checks.

| Metric | Both normalized cases |
| --- | ---: |
| Sediment export, kg/year | 4473.288284256344 |
| Runoff, mm/year | 1001.54 |
| Spatial net loss, kg/year | 4525.834420976531 |

This reproduces the previous explicitly split result, not the lower unsplit
109.099 kg/year result. No native conductivity fix or road calibration is claimed.
The replay uses ordinary preparation with the Roads specimen; channel coverage
is emitted-artifact validation, not a new watershed simulation benchmark.

## Focused regression checks

- Roads matrix and publication gate: 530 passed, 5 skipped.
- Disturbed native matrix: 99 passed.
- Treatment-soil artifacts: 230 passed.
- Boundary/modern-version/capacity tests: 39 passed.
- Direct writers plus boundary tests: 46 passed.
- Final direct writers and SSURGO canned/mineral profiles: 15 passed.
- Soils, ESDAC and anisotropy focused run: 163 passed, 5 skipped.
- Utility serializers, single-input and upload references: 118 passed.
- Multi-OFE public stub: `wctl run-stubtest wepppy.wepp.soils.utils.multi_ofe` passed.
- `wctl check-test-stubs` passed.
- Changed-production broad-exception gate passed after relocating four existing
  SIFT allowlist line references; no new handler was introduced.
- Documentation lint and whitespace checks pass for current reviewed documents.

Focused counts overlap and must not be summed as unique repository coverage.
Unique coverage and exact log identities are retained in [validation.json](validation.json).

| Disjoint coverage | Passed | Skipped |
| --- | ---: | ---: |
| Successful broad prefix | 5314 | 54 |
| Exact continuation, starting with corrected case | 5962 | 239 |
| Roads | 530 | 5 |
| Disturbed native matrix | 99 | 0 |
| Treatment-soil artifacts | 230 | 0 |

The broad command was `wctl run-pytest tests --ignore=tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py --ignore=tests/disturbed/test_disturbed_matrix.py --ignore=tests/roads --maxfail=1 -q`.
The continuation used `wctl run-pytest @/wc1/runs/so/soil-boundary-consistency-20261029-v4/remaining-nodeids.txt --maxfail=1 -q`.
Excluded groups ran separately through `wctl run-pytest <group> --maxfail=1 -q`.

## Corrections during execution

Existing ESDAC and anisotropy assertions expected unsplit generated counts.
Updated assertions check emitted boundaries, copied properties and preserved
uploads; historical source fixtures remain intact. The SSURGO legacy writer
retains 350 mm total depth in the new crossing fixture, whereas its modern
writer already rounds to 400 mm; the test now preserves each existing behavior.

The first native harness call incorrectly passed `None` as initial saturation;
WEPP rejected that harness-generated header. Corrected the harness to retain
0.75. The next comparison incorrectly demanded identical provenance comments;
changed the assertion to exact model records while retaining distinct source
hashes. Final v4 additionally validates complete WAT calendars and source-code
identities. Failed scratch roots/logs remain available; no production input or
historical study artifact was rewritten.

The first Roads gate reached a provenance assertion while its already-imported
source-hashing code predated the new dependency-hash update. A fresh focused
publication check passed; a fresh complete Roads gate passed **530 tests, 5 skipped** against the
final source-hashing implementation. Historical publication evidence remains
explicitly stale rather than relabeled as newly executed evidence.

## Broad-suite continuation

The first broad run passed 5,314 cases and skipped 54 before finding the same
old horizon-count expectation in the developer-mode artifact test. Its corrected
assertions now require 100/200/500/800 mm and the copied assigned anisotropy value.
No production change was needed. A fresh collection contains 11,568 node IDs;
the failing case is at offset 5,367 (5,314 passed plus 53 runtime skips before it;
the remaining skip was collection-time). The response-file continuation starts
with that exact failing node and includes all 6,201 remaining nodes, including
new direct-writer tests added after the initial broad collection. Exact node lists
are retained in the final scratch root; hashes and exact partition checks are recorded in
[coverage-continuation.json](coverage-continuation.json). The continuation passed
5,962 tests and skipped 239; it includes all 13 later-added direct-writer/SSURGO
tests. There are no unresolved failures or uncovered deselections.
