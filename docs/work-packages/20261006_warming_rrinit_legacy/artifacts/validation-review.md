# Validation review of the original build comparison

## Execution and input isolation

The execution summary records 2,592 successful hillslope runs, three successful main watershed runs and one successful output-mode control. The seven canonical watershed output files are byte-identical between full hydrograph output and peak-only output at baseline roughness. All three main lanes contain 8,766 daily outlet records and 1,262,304 hydrograph samples, with no missing days. EBE and channel-ledger daily volumes agree exactly at printed precision.

The runner verified the exact input manifests against the corresponding corrected-build lanes before execution. All 1,885 eligible roughness tokens were parsed back in each changed lane; noneligible records were preserved. The original project's 5,201 input files match the frozen manifest. Release binary hashes and sidecars are retained in `evidence/`. The source audit covers 485 source/include/build files and resolves the build system's capacity-include swap without changing sources.

Post-execution checks passed: 865 successful terminal records per main lane, zero consumed-input hash mismatches, exactly 0/1,885/1,885 changed roughness tokens for 10/17/60 cm, all 98 output files from fourteen negative-control hillslopes identical across roughness lanes, and no stderr or warning lines. All 6,059 output hashes per lane were independently reread and matched. The binary hashes remain unchanged. Records are retained in `evidence/validation.json`, `evidence/output-hash-check.json` and `evidence/output-mode-parity.json`.

## Derived data and figures

Native PASS conversions each accept 7,573,824 records and native WAT conversions each accept 16,690,464 records, with zero rejected records. Fresh totalwatsed uses the original groundwater settings and the same daily calendar across all six cases. Streamflow equals runoff plus lateral flow plus baseflow. Matched PASS joins contain exactly 864 × 8,766 records. Both the original and corrected outlet series are finite and nonnegative; the full 600-second sample calendar is checked by the analysis parser.

Focused comparison tests pass for unchanged arrays, zero denominators, signed percentage differences and the management-token selector, including higher OFE indices. All research scripts compile. Local Markdown links and `git diff --check` pass. Figures 1–4 were visually reviewed for labels, dates, scales, legends and clipping; Figure 1 uses shared vertical scales across builds. Selection rules are explicit, and the figures preserve increases, decreases and printing limitations.

The full application test suite was not run: this package changes no application or model source, and the acceptance evidence is fresh execution of the actual model plus independent artifact and numeric checks. This does not claim broad application regression coverage.

## Scientific disposition

Long-term volume agreement is strong, including negligible totalwatsed differences and a 4.25 m³ difference in the 10 cm outlet ledger over 1.2723 billion m³. Daily outlet volumes do redistribute across boundaries; 44 days change by more than 1%. Peaks change in both directions. Two H670 positive-volume/zero-peak days occur in both builds and remain unresolved shared anomalies.

The printed routed hydrograph integral is not reconciled with the volume ledger. At 10 cm the deficit grows from 0.4628% in the original build to 1.3212% in the candidate, beyond conservative printing-rounding bounds in both. In the October 25–29, 1994 window it grows from 0.83% to 18.30% while the ledger changes by only 0.29 m³. No normalization or repair was applied to conceal that discrepancy.

Disposition: the requested comparison is complete as environment-validated research. It does not close a full hydrograph-conservation or release-validation claim. Diagnosing the channel hydrograph/volume relationship, scientific review of the peak approximation, deployment and affected-run rebuilding remain outside this comparison's completed scope.
