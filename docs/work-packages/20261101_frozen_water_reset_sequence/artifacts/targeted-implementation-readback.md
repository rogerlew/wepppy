# Completed targeted-history implementation review

Disposition: **PASS for all three declared targeted histories.** No model rerun, compilation or raw write was performed by this reviewer. The twelve compiled controls are accepted separately in `control-implementation-readback.md`.

Independently reverified the exact approved targeted freeze and every actual file/library binding, including all 982 accepted build members and original runtime inputs. Each process completed normally with exit zero and the native completion marker. Actual stdout/stderr hashes match process receipts; command, executable hash, PATH and FC match the reviewed execution. The sole input change in each scenario is the declared observation marker, with exact selected year/day. All seventeen copied inputs remain unchanged after execution.

Every history has the full 17,532 unique daily water-balance keys and the declared 1,800 mm profile depth. Independently hashed all seven actual ordinary outputs and the entire FRWATC trace: each equals its previously accepted counterpart exactly. Thus retargeting the existing observation window preserves the accepted model outputs and full fine/coarse event trace in this finite panel.

Independently parsed each actual diagnostic log and matched its retained readback. All three contain exactly 144 unique two-day/OFE/hour groups, all ten layers at each of the three water stages, and all four declared allocation/flux operand records. Every parsed numeric payload is finite, clocks are correct, no required support is missing or duplicated, and complete record inventories agree. Diagnostic log hashes match the readbacks. This acceptance concerns the recorded stage data; composite boundaries do not identify an individual internal producer or establish annual loss.

Approved freeze SHA-256: `dff5f3ce894e95b9fdde700ed5c0b2c5a00d2b1834b13fc404267e413ebeb61c`. Completed panel receipt SHA-256: `6acd0e19f619ac8738bb0c7c5162f011f5717452ce7fb8adbd9de8fc9cb758b9`.

| Scenario | Readback SHA-256 | Diagnostic log SHA-256 |
| --- | --- | --- |
| zero-ks1 | `9c32fcd789443270e98012abd9e8aa1a7f2f0c38e6016afe327acc1e8e0c8204` | `55aa96d62c27f66c31469996cc35503c2dee5c0d0d2e1e617d26a64a1f284acb` |
| normal-ks1 | `70a3519095b0e6a7fa97985f56b5c24785e15f17ce6a9e395b20a6ed4ba40ecf` | `f8f8f159020229baca392db858a0a07da5a1b8b16f119b8311f75838e9c2fe94` |
| high-ks1 | `4e1d9c92eeb73a427a2396f4496aa9c3ee4905b49af4126f3b5107ac8098a120` | `63d3dce6a9ad071a909066ebfed2e78d7e9497d22a3763320f0e3564549f5d34` |

No implementation or evidence-integrity blocker prevents archival after all writers clear. Final archive inventory/member verification and publication/staged-byte checks remain the normal closure gates; this review does not pre-approve an uncreated archive. Reviewer writers are clear after scoped documentation lint.
