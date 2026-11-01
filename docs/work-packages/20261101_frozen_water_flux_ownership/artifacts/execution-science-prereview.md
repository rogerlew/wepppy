# Exact flux observer: scientific execution prereview

Status: approved for the exact three-history freeze below, subject to independent implementation approval and the declared execution/parity gates. No native build or model run was performed by this reviewer.

All four earlier scientific reader findings are resolved: absolute liquid/ice component checks are distinct from negative dry-relative coordinates; daily growth/uptake comparisons retain W/K support flags; unsupported interception and negative inferred uptake remain explicit; and each daily uptake interval follows its own final hourly state. Reader v3 additionally requires DFLUX after the completed drainage snapshot. The corrected contract uses the proper total-water coordinate and distinguishes double reconstruction, native REAL arithmetic and conditional threshold allowances.

The ET residue equations match the actual method: EVAP separates ERES, whereas EVAPPM leaves residue contribution within ES. Return EP is not automatically root uptake; the actual SWU decision and canopy correction govern that comparison. Missing calls are not guessed fluxes. Stage and method order, complete support and unchanged input/output/frost/legacy-BPO comparisons remain mandatory. Flags or outside-allowance comparisons must be retained as limitations/findings even when observer parity passes; comparison allowances do not establish physical closure.

The final controls retain 144 hourly and six daily groups, reject fourteen malformed cases, and pass four nonzero arithmetic checks plus coordinate/interception flag checks. The failed earlier control placement and superseded versions remain historical evidence. Runner validation failures now retain a failed readback before stopping. The declared scopes, windows and three-process budget have not changed.

Directly verified the current authored/prepared/tool/runtime bindings (32 files). The frozen 982-member base inventory agrees with the previously accepted build receipt, and each of the three scenarios binds seventeen accepted inputs. Existing large frozen traces remain bound through prior accepted hashes; this review did not rehash all old trace bytes. The runner must perform its complete dependency verification before execution and afterward.

## Exact bindings

- `freeze.json`: `925eb71538a22fddba99ee143e27607f245dbd4a328ad302681eca833cd1ae5f`.
- `ownership-contract.md`: `ea9b7c9f38937170514743abc6b2d16758d85f8c3099e070fae9ed4bcb8106fe`.
- `declaration.md`: `adc3dcd4369776e4920efea7a326402d1b0f5a3d3218f1628df313bf85c38f98`.
- `read_flux_v3.py`: `1dcdd8f05376b0059327bb84fbd280112dc0b24d808f6564a517b7ef8051320d`.
- `run_flux.py`: `490538d0455c5fef0aee826f1b476276b481836bf501475472d7cb4e00442eb8`.
- `check_flux_reader_v4.py`: `b25cdf59df89cc68e1d79cdf81a7c156b68ebbae6723482827d9874a3872dd25`.
- `reader-controls-v4/receipt.json`: `da2513d3a4bab73433cbba6fb50d4a5f693ca4644e31e9ea9cca04c85d81b439`.
- `prepared-v2/source-bindings.json`: `d373b146b12af3bf973516ea8aca94fd89a1fab6c5edb4dd141d0827db49e90a`.

Writer status: clear. No physical correction, added scenario, source publication or annual-budget claim is approved.
