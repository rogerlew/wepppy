# Paired retention native staging review

Date: 2026-11-03 UTC. Independent reviewer: `mipa_contract_scope`.

**PASS for the concrete staged declaration.** The installed-container readback
matches the selected 16-call design and the independently reviewed preparation.
No declaration or native call was made by this reviewer. Execution still requires
the separate reviewed-declaration receipt; initialized-layer and scientific
outcome claims remain unapproved.

## Bound evidence

| Artifact | SHA256 |
| --- | --- |
| Native declaration | `631e70e5ddbe6573bd694c18c900b798d621b4c138fd93ed31f591511425e814` |
| Preparation result | `e24ade55e77907dc75ebc4d4e45378d53cf48483ec86366991830cec6f1e68ab` |
| Independent preparation outcome readback | `fd835f0e92752175e6c159376e3cbdafbaf2dba5f8fd51cada1ce36bd924b138` |
| [This staging readback JSON](resumption-r7-retention-native-staging-review.json) | `294951e6ba76d363d898e6b7fa0398f32e995623ea2576ab73cb1fe5ccb40329` |

Native declaration root:
`/wc1/runs/ro/roads-parameterization-program-20261103/retention-native-v1`.
Actual staged execution root inside `weppcloud`:
`/tmp/roads-retention-native-v1`.

## Verified staging

- Exactly eight ordinary and eight observed tasks, covering B2/B3/B4/B5 and
  default/optional once in each mode. Case, stratum, role order and all eleven
  non-soil native inputs plus auxiliary `reference.sol` match preparation.
- All 83 dependencies, 91 reference bindings and 100 retained preparation
  bindings rehash successfully. Driver/protocol snapshots match their frozen
  hashes and the prior [implementation review](resumption-r7-retention-native-implementation-review.md).
- All 344 staged file bindings match. Each prepared case's complete soil and
  provenance tree is copied byte for byte. No staged symlink is present.
- All eight ordinary/observed pairs differ only by the empty regular
  `wepp_observe.on` marker. Frost markers, observer logs, stdout/stderr,
  native receipts and model outputs are absent. Output directories are empty.
- All 48 optional companions validate recursively at their actual local roots:
  eight source-v3, 24 treatment-v3, eight stack-v3 and eight stage-v3. Source
  companions bind the approved acquisition receipt. Default cases are unmarked
  and have no companions.
- UID/GID are 1000/993, concurrency is one, and timeout is 300 seconds.
  The executable has execute permission and SHA256
  `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`.
  It is the reviewed watershed r7 executable selected in hillslope mode.
- No execution-start, result, partial-result or failure artifact exists in the
  native root. Declaration and all bound files remained unchanged through
  the closing recheck.

## Scientific comparability readback

Actual staged soils were parsed with preserved 9002 hydraulic trailers.
Only main horizon FC/WP differ between default and optional; all seven trailer
fields remain unchanged. The differences exactly reproduce the independently
approved preparation outcome JSON.

| Case | Depth in each OFE, mm | Paired FC/WP field changes | Fresh-default semantic drift from frozen U12 |
| --- | ---: | ---: | --- |
| B2 | 1600 | 6 | None |
| B3 | 1600 | 6 | None |
| B4 | 400 | 18 | None |
| B5 | 1600 | 36 | Nine deep fallback field changes |

Every profile retains its complete frozen horizon-depth sequence and 200 mm
support. B2/B3's sole changed source row remains 990–1600 mm in each OFE:
default FC/WP 0.1851/0.0823 versus optional 0.1751/0.0778, at unchanged
density 1.5, K 100.8 and RFG 12.5%.

For B5, fresh default differs from frozen U12 only in the deepest row of each
OFE: FC 0.1880 to 0.1958, WP 0.0900 to 0.0815 and K 59.8734 to 21.3038.
That is a separate source/builder fallback change, shared by the paired arms.
It cannot be attributed to optional retention or called an unchanged frozen
baseline. The staged comparison preserves this distinction explicitly.

Semantic comparisons exclude comment/header provenance; they are not claims of
byte-identical rebuilt defaults. The independent initialization inventory,
native layer mapping, all 56 ordinary-output parity comparisons, physical gates
and target/control response review remain required after execution.
