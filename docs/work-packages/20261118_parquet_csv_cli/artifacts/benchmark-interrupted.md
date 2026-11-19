# Interrupted measurement and disposition

The first benchmark of release SHA-256
`2efd194f5842f668687b58659337598b5d3b868151fc12f0d3b837b9313a8b37`
completed three H.wat samples and two chnwb samples, then a chnwb worker returned
exit 1. `benchmark-interrupted.jsonl` retains the completed records. The original
runner captured stderr but raised CalledProcessError without retaining it, so
there is no evidence of that worker's exact failure code or cause. Immediate
single-worker replay passed. A second full benchmark and 100 repeated conversions
also passed with the earlier harness. These are diagnostic reruns, not proof that
the original failure was harmless or understood.

The runner now writes a bounded `failure.json` before raising on a failed worker.
During investigation, the security reviewer directly demonstrated that reading an
already-open /proc child stat descriptor after child exit raises ProcessLookupError.
The harness had handled only FileNotFoundError. This independently confirmed race
is fixed; a real child open/exit/read regression covers it, and other observation
errors remain fail-closed. Do not claim this was the proven cause of the original
benchmark failure. SEC-07 and the correctness amendment retain the distinction.

The final benchmark contains nine successful samples with the corrected harness;
final lifecycle/readback and canonical test receipts identify the accepted build.
The earlier interrupted sample set is excluded from median acceptance calculations
and is not silently erased. No reliability rate or exhaustive race-coverage claim
is supported by these finite runs.
