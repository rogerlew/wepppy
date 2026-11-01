# Targeted hourly windows: independent scientific readback

Accepted as three parity-preserving diagnostic windows. Completed receipts report identical seven ordinary outputs and complete FRWATC traces. Independently parsed each raw BPO log and matched all 144 retained hourly profiles/operand records per case. This review identifies the composite interval that sets top ST to zero; it does not claim a separately observed ET call or a closed external-flux budget.

For zero and normal, top ST is unchanged across allocation/PURK on all 24 hours of the predecessor day. Only hour 24 changes it after PURK, from 0.867958413 and 1.152466401 mm respectively to zero. Zero has zero recorded allocation/seepage/surface/lateral operands. Normal has nonzero deep seepage in the PURK interval: hour-24 profile ST change is about -0.007905066 mm versus recorded SEP 0.007904445 mm. That is separate from its post-PURK top drop and must not be assigned to that drop or counted again from the overlapping FLUX record.

High differs materially. On predecessor day 343, allocated input is about 0.033333334 mm each hour (daily fin about 0.8 mm); top ST increases by about 0.016666716 mm across allocation/PURK each hour. Hour 24 then reduces top ST from 1.424178132 mm to zero in the composite post-PURK interval. Recorded seepage is nonzero, with zero recorded surface/lateral outflow. The zero/normal no-input premise does not apply to high. The initial checker retained that premise and failed on high; separate v2 extraction records the observed differences without changing model evidence.

Reported daily Es is 0.87, 1.15 and 1.42 mm, with Ep zero. Those rounded values are consistent with the observed post-PURK profile drops. Coupled with source timing, they support soil evaporation as the candidate explanation, but rounded daily output and composite stage boundaries do not independently establish accepted per-call ET or exclude every compensating internal action.

For selected clear/reset pairs 1576→1581, 1591→1596 and 5243→5247, YST and fine aggregate stocks are unchanged between clear POST and reset PRE. Cleared NW plus subsequent fine removal reconciles the net coarse ST drop with residuals approximately -1.87e-13, +2.11e-11 and +2.47e-12 m. This is a specific sequence stock identity, not causal restoration or annual water loss. In high, net coarse endpoint drop is 1.024176949 mm, while the hour-24 post-PURK removal is 1.424178132 mm because the intervening top input is about 0.400001183 mm. Confusing endpoint change with gross removal would omit that input.

These observations narrow the producer gap to the final-hour composite interval and explain why an inherited reset residual can persist without an erroneous reset assignment. No reset repair, invented sink, global capacity multiplier or annual discrepancy sum follows. Individual accepted ET and other internal writer attribution remain limited by the existing observer.

## Bindings

- `scientific-targeted-v1/check.py`: `345d6bb950d1fa25e67eedd07b17a29a5e35b7ef9382b034603b07d406a803d7`.
- `scientific-targeted-v1/check_v2.py`: `b381fdb98b7f542ccae6ecdeb9c87796d24766ecba157329cabe73ad6197c388`.
- `scientific-targeted-v1/zero-ks1.json`: `4447ad03a3d7f0b5881344f1097970881fa941b3e6c0039a8afe8fe1baed9a03`.
- `scientific-targeted-v1/normal-ks1.json`: `f3ddc4e5ded5695a20b32f8e0a5ea08cb9604286104845779528b00274e187fb`.
- `scientific-targeted-v1/high-ks1-v2.json`: `d31206d95c5cae1bdcf910dd6426245054f0ffbecefa795d2ea16dbffb2fbb04`.
- `targeted-v1/zero-ks1/readback.json`: `9c32fcd789443270e98012abd9e8aa1a7f2f0c38e6016afe327acc1e8e0c8204`.
- `targeted-v1/normal-ks1/readback.json`: `70a3519095b0e6a7fa97985f56b5c24785e15f17ce6a9e395b20a6ed4ba40ecf`.
- `targeted-v1/high-ks1/readback.json`: `4e1d9c92eeb73a427a2396f4496aa9c3ee4905b49af4126f3b5107ac8098a120`.

Writer status: clear. No additional model execution or frozen-evidence edits.
