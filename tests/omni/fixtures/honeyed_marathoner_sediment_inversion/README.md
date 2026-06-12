# Honeyed Marathoner Sediment Inversion Fixture

These fixtures preserve the three hillslopes from
`/wc1/runs/ho/honeyed-marathoner` on `wepp1` where the unburned OMNI
`undisturbed` scenario produced trace annual sediment while the burned
`sbs_map` base scenario produced zero sediment.

## Contents

The copied files live below `run_root/` and keep the production-relative WEPP
layout:

```text
run_root/
  wepp/
    runs/p118.*
    runs/p122.*
    runs/p264.*
    output/H118.*
    output/H122.*
    output/H264.*
  _pups/omni/scenarios/undisturbed/wepp/
    runs/p118.*
    runs/p122.*
    runs/p264.*
    output/H118.*
    output/H122.*
    output/H264.*
```

The burned base scenario contains the shared `.slp` and `.cli` files. The
unburned `.run` files intentionally reference those files by relative paths,
matching the original production run:

```text
../../../../../../wepp/runs/p<ID>.slp
../../../../../../wepp/runs/p<ID>.cli
```

The copied `.err` files record the WEPP runner binary used for both burned and
unburned runs:

```text
/workdir/wepppy/wepp_runner/bin/wepp_dcc52a6_hill
```

The binary identity lines record SHA-256
`365d44d643f70c5eee54e0ea81e74a125003799df8c912bab9ff267c476308a8`. The
copied `loss.dat` outputs report WEPP model version `2020.500`.

## Hillslopes

| WEPP ID | Base scenario | OMNI scenario | Notes |
| --- | --- | --- | --- |
| 118 | `sbs_map` root `wepp/` | `undisturbed` | Trace unburned sediment on `1992-06-16` |
| 122 | `sbs_map` root `wepp/` | `undisturbed` | Trace unburned sediment on `1992-06-16` |
| 264 | `sbs_map` root `wepp/` | `undisturbed` | Largest inversion, still only `61.179 kg` annual average |

## Verification

The fixture is exercised by:

```text
tests/omni/test_honeyed_marathoner_sediment_inversion_fixture.py
```

That test parses the copied WEPP outputs and asserts the event-level behavior
that motivated the fixture.
