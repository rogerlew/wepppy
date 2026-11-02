# Python MOFE input producer audit

Date: 2026-11-02 19:35 UTC. Scope: read-only audit of WEPPpy inputs other than
management/PMET, which have a separate audit. No production files, native binaries,
or active rock/water test inputs were changed. Findings below are source-level;
none establishes a measured native-output consequence.

## Confirmed source-level findings

### MOFE-SOIL-01: first-OFE land use controls every kslast override

Priority: high. `wepppy/wepp/soils/utils/wepp_soil_util.py:493–511`
(`modify_kslast`) reads `obj['ofes'][0]['luse']` and returns for a developed
land use, otherwise writes the override to every OFE. MOFE staging calls this
method in `wepppy/nodb/core/wepp.py:742–743`.

For a mixed developed/forest profile, the first OFE decides whether the forest
override is suppressed or the developed OFE loses its existing exemption.
An AST-extracted execution of the actual method with initial values `[1, 2]`
and requested value `99` gives:

| OFE order | Result |
| --- | --- |
| developed high, forest | 1, 2 |
| forest, developed high | 99, 99 |

Smallest repair: apply the existing exemption per OFE while preserving explicit
`preserve_input_format` behavior. Resolve the legacy top-level `res_lyr` alias
without allowing it to overwrite an exempt OFE. Acceptance must read actual
prepared soil files in both orders, with distinct original values and a
preservation-mode control. The probe does not exercise parsing or serialization.

### MOFE-COVER-01: lexical cover-block order at ten or more OFEs

Priority: high. `wepppy/nodb/mods/rap/rap_ts.py:163` reconstructs MOFE identities
as strings. Both `prep_cover` at line 361 and `_prep_transformed_cover` at line
435 sort those strings without numeric conversion. With twelve OFEs the order
is `1,10,11,12,2,3,4,5,6,7,8,9`. The soil producer explicitly orders numeric IDs
in `wepppy/nodb/mods/disturbed/disturbed.py:2270`.

Smallest repair: numeric OFE ordering in both cover writers, plus verification
of the expected complete OFE identity set. Acceptance should use at least twelve
distinct cover blocks and compare actual `.cov` block identity with `.slp`,
`.sol`, and `.man`, including the transformed-cover path. Observe consumption
with the correct 9005/revegetation binary before claiming native output impact.
Only source inspection and a Python sort demonstration were performed here.

### MOFE-SOIL-02: first-OFE texture enum copied into all 9005 headers

Priority: medium. The per-OFE 9005 writer at
`wepppy/wepp/soils/utils/wepp_soil_util.py:748` uses
`self.simple_texture_enum`. That property at lines 1345–1348 calls `self.clay`
and `self.sand`, which read OFE 0's first horizon at lines 1272 and 1261.
Different OFE textures therefore receive the first OFE's enum, even though
their individual `stext` values are retained. Debug serialization repeats the
selection at line 863.

Smallest repair: derive the enum from the current OFE, or preserve admitted
explicit values where required by the upload contract. Acceptance should read
back two different textures in both OFE orders through the actual writer and
the matching native consumer. Explicitly distinguish preservation mode.

The audited `/workdir/wepp-forest/src/input.for:471–473` reads the older
five-field `>=9003` header. It is not sufficient evidence of 9005-specific enum
consumption; bind the intended binary/source before native validation.

## Boundary risks requiring reproduction

`prep_multi_ofe_hillslope` publishes slope, soil and management separately
(`wepp.py:720–778`) without a visible cross-file OFE count/order check.
`SoilMultipleOfeSynth.write` declares `len(stack)` but appends all source OFE
records without asserting that each source contains exactly one OFE
(`wepppy/wepp/soils/utils/multi_ofe.py:69–87`). Current callers generally pass
single-OFE sources. These are validation gaps, not demonstrated malformed
production runs. Add stale/mismatched source fixtures and a multi-OFE stack
element negative control before deciding whether a repair is required.

## Coverage and limits

Inspected general MOFE staging; slope clipping; soil initial saturation, depth,
anisotropy and kslast mutations; single-input replication; Disturbed soil stack
ordering; Roads routed soil selection; hillslope climate/run controls; RAP cover;
and frost, snow, baseflow and phosphorus preparation.

No first-OFE defect was found in slope clipping, initial saturation, depth or
anisotropy loops. Disturbed soil ordering is numeric. Roads explicitly selects
and reorders scenario OFEs; its two-line parser uses controlled templates.
Climate is shared per hillslope. Run-wide sidecars were not misclassified as
per-OFE gaps without an applicable per-OFE contract.

Not exercised: complete application/native histories, all specialized producers,
all treatment and archive/mixed-source transitions, actual 9005 consumer
execution, or output consequences. No broad test suite was run.

## Reproduction and source binding

Run from the repository root:

```bash
python3 docs/work-packages/20261102_mofe_input_producer_audit/artifacts/reproduce_python_inputs_audit.py
```

The probe compiles only the actual `modify_kslast` AST into a minimal namespace,
uses synthetic two-OFE objects, prints results and the current source hash, and
writes no files. It also demonstrates string sorting; it does not execute the
RAP writer. It intentionally reports observations rather than treating buggy
behavior as a permanent passing test contract.

Source SHA256 at audit time:

| Repository-relative source | SHA256 |
| --- | --- |
| `wepppy/wepp/soils/utils/wepp_soil_util.py` | `9d6babff56f8d6e9e87c4a6abc3b48b9e9e55f98f91c532e0018bf73e1667d17` |
| `wepppy/nodb/mods/rap/rap_ts.py` | `4bcbf71464ffab30fc8c4e22b4783b90adedae5f986f47b3a624cd94a2e41cab` |
| `wepppy/nodb/core/wepp.py` | `852481db0fd89fec25bebcaa426ab1e4b35420ab778eadfe863a4df5d1c1e71e` |
| `wepppy/wepp/soils/utils/multi_ofe.py` | `774beb06c21a8142ec2c339090ffd875eecf5bfab2beec6ec43c88c9826893d3` |
| `wepppy/nodb/mods/disturbed/disturbed.py` | `fb6128da54d5d7bb3109cba1ffa837aacd4a218e408834f8f9d32b20fcd41cd5` |
