# First completed flux window and supplemental reader review

The completed zero-rock window supports identifying EVAPPM as the executed owner of the selected final-hour coarse depletion. At year 3/day 19/OFE 1/hour 24, reported request is 2.245685551 mm, unmet amount is 1.377727138 mm and returned ES is 0.867958413 mm. Residue is zero; returned ES exactly equals the independently observed profile ST reduction. Later capacity, drain, lateral and surface stages change no profile stock. The actual uptake decision has EP/root depth zero, no SWU call and unchanged stocks. This resolves the selected routine/accepted-removal question; it does not establish an annual or universal water budget.

An independent raw-log parser reproduced all 720 hourly stage comparisons exactly, matched their emitted W/K stages and daily uptake operands, and verified the selected interpretation without importing the production reader. The retained flags distinguish negative relative FRZW from absolute ice: no negative absolute ice was found in the six independently inspected hourly stages. The reader's 24 flagged hours and one flagged day contain only negative relative-coordinate flags, not negative physical ice or changed-support findings.

Supplemental read_flux_v5.py is scientifically appropriate. Its only parsing change accepts the existing BP_IRS_ENTER/OFE0/index0 global-context record on valid window dates. That record remains in exact legacy-BPO parity, outside layer and flux populations. New FX records and hourly/daily support remain restricted to OFE1–3. The separate reread_flux.py validates completed native histories, ordinary-output/frost/legacy-BPO parity and unchanged original campaign/dependencies, and writes a fresh readback destination without model execution. Actual corrected high readback and the remaining scenarios require separate review when complete.

## Bindings

- `zero observations`: `eb453d0bb8e15d2399fb215c42383bfb02bdd28687b40afef0fab3f60d84ab2d`.
- `independent raw checker`: `a6e614196a24ebd264e0a2b3c60418fcf9e4ec4a664924ceb4eccec7f52993f3`.
- `independent zero receipt`: `352248f27db3ca0921b87c2fdb886def61a795463677466718d6b5b01517a0b6`.
- `read_flux_v5.py`: `c0793beae8ec7f3653544fb1d2c1d62fff77b50cfd068379d95e7a56c559480c`.
- `reread_flux.py`: `78bef2d3020bf60b2384100271743564158221c0686de0da37de65c8abf9e41f`.

Writer status: clear. No model invocation or frozen evidence modification.
