# r7 retention observer outcome

Independent reviewer: `mipa_contract_scope`. Review date: 2026-11-02.

**PASS for retained observer parity, initialization inventory, and the bounded
initialized FC/UL domain readback.** Optional retention reaches the initialized
native state in B2/B3 at layers inside the emitted 1600 mm profile. This is not a
release, default-change, frozen-consumer, drainage-domain, or water-closure
acceptance. The reviewer made zero native calls.

## Evidence and reproduction

- [Read-only helper](read_r7_retention_observer.py), SHA-256
  `779fae9b96c98bc1659089161756132f4535374d6cbabd67a93a7f321cf21d98`.
- [Machine readback](resumption-r7-retention-observer-outcome.json), SHA-256
  `35e5fda0405eafd6205d2466fdaca143b279ea518e5667a0dd9058d3dff4afa0`.
- Native root:
  `/wc1/runs/ro/roads-parameterization-program-20261103/retention-native-v1`.
  Its `results.json` SHA-256 is
  `e4c1e59db6a661b83214b289bcdf9e3a735f51631ef9792db81a6fc5ca455fdc`;
  declared execution SHA-256 is
  `631e70e5ddbe6573bd694c18c900b798d621b4c138fd93ed31f591511425e814`.
- [Independent layer map](resumption-r7-retention-initial-layer-map.json),
  SHA-256 `5dcc0c68d3dd4213c1ae1cbc5bf7b18393318f962b2dde80f1d3b6f329c653c7`,
  and [map review](resumption-r7-retention-initial-layer-review.md), SHA-256
  `05908301a7110aadf5450906ca3880b8d9a7a408927463896088f210220dbebc`.
- Source semantics use the map's eleven bound native units and `winter.for`
  SHA-256 `6dca46e762611ddd93e030d7fcc619af92922d614a4ddc1c44576b90ee9d86ff`.
  The latter was independently byte-matched to source commit
  `e0abe0581f77c6f66917e90daf8f8f429e9315c8` before interpretation.

The helper requires a fresh output destination. Reproduce with
`python3 docs/work-packages/20261029_roads_parameterization_program/artifacts/read_r7_retention_observer.py --output /tmp/retention-observer-readback.json`.
It verifies the declared execution/review receipts, source and preparation
bindings, archived inputs and logs, case identities, retained result receipts,
ordinary scientific gates, seven raw output hashes, and marker-only replica
inputs. **All eight replica pairs must pass before any trace is parsed.**
It checks the resulting evidence hashes again before writing its result.
The machine artifact retains original selected lines and tokens, full tag
counters, per-layer comparisons, trace byte counts and hashes, and file bindings.

## Parity, inventory, and precision

All eight ordinary runs pass their retained physical, particle, and pass-file
completeness gates. All eight corresponding observer runs preserve all seven
ordinary outputs exactly: 56 pairwise output comparisons, independently
rehashing 112 output files. This parity compares each marked replica with its
own ordinary arm, not default policy with optional policy.

All 408 expected selected rows are present exactly once: 204 `WBH_HK_FCUL` and
204 `WBH_HK_RATIO` rows. For every arm, owners are OFEs `e=1,2,3`, `c=0`, with
`s=1..10` in B2/B3/B5 and `s=1..4` in B4. Both tags use initialization
`y=0,d=0`; this is not daily climate coverage. No duplicate, missing, unexpected,
or malformed rows were found. The ratio row's second payload is always zero.

The original `1pe12.4` output has five significant digits. The JSON preserves
those tokens; its deltas are differences of printed numbers, not exact binary32
state. Half-quantum intervals describe output rounding, not a fitted acceptance
tolerance. Every reported changed field has disjoint print intervals between
arms. An unchanged token establishes equality only at this printed precision.

Across all 204 pairs, FC and UL are finite and positive. All ratios are positive,
with the logarithm's singularity at one excluded at printed precision. The
separate stricter screen `0 < FC < UL` and `0 < FC/UL < 1` also passes. Printed
ratios span `1.5007E-01` to `5.2925E-01`. This does not claim that existing native
guards enforce that stricter screen. FC and UL are meters of water above the
native dry reference, not serialized volumetric FC and porosity.

## Paired initialized changes

Depths below come from the independently bound source map, not observed DG.
Both top layers, `s1=0–100 mm` and `s2=100–200 mm`, use the same averaged
`0–200 mm` material properties. They must not be interpreted as independent
100 mm source averages. Each count below includes all three OFEs.

| Case / source | Changed layers within emitted profile | Changed native extension | Unchanged layers |
| --- | ---: | ---: | --- |
| B2 / 1718494 | 12: s6–9 in each OFE | 3: s10 | s1–5 |
| B3 / 1718494 | 12: s6–9 in each OFE | 3: s10 | s1–5 |
| B4 / 1718465 | 9: s1–3 in each OFE | 3: s4 | None |
| B5 / 2711184 | 24: s1–8 in each OFE | 0 | s9–10 |

**B2/B3's primary witnesses are s7–9**, covering 1000–1600 mm, wholly inside the
emitted profile and the changed 990–1600 mm source horizon. All three OFEs and
both cases have the following printed values at each of these three layers:

| Observed quantity | Default token | Optional token |
| --- | --- | --- |
| FC (m) | `1.9022E-02` | `1.8004E-02` |
| UL (m) | `6.9526E-02` | `7.0359E-02` |
| FC/UL | `2.7359E-01` | `2.5589E-01` |

Layer s6, 800–1000 mm, also changes; only its last 10 mm intersects that changed
source horizon. Layer s10, 1600–1800 mm, has the same printed deeper response,
but it is a native-added extension and is counted separately. Unchanged upper
CPM=1 material therefore did not exclude a deeper initialization response.

B4 changes all initialized layers, including its separate 400–600 mm native
extension. Its direction is not uniform: the upper averaged material has lower
FC and ratio, while s3–4 have higher FC and ratio. B5 changes s1–8 and leaves
s9–10 unchanged at printed precision; the latter include its unchanged deep
fallback and the native extension. No case has a changed initialized layer
without changed FC/WP input support in the source map.

These are same-fresh-source default/optional comparisons. The independently
reviewed preparation established exact frozen default semantics for B2/B3/B4.
B5's separately reported fresh deep-fallback vintage drift remains distinct
from the optional-policy effect; this observer readback does not reclassify it.

## Guard semantics and retained traces

Every tag is counted; explicit guard summaries include `_G_`, `GUAR`, `BAD`, and
`WARN` matches. There are no `WBH_G_HKDOM`, other `_G_`, `BAD`, or `WARN` rows.
There are 47,456 `WFR_SUM_GUAR` rows, all with both payloads zero. In bound
`winter.for:403`, this tag is emitted unconditionally at hour 24 and summarizes
near-zero `qoutdm` and frost/thaw boundary counts. Its occurrence is not itself
a fatal event.

The corresponding `WFR_SUM_CALL` counters report 468,996 frost-condition
opportunities and exactly 468,996 KSFLAG skips across all eight traces. These
are opportunities, not calls that reached `frostN`. Thus the zero guard
summaries provide no exercised frozen-consumer domain evidence. The source
warning threshold was not reached, and no summary warning tag was emitted.

All raw traces remain at
`<native-root>/cases/observed/<arm>/<case>/runs/wepp_observe.log`.
Their complete hashes are in the JSON; the short prefixes here identify them.
The retained total is 91,202,726 bytes and 1,146,577 lines.

| Case / arm | Bytes | Lines | Selected rows | Guard-summary rows | SHA-256 prefix |
| --- | ---: | ---: | ---: | ---: | --- |
| B2 default | 15,236,838 | 189,241 | 60 | 9,876 | `ad97a8ce9c45` |
| B2 optional | 15,236,838 | 189,241 | 60 | 9,876 | `2e0d045e3956` |
| B3 default | 10,067,655 | 126,219 | 60 | 7,448 | `0dbb2f7a57fa` |
| B3 optional | 10,067,655 | 126,219 | 60 | 7,448 | `bdd3f1fec08b` |
| B4 default | 10,107,520 | 128,379 | 24 | 3,202 | `88fd096a205b` |
| B4 optional | 10,215,034 | 129,774 | 24 | 3,202 | `27058bd32454` |
| B5 default | 10,085,566 | 128,104 | 60 | 3,202 | `1912f51f4f73` |
| B5 optional | 10,185,620 | 129,400 | 60 | 3,202 | `82f8b21c9c31` |

## Limits and validation

The [whole-soil capacity contract](../../../schemas/whole-soil-water-capacity-contract.md#native-consumer-domains)
requires distinctions this readback preserves. The selected trace observes
initialized FC, UL, and their ratio before the log expression. It does not
observe stored HK, dynamic PERC operands, UL−DRFC, porosity, dry reference, or
actual layer thickness. It cannot establish frozen/unfrozen consumer coverage,
unique drainage/ET causality, pore-capacity validity, thermal closure, or a
whole-system water balance. Layer-depth support is source-derived. General
native/release holds and withheld-source boundaries remain unchanged.

Validation: the full retained-data reader passed. Offline parser checks passed
for exact initialization keys and hashes, duplicate and malformed-row rejection,
and zero/nonzero guard-summary distinction. An initial unissued reader result,
before explicitly summarizing abbreviated `GUAR` tags, is preserved at
`/tmp/resumption-r7-retention-observer-outcome-initial-20261102.json`; it is not
the issued evidence artifact. No native output, frozen review, or execution
declaration was changed.
