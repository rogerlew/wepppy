# Corrected ET caller scope: scientific execution prereview

Status: approved for the exact corrected freeze below and its three-history budget, subject to independent implementation approval and all existing parity/support gates. This supersedes execution approval for the failed first build; that build and earlier review remain retained. No model history has yet been invoked, and this reviewer performed no compilation or native execution.

The sole prepared source difference replaces the invalid caller reference to routine-local ET with a reserved zero in FX_ET_POST. Reader v4 checks that slot equals zero and compares only the four shared return quantities: EP, ES, ERES and RESINT. Method and call ordering checks remain. The internal REQUEST/RETURN records still preserve initialized routine-local ET. It is not inferred at the caller or interpreted as final accepted daily extraction.

Scientific ET/residue, uptake, profile-delta and precision equations are unchanged. The new runner selects prepared-v3, reader v4 and a fresh campaign-v2. Reader-controls-v5 passes fourteen malformed cases, four nonzero arithmetic checks and the retained coordinate/interception flag checks. Exact source/input/output/frost-trace/old-BPO parity and observed supported-call coverage remain mandatory. No physical correction, additional scenario or tolerance change is authorized.

Directly verified 36 current authored/prepared/tool/runtime file bindings against this freeze. Prior accepted build and trace bindings retain the earlier review scope; the runner performs full verification.

## Exact bindings

- `freeze.json`: `b64ef3722da2e5909858a4c48e3bce895564739940fb56b3ec910ff7b542478e`.
- `read_flux_v4.py`: `475ea461e1767f6cdc79a6cbdf9bcb440b9ca6d34d7ab8dffa8815a4ca911fa1`.
- `run_flux_v2.py`: `83994e666a15dcf9edfc7f6a66a3faa77417e8f57e5ba706da8024ecb1eed60e`.
- `ownership-contract.md`: `dbd0df98e3f88242553589f9f2c829f240365ffb98ba31452e6a8265264a2abd`.
- `declaration.md`: `a9b1cb1c78bdd9e24984241c49625c8502e388a62496ea045b475b5c92614440`.
- `prepared-v3/source-bindings.json`: `fa10e69286bdb6a583ca08443cc8e1062de581b9b21b67223609b92843af4028`.
- `reader-controls-v5/receipt.json`: `da2513d3a4bab73433cbba6fb50d4a5f693ca4644e31e9ea9cca04c85d81b439`.

Writer status: clear.
