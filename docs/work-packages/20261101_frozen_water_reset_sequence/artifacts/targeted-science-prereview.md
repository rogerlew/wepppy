# Existing diagnostic-window reuse: scientific execution prereview

Status: approved for the exact three-history declaration bound below, subject to independent implementation approval and all parity/coverage gates. No new native source, compilation or model invocation was performed by this reviewer.

The selected windows are fixed by the completed census: zero and normal year 3 day 20, high year 7 day 344, plus each preceding day. The existing bpactive selector in the accepted binary supports precisely these two-day windows. Reusing it is an appropriate bounded way to narrow the writer gap before adding instrumentation. The marker change must be the sole runtime-input difference; seven ordinary outputs and the entire FRWATC trace must remain byte-identical to the accepted counterpart.

Source review of the bound existing observer confirms the three stages surround allocation/percolation and then the composite post-percolation water balance. BEFORE occurs after allocation operands are computed but before their layer assignments; PURK occurs immediately after percolation; AFTER occurs after ET, redistribution, drainage and surface overflow. ET is called only on the final hourly step, but the AFTER interval does not isolate it. The observed zero-ST producer must not be named from a coarse stage difference alone.

Water stage columns are ST, UL, FRZW, THETDR, DG and cumulative depth. ST is available storage; FRZW is a dry-reference coordinate. Profile absolute stock can be reconstructed as sum(ST+FRZW+THETDR*DG) where clocks/support are coherent. If liquid and ice are separated, frozen support from the companion K records or another synchronized observation is required; the compact reader currently retains only W stages. Keep original K records available in the raw log.

ALLOC operands are hourly allocated infiltration, fin, subrin, upstream/cell hourly runoff and routed return. SEEP records sep and remaining hrfin. FLUX/RETURN include hourly and cumulative quantities, with overlap. Their names alone do not establish accepted external fluxes or time normalization; consult the executed source and avoid summing redundant/cumulative columns. A zero stage delta cannot rule out offsetting internal writers. The 144 required hour/OFE/day profiles with all ten layers and all three stages establish window coverage, not a closed flux budget.

The three fixed full histories, unchanged accepted binary, exact input comparison, bounded process time, complete finite stage/operand coverage, preserved failure receipts and full trace/output parity are sufficient scientific gates for this observational extension. No adaptive scenario selection, parameter change, annual-loss estimate or behavioral ablation is approved.

## Exact bindings

- `targeted-freeze.json`: `9f333b9e4d8d90161fbc2b3f97a57ea17fbf2c4e42439ab5bb6f147467261769`.
- `targeted-declaration.md`: `eac3af9c29f6cfd19f3ddb982b9c0a98f240584a85c0b891e96b27a4796025ed`.
- `run_targeted_histories.py`: `afb0a04aaf3427bf3e67d07c98af399855392d43e97105a8efbeda462683ee12`.
- Accepted build `contin.for`: `4e419620fb1fd5203c2d532a4fa61b9b97349bfd35f4f8c215373e5226238604`.
- Accepted build `watbal_hourly.for`: `dbfeed35c303c54037d130bc62852b59fcd76946e62addc30ff5ed5910abf986`.

All frozen file/runtime dependencies were verified. Writer status: clear.

## Pre-execution provenance amendment

Approved current second freeze below. The reviewed diff adds PATH/FC and stdout/stderr/BPO hashes to receipts and binds the malformed-reader control source. Three targets, binary, inputs, stage interpretation and scientific gates are unchanged. All current frozen file/runtime hashes verified. The retained reader controls cover 144 valid hourly profiles and reject duplicate/missing layers, missing flux records, nonfinite values and wrong clocks. No targeted model invocation preceded this review.

- `targeted-freeze.json`: `dff5f3ce894e95b9fdde700ed5c0b2c5a00d2b1834b13fc404267e413ebeb61c`.
- `run_targeted_histories.py`: `b9c67d7c0b5f2ac276db71100cd9971865ce665058a6f6e158d88cc6882c745e`.
- `check_targeted_reader.py`: `b62199983f3355a36cfa25e11c6da9e24db55aedc3cef425482b2f7adeff0b67`.
- `targeted-reader-controls/receipt.json`: `1c9470a6b4d72761c3e0c5713cf18c3979c29a75c3903be1745d691ac262ad48`.
