# Completed controls: independent scientific readback

Accepted for the declared observation study. Independently read all 29 completed synthetic traces (52 map transfers), recomputed six fine/coarse stock quantities directly from C/F records without importing the campaign reader, and compared every before/after quantity with emitted transfers. Differences were below 1e-16 m. Independently verified all 29 ordinary stdout hashes against the previous fixtures and all trace hashes against retained readback. The runner also passed its independent previous STATE/FINE comparison. These checks validate observation arithmetic and parity; they do not establish general model conservation.

All five required signatures occur in their intended positive controls. F-low omits approximately 0.270 mm from the coarse representation while fine stock is unchanged. G-low leaves its approximately 0.020 mm request absent from fine storage and subsequently exhibits the separate F discrepancy; those are distinct mapping comparisons, not additive annual fluxes. H-low clears approximately 0.050 mm from NWFRZZ after coarse mapping includes it. Its first coarse-after/fine-before residual is only roundoff, while fine stock decreases: the two diagnostics must remain separate. I-small and I-middle retain actual ignored requests of approximately 5.02914e-8 m and 4.99189e-7 m. Signature absence elsewhere is bounded by available initialized support and observed branch coverage.

The only finished pair included in this review is zero-ks0. Independently verified its seven output hashes and parity, then streamed its completed trace: all 17,532 unique expected daily gates, zero actual frost calls, zero mappings and 84,331 weather opportunities. The latter are not frost calls. This is an observed inactive control, not evidence that threshold behavior cannot occur under enabled conditions. No unfinished trace was read. Remaining histories require separate final review.

H ownership remains unresolved beyond the synthetic endpoints. No external water-loss estimate, drainage attribution, causal restoration, parameter change or production repair follows from these results.

## Evidence bindings

- `campaign-v1/controls/receipt.json`: `50fa8b75f5173cd9c9b326e628a00ed2b85733297be2e2e96cf57e09ad7b6e54`.
- `campaign-v1/zero-ks0/receipt.json`: `3e1967b69ce4d68f7cb2cec731852cf4d634b4714f5346fb693ef15563ddb55b`.
- `scientific-readback-v1/check_controls.py`: `a80aef2c643eaaeeb01555137ad33a4d5d51adb3a87c590f65244cf64f44b329`.
- `scientific-readback-v1/receipt.json`: `f38da979122d66a6501e472da96610f1d8f4544adb9ac8b4695bde5379134668`.

Writers clear. No model rerun, build, native source mutation or prior-evidence mutation.
